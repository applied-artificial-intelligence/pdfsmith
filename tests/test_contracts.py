"""Regressions for the reviewed discovery, option and execution contracts."""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest

from pdfsmith import get_backend, parse, parse_async
from pdfsmith.backends.registry import BACKEND_REGISTRY, BackendInfo
from pdfsmith.config import BACKEND_DEFAULTS, BackendConfig, get_backend_defaults


def test_discovery_does_not_import_wrappers_or_change_environment():
    code = """
import os, sys, json
from pdfsmith import available_backends
before = dict(os.environ)
available_backends()
loaded = [n for n in sys.modules if n.startswith('pdfsmith.backends.')
          and n != 'pdfsmith.backends.registry']
print(json.dumps({'loaded': loaded, 'changed': before != dict(os.environ)}))
"""
    env = {key: value for key, value in os.environ.items() if key != "OMP_NUM_THREADS"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    observed = json.loads(result.stdout)
    assert observed == {"loaded": [], "changed": False}


def test_dependency_detection_never_executes_a_broken_loader():
    def broken():
        raise OSError("installed native library cannot load")

    info = BackendInfo("pypdf", "test", "pypdf", "light", broken)
    assert info.is_available() is True


def test_released_pdf_path_keyword_and_alias_conflict(sample_pdf):
    assert parse(pdf_path=sample_pdf, backend="pypdf") == parse(
        input_path=sample_pdf, backend="pypdf"
    )
    with pytest.raises(TypeError, match="both"):
        parse(sample_pdf, input_path=sample_pdf, backend="pypdf")


async def test_async_released_pdf_path_keyword(sample_pdf):
    assert await parse_async(pdf_path=sample_pdf, backend="pypdf") == parse(
        sample_pdf, backend="pypdf"
    )


def test_no_option_instances_reuse_but_configured_instances_do_not():
    assert get_backend("pypdf") is get_backend("pypdf")
    assert get_backend("pypdf", backend_options={}) is not get_backend(
        "pypdf", backend_options={}
    )


def test_simultaneous_default_requests_construct_one_instance():
    constructed = []

    class SlowBackend:
        def __init__(self):
            constructed.append(self)
            time.sleep(0.02)

    info = BackendInfo("slow", "test", "pypdf", "light", lambda: SlowBackend)
    with ThreadPoolExecutor(max_workers=4) as pool:
        instances = list(pool.map(lambda _: info.get_instance(), range(4)))
    assert len(constructed) == 1
    assert all(instance is instances[0] for instance in instances)


def test_instance_creation_does_not_change_metadata_equality():
    class Backend:
        pass

    def loader():
        return Backend

    left = BackendInfo("test", "test", "pypdf", "light", loader)
    right = BackendInfo("test", "test", "pypdf", "light", loader)
    assert left == right
    left.get_instance()
    assert left == right


@pytest.mark.parametrize("name", sorted(BACKEND_REGISTRY))
def test_unsupported_image_is_rejected_before_loading(name, tmp_path, monkeypatch):
    path = tmp_path / "scan.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    info = BACKEND_REGISTRY[name]
    if "png" in getattr(info, "input_formats", ()):
        pytest.skip("This backend has a separately verified PNG route")

    def reached_loader():
        raise AssertionError("unsupported image reached backend initialization")

    monkeypatch.setattr(info, "loader", reached_loader)
    with pytest.raises(ValueError, match="support"):
        parse(path, backend=name)


def test_pdfplumber_constructor_layout_changes_actual_output(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "columns.pdf"
    document = canvas.Canvas(str(path), invariant=1)
    document.drawString(72, 720, "LEFT COLUMN")
    document.drawString(360, 720, "RIGHT COLUMN")
    document.save()
    backend = BACKEND_REGISTRY["pdfplumber"].loader()
    plain = backend().parse(path)
    layout = backend(layout=True).parse(path)
    assert "LEFT COLUMN" in layout and "RIGHT COLUMN" in layout
    assert plain != layout
    assert parse(path, backend="pdfplumber", backend_options={"layout": True}) == layout


def test_nested_defaults_are_not_shared_between_backend_configurations(monkeypatch):
    monkeypatch.setitem(BACKEND_DEFAULTS, "docling", {"ocr_languages": ["en"]})
    first = get_backend_defaults("docling")
    first["ocr_languages"].append("de")
    assert get_backend_defaults("docling")["ocr_languages"] == ["en"]


def test_documented_docling_ocr_environment_alias(monkeypatch, tmp_path):
    from pdfsmith.config import load_backend_config

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("DOCLING_OCR", "true")
    config = load_backend_config("docling", known_options=["do_ocr"])
    assert config.get_bool("do_ocr") is True


def test_project_configuration_preserves_unrelated_user_options(monkeypatch, tmp_path):
    from pdfsmith.config import load_backend_config

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    user = tmp_path / ".config/pdfsmith"
    user.mkdir(parents=True)
    (user / "docling.yaml").write_text("num_threads: 7\n")
    local = project / ".pdfsmith"
    local.mkdir()
    (local / "docling.yaml").write_text("do_ocr: false\n")
    config = load_backend_config("docling", known_options=["num_threads", "do_ocr"])
    assert config.get_int("num_threads") == 7
    assert config.get_bool("do_ocr") is False


def test_invalid_boolean_is_not_silently_coerced_to_false():
    with pytest.raises(ValueError, match="boolean"):
        BackendConfig("docling", {"do_ocr": "typo"}).get_bool("do_ocr")


async def test_async_initialization_allows_loop_work(sample_pdf, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    class BlockingBackend:
        def __init__(self):
            started.set()
            self.released_while_initializing = release.wait(timeout=0.2)

        def parse(self, path):
            return str(self.released_while_initializing)

    info = BackendInfo("blocking", "test", "pypdf", "light", lambda: BlockingBackend)
    monkeypatch.setitem(BACKEND_REGISTRY, "blocking", info)

    async def loop_work():
        while not started.is_set():
            await asyncio.sleep(0)
        release.set()

    parsed, _ = await asyncio.gather(
        parse_async(sample_pdf, backend="blocking"), loop_work()
    )
    assert parsed == "True"


def test_unsupported_options_fail_before_parsing(sample_pdf, monkeypatch):
    backend_class = BACKEND_REGISTRY["pypdf"].loader()

    def unexpected_parse(self, path):
        raise AssertionError("invalid configuration reached extraction")

    monkeypatch.setattr(backend_class, "parse", unexpected_parse)
    with pytest.raises((TypeError, ValueError), match="typo"):
        parse(sample_pdf, backend="pypdf", backend_options={"typo": True})


def test_configured_options_are_a_defensive_snapshot():
    from pdfsmith.config import load_backend_config

    options = {"nested": {"languages": ["en"]}}
    expected = deepcopy(options)
    config = load_backend_config("test", explicit_options=options)
    options["nested"]["languages"].append("de")
    assert config.options == expected
