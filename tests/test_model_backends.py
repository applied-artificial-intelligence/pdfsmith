"""Model wrapper discovery must not initialize libraries or acquire assets."""

import os
import subprocess
import sys

import pytest

from pdfsmith.backends.registry import BACKEND_REGISTRY


@pytest.mark.parametrize("backend", ["docling", "marker"])
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


@pytest.mark.parametrize(
    "options",
    [
        {"use_llm": True},
        {"disable_ocr": "invalid"},
        {"num_threads": 0},
        {"num_threads": True},
        {"model_cache_dir": ""},
        {"llama_cpp_binary": ""},
        {"unknown": True},
    ],
)
def test_marker_rejects_paid_augmentation_and_invalid_options_before_sdk_work(options):
    with pytest.raises(ValueError):
        BACKEND_REGISTRY["marker"].loader()(**options)


@pytest.mark.parametrize("fail", [False, True])
def test_marker_reaps_only_its_own_real_subprocesses_on_return_and_failure(fail):
    from pdfsmith.backends.marker_backend import _OwnedProcesses

    command = [
        sys.executable,
        "-c",
        "import time;print('ready',flush=True);time.sleep(120)",
    ]
    unowned = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    owned = _OwnedProcesses()
    child = None
    try:
        assert unowned.stdout.readline().strip() == "ready"
        try:
            with owned:
                child = owned.Popen(command, stdout=subprocess.PIPE, text=True)
                assert child.stdout.readline().strip() == "ready"
                assert child.poll() is None
                if fail:
                    raise RuntimeError("Controlled conversion failure")
        except RuntimeError as exc:
            assert fail and str(exc) == "Controlled conversion failure"
        assert child.poll() is not None
        assert child.wait(timeout=1) == child.returncode
        assert unowned.poll() is None, "Another caller's process was stopped"
    finally:
        for process in (child, unowned):
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
                process.stdout.close()


def test_model_worker_allows_only_the_port_of_its_owned_local_server():
    code = '''import os, socket, sys
from pdfsmith.backends._process import _test_network_guard
from pdfsmith.backends.marker_backend import _OwnedProcesses
server = socket.socket();server.bind(("127.0.0.1", 0))
port = server.getsockname()[1];server.close()
unowned = socket.socket();unowned.bind(("127.0.0.1", 0));unowned.listen()
os.environ["_PDFSMITH_TEST_OFFLINE"] = "1"
_test_network_guard()
program = """import socket,sys
s=socket.socket();s.bind(('127.0.0.1',int(sys.argv[-1])));s.listen()
print('ready',flush=True)
conn,_=s.accept();conn.sendall(b'owned');conn.close();s.close()
"""
with _OwnedProcesses() as owner:
    child = owner.Popen([sys.executable, "-c", program, "--port", str(port)],
                        stdout=owner.PIPE, text=True)
    assert child.stdout.readline().strip() == "ready"
    with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
        assert conn.recv(20) == b"owned"
    for address in [("127.0.0.1", unowned.getsockname()[1]), ("example.com", 443)]:
        try:socket.create_connection(address, timeout=1)
        except RuntimeError:pass
        else:raise AssertionError("Unowned or external endpoint was allowed")
    child.stdout.close()
try:socket.create_connection(("127.0.0.1", port), timeout=1)
except RuntimeError:pass
else:raise AssertionError("Stopped server port remained authorized")
unowned.close()
'''
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr


def test_model_worker_keeps_completed_content_when_real_child_wait_reports_failure(
    monkeypatch, tmp_path
):
    import contextlib
    import io
    import json

    from pdfsmith.backends import _process
    from pdfsmith.backends.marker_backend import _OwnedProcesses
    from pdfsmith.errors import BackendOperationError

    def produce(backend, path, options):
        with _OwnedProcesses() as owner:
            child = owner.Popen([sys.executable, "-c", "import time;time.sleep(120)"])
            wait = child.wait

            def broken_wait(*args, **kwargs):
                wait(*args, **kwargs)
                raise OSError("Controlled OS wait reporting failure")

            monkeypatch.setattr(child, "wait", broken_wait)
            owner.content = "Completed extraction"
        return owner.content

    def execute_worker(command, *, input, **kwargs):
        output = io.StringIO()
        monkeypatch.setattr(sys, "stdin", io.StringIO(input))
        monkeypatch.setattr(sys, "argv", ["pdfsmith.backends._process"])
        with contextlib.redirect_stdout(output):
            _process.main()
        return subprocess.CompletedProcess(command, 0, output.getvalue(), "")

    monkeypatch.setattr(_process, "_extract", produce)
    monkeypatch.setattr(_process, "_test_network_guard", lambda: None)
    monkeypatch.setattr(subprocess, "run", execute_worker)
    with pytest.raises(BackendOperationError) as caught:
        _process.extract_in_process("marker", tmp_path / "controlled.pdf", {})
    assert caught.value.parse_completed
    assert caught.value.recovered_content == "Completed extraction"
    assert caught.value.resource_ids
    assert isinstance(caught.value.cleanup_errors, tuple)
    assert "Controlled OS wait reporting failure" in caught.value.cleanup_errors[0]
    json.dumps(caught.value.resource_ids)
