"""Console-level regressions for input protection and atomic file output."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pdfsmith import cli


def run_cli(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(Path(sys.executable).with_name("pdfsmith")), *arguments],
        capture_output=True,
        timeout=30,
    )


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_console_rejects_output_aliases_without_destroying_input(
    sample_pdf, tmp_path, alias
):
    output = sample_pdf if alias == "same" else tmp_path / "alias.md"
    if alias == "symlink":
        output.symlink_to(sample_pdf)
    elif alias == "hardlink":
        os.link(sample_pdf, output)
    original = hashlib.sha256(sample_pdf.read_bytes()).hexdigest()
    result = run_cli("parse", str(sample_pdf), "--backend", "pypdf", "-o", str(output))
    assert result.returncode == 1, result.stderr
    assert hashlib.sha256(sample_pdf.read_bytes()).hexdigest() == original
    assert b"input" in result.stderr.lower()


def test_console_stdout_and_file_have_identical_content(sample_pdf, tmp_path):
    output = tmp_path / "output.md"
    stdout = run_cli("parse", str(sample_pdf), "--backend", "pypdf")
    written = run_cli("parse", str(sample_pdf), "--backend", "pypdf", "-o", str(output))
    assert stdout.returncode == written.returncode == 0
    assert stdout.stdout == output.read_bytes()
    assert written.stdout == b""


def test_console_backend_options_reach_the_parser(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "columns.pdf"
    document = canvas.Canvas(str(path), invariant=1)
    document.drawString(72, 720, "LEFT COLUMN")
    document.drawString(360, 720, "RIGHT COLUMN")
    document.save()
    plain = run_cli("parse", str(path), "--backend", "pdfplumber")
    layout = run_cli(
        "parse",
        str(path),
        "--backend",
        "pdfplumber",
        "--backend-options",
        '{"layout": true}',
    )
    assert layout.returncode == 0, layout.stderr
    assert plain.stdout != layout.stdout
    assert b"LEFT COLUMN" in layout.stdout and b"RIGHT COLUMN" in layout.stdout


@pytest.mark.parametrize("payload", ["{", "[]", '{"typo": true}'])
def test_invalid_configuration_preserves_existing_output(sample_pdf, tmp_path, payload):
    output = tmp_path / "output.md"
    output.write_bytes(b"previous valid output")
    result = run_cli(
        "parse",
        str(sample_pdf),
        "--backend",
        "pypdf",
        "-o",
        str(output),
        "--backend-options",
        payload,
    )
    assert result.returncode != 0
    assert output.read_bytes() == b"previous valid output"


@pytest.mark.parametrize("fault", ["write", "close"])
def test_real_console_io_failure_preserves_existing_output(
    sample_pdf, tmp_path, monkeypatch, fault
):
    output = tmp_path / "output.md"
    output.write_bytes(b"previous valid output")
    startup = tmp_path / "sitecustomize.py"
    startup.write_text(
        "import io, os\n"
        "original = io.open\n"
        "class FailingOutput:\n"
        "    def __init__(self, raw): self._stream = raw\n"
        "    def __getattr__(self, key): return getattr(self._stream, key)\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *args):\n"
        "        result = self._stream.__exit__(*args)\n"
        f"        if {fault!r} == 'close': raise OSError('controlled close failure')\n"
        "        return result\n"
        "    def write(self, value):\n"
        f"        if {fault!r} == 'write':\n"
        "            self._stream.write(value[:max(1, len(value)//2)])\n"
        "            self._stream.flush()\n"
        "            raise OSError('controlled partial write failure')\n"
        "        return self._stream.write(value)\n"
        "def failing_open(file, mode='r', *args, **kwargs):\n"
        "    raw = original(file, mode, *args, **kwargs)\n"
        "    return FailingOutput(raw) if 'w' in mode else raw\n"
        "io.open = failing_open\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    result = run_cli("parse", str(sample_pdf), "--backend", "pypdf", "-o", str(output))
    assert result.returncode == 1
    assert b"controlled" in result.stderr
    assert output.read_bytes() == b"previous valid output"


def test_unencodable_parser_output_does_not_truncate_destination(
    sample_pdf, tmp_path, monkeypatch
):
    output = tmp_path / "output.md"
    output.write_bytes(b"previous valid output")
    value = json.loads('"\\ud800"')
    monkeypatch.setattr(cli, "parse", lambda *args, **kwargs: value)
    args = argparse.Namespace(pdf_file=sample_pdf, output=output, backend="pypdf")
    assert cli.cmd_parse(args) == 1
    assert output.read_bytes() == b"previous valid output"


def test_replacement_failure_preserves_destination(sample_pdf, tmp_path, monkeypatch):
    output = tmp_path / "output.md"
    output.write_bytes(b"previous valid output")

    def fail_replace(*args, **kwargs):
        raise OSError("controlled replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    args = argparse.Namespace(pdf_file=sample_pdf, output=output, backend="pypdf")
    assert cli.cmd_parse(args) == 1
    assert output.read_bytes() == b"previous valid output"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["output.md", "test.pdf"]


def test_post_commit_diagnostic_failure_keeps_success_and_output(
    sample_pdf, tmp_path, monkeypatch
):
    output = tmp_path / "output.md"

    class BrokenDiagnostics:
        def write(self, value):
            raise OSError("diagnostic pipe closed")

    monkeypatch.setattr(sys, "stderr", BrokenDiagnostics())
    args = argparse.Namespace(pdf_file=sample_pdf, output=output, backend="pypdf")
    assert cli.cmd_parse(args) == 0
    assert "pdfsmith" in output.read_text()


def test_unusable_output_directory_fails_before_parser_initialization(
    sample_pdf, tmp_path, monkeypatch
):
    called = []
    monkeypatch.setattr(cli, "parse", lambda *args, **kwargs: called.append(True))
    args = argparse.Namespace(
        pdf_file=sample_pdf, output=tmp_path / "missing" / "output.md", backend="pypdf"
    )
    assert cli.cmd_parse(args) == 1
    assert called == []


def test_console_complete_inventory_exposes_registered_services():
    result = run_cli("backends", "--all")
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.decode().split("configuration not checked")) == 20
    assert b"aws_textract: registered" in result.stdout
    assert b"llamaparse: registered" in result.stdout


def test_completed_content_survives_provider_cleanup_failure(
    sample_pdf, tmp_path, monkeypatch
):
    from pdfsmith import BackendOperationError

    output = tmp_path / "output.md"
    output.write_bytes(b"previous valid output")

    def fail_cleanup(*args, **kwargs):
        raise BackendOperationError(
            "controlled provider cleanup failure",
            parse_completed=True,
            recovered_content="# Completed document",
            resource_ids={"job_id": "controlled-job"},
            cleanup_errors=("controlled cleanup failure",),
        )

    monkeypatch.setattr(cli, "parse", fail_cleanup)
    args = argparse.Namespace(pdf_file=sample_pdf, output=output, backend="llamaparse")
    assert cli.cmd_parse(args) == 1
    assert output.read_bytes() == b"previous valid output"
    recoveries = list(tmp_path.glob("pdfsmith-recovery-*.json"))
    assert len(recoveries) == 1
    recovered = json.loads(recoveries[0].read_text())
    assert recovered["recovered_content"] == "# Completed document"
    assert recovered["resource_ids"] == {"job_id": "controlled-job"}
