"""Model wrapper discovery must not initialize libraries or acquire assets."""

import os
import subprocess
import sys

import pytest

from pdfsmith.backends.registry import BACKEND_REGISTRY


@pytest.mark.parametrize("backend", ["docling"])
def test_model_constructor_does_not_initialize_sdk_or_change_thread_environment(
    backend,
):
    code = """import os, sys, socket
def denied(*args, **kwargs): raise RuntimeError("Constructor attempted networking")
socket.socket.connect = denied
socket.getaddrinfo = denied
from pdfsmith.backends.registry import BACKEND_REGISTRY
before = dict(os.environ)
BACKEND_REGISTRY[sys.argv[1]].loader()()
assert dict(os.environ) == before, "Constructor changed process environment"
roots = {n.split(".")[0] for n in sys.modules}
assert not roots.intersection({"docling", "marker", "surya", "torch"}), roots
"""
    result = subprocess.run(
        [sys.executable, "-c", code, backend],
        env={
            **os.environ,
            "SURYA_INFERENCE_AUTOSTART": "false",
            "FAST_LAYOUT_SERVER_AUTOSTART": "false",
            "OCR_ERROR_SERVER_AUTOSTART": "false",
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "options",
    [
        {"do_ocr": "maybe"},
        {"device": "unknown"},
        {"num_threads": 0},
        {"num_threads": True},
        {"table_mode": "unknown"},
        {"ocr_languages": [""]},
        {"generate_page_images": True},
        {"images_scale": 2},
    ],
)
def test_docling_rejects_ignored_or_invalid_options_before_sdk_work(options):
    with pytest.raises(ValueError):
        BACKEND_REGISTRY["docling"].loader()(**options)


def test_docling_freezes_typed_configuration_and_preserves_documented_none_aliases(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOCLING_OCR", "false")
    monkeypatch.setenv("DOCLING_THREADS", "3")
    backend = BACKEND_REGISTRY["docling"].loader()(
        do_ocr=None, ocr_languages=["en", "de"], table_mode="fast"
    )
    options = backend.effective_options
    assert options["do_ocr"] is False
    assert options["num_threads"] == 3
    assert options["ocr_languages"] == ["eng", "deu"]
    options["ocr_languages"].append("fra")
    monkeypatch.setenv("DOCLING_OCR", "true")
    assert backend.effective_options["ocr_languages"] == ["eng", "deu"]
    assert backend.effective_options["do_ocr"] is False


def test_docling_missing_input_fails_before_sdk_initialization(tmp_path):
    with pytest.raises(FileNotFoundError):
        BACKEND_REGISTRY["docling"].loader()().parse(tmp_path / "missing.pdf")
