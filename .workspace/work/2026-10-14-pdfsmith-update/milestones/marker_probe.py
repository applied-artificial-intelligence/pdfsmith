"""Installed Marker CPU evidence, including owned model-server termination."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pdfsmith


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from pdfsmith.backends.marker_backend import (
        MarkerBackend,
        _extract,
        _OwnedProcesses,
    )

    options = dict(
        model_cache_dir=str(args.assets),
        llama_cpp_binary=str(args.binary),
        num_threads=8,
    )
    before = dict(os.environ)
    backend = MarkerBackend(**options)
    assert not any(n.startswith(("marker.", "surya.", "torch")) for n in sys.modules)
    public_options = {**options, "disable_ocr": True}
    public = pdfsmith.parse(
        args.document, backend="marker", backend_options=public_options
    )
    assert "Summary" in public
    controlled = backend.parse(args.fixtures / "two-pages.pdf")
    assert controlled.count("LEFT COLUMN") == 2
    assert backend.parse(args.fixtures / "blank.pdf") == ""
    errors = {}
    for label in ("missing", "corrupt"):
        try:
            backend.parse(args.fixtures / f"{label}.pdf")
        except Exception as exc:
            errors[label] = dict(type=type(exc).__name__, message=str(exc))
        else:
            raise AssertionError(f"{label} succeeded")

    async def run():
        result = await pdfsmith.parse_async(
            args.fixtures / "two-pages.pdf", backend="marker", backend_options=options
        )
        assert result == controlled

    asyncio.run(run())
    configured_options = {**options, "paginate_output": True, "disable_ocr": True}
    configured = pdfsmith.parse(
        args.fixtures / "two-pages.pdf",
        backend="marker",
        backend_options=configured_options,
    )
    assert configured != controlled
    assert "{0}" in configured and "{1}" in configured
    cli = subprocess.run(
        [
            str(Path(sys.executable).with_name("pdfsmith")),
            "parse",
            str(args.fixtures / "two-pages.pdf"),
            "-b",
            "marker",
            "--backend-options",
            json.dumps(configured_options),
        ],
        capture_output=True,
        timeout=150,
    )
    assert cli.returncode == 0, cli.stderr
    assert cli.stdout == configured.encode()
    ocr = backend.parse(args.fixtures / "scanned.pdf")
    assert "OCR READABLE SENTINEL 12345" in ocr
    assert dict(os.environ) == before, "Public parsing changed the caller environment"

    os.environ.update(
        MODEL_CACHE_DIR=str(args.assets / "models"),
        FONT_PATH=str(args.assets / "font/GoNotoCurrent-Regular.ttf"),
        TORCH_DEVICE="cpu",
    )

    # SDK fault injection stays inside this standalone evidence process. It uses
    # real conversion/model responses and records the actual spawned processes.
    from pdfsmith.backends._process import _test_network_guard

    _test_network_guard()
    from marker.builders.document import DocumentBuilder
    from marker.renderers.markdown import MarkdownRenderer

    original_build = DocumentBuilder.__call__
    original_exit = _OwnedProcesses.__exit__
    servers = []
    partial_pages = []

    def record_exit(self, *a, **kw):
        original_exit(self, *a, **kw)
        for child in self.children:
            assert child.poll() is not None, "Owned model server survived cleanup"
            servers.append(
                dict(pid=child.pid, returncode=child.returncode, args=child.args)
            )

    def drop_last_page(self, *a, **kw):
        document = original_build(self, *a, **kw)
        assert len(document.pages) == 2
        document.pages.pop()
        partial_pages.append(len(document.pages))
        return document

    no_ocr = MarkerBackend(**{**options, "disable_ocr": True}).effective_options
    with (
        patch.object(DocumentBuilder, "__call__", drop_last_page),
        patch.object(_OwnedProcesses, "__exit__", record_exit),
    ):
        try:
            _extract(args.fixtures / "two-pages.pdf", no_ocr)
        except RuntimeError as exc:
            assert "coverage" in str(exc)
            errors["partial"] = str(exc)
        else:
            raise AssertionError("Incomplete SDK document was accepted")
    assert partial_pages == [1]
    assert servers

    def export_failure(self, *a, **kw):
        raise RuntimeError("Controlled Marker renderer failure")

    previous = len(servers)
    with (
        patch.object(MarkdownRenderer, "__call__", export_failure),
        patch.object(_OwnedProcesses, "__exit__", record_exit),
    ):
        try:
            _extract(args.fixtures / "two-pages.pdf", no_ocr)
        except RuntimeError as exc:
            assert "Controlled Marker renderer failure" in str(exc)
            errors["export"] = str(exc)
        else:
            raise AssertionError("Renderer failure was suppressed")
    assert len(servers) > previous
    for name, output in (
        ("public", public),
        ("controlled", controlled),
        ("configured", configured),
        ("ocr", ocr),
    ):
        (args.output / f"{name}.md").write_text(output)
    package = Path(pdfsmith.__file__).parent
    result = dict(
        evidence="local-e2e; controlled SDK producing-code faults; no quality ranking",
        python=platform.python_version(),
        version=pdfsmith.__version__,
        package_path=str(package),
        options=backend.effective_options,
        public_options=public_options,
        dependencies={
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        source_hashes={
            str(p.relative_to(package)): sha(p.read_bytes())
            for p in package.rglob("*.py")
        },
        inputs={
            str(p): sha(p.read_bytes())
            for p in [args.document, *args.fixtures.glob("*.pdf")]
        },
        outputs={p.name: sha(p.read_bytes()) for p in args.output.glob("*.md")},
        errors=errors,
        terminated_model_servers=servers,
        cli_returncode=cli.returncode,
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"outputs": result["outputs"], "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
