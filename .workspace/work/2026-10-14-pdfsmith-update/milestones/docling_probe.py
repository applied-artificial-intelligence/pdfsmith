"""Installed Docling CPU conversion and producing-SDK failure evidence."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def denied(*a, **kw):
        raise RuntimeError("Network disabled in Docling conversion evidence")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    socket.create_connection = denied
    from pdfsmith.backends.docling_backend import (
        DoclingBackend,
        _extract,
        _get_converter,
    )

    before = dict(os.environ)
    options = dict(device="cpu", num_threads=2, artifacts_path=str(args.assets))
    backend = DoclingBackend(**options)
    assert dict(os.environ) == before
    assert not any(name.startswith(("docling.", "torch")) for name in sys.modules)
    text = pdfsmith.parse(args.document, backend="docling", backend_options=options)
    assert "Summary" in text
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
            args.fixtures / "two-pages.pdf", backend="docling", backend_options=options
        )
        assert result == controlled

    asyncio.run(run())
    cli = subprocess.run(
        [
            str(Path(sys.executable).with_name("pdfsmith")),
            "parse",
            str(args.fixtures / "two-pages.pdf"),
            "-b",
            "docling",
            "--backend-options",
            json.dumps(options),
        ],
        capture_output=True,
        timeout=150,
    )
    assert cli.returncode == 0, cli.stderr
    assert cli.stdout == controlled.encode()
    ocr_options = {**options, "do_ocr": True, "ocr_languages": ["en"]}
    ocr = pdfsmith.parse(
        args.fixtures / "scanned.pdf", backend="docling", backend_options=ocr_options
    )
    assert "OCR READABLE SENTINEL 12345" in ocr

    assert dict(os.environ) == before, "Public parsing changed the caller environment"

    from docling.backend.docling_parse_backend import (
        ThreadedDoclingParseDocumentBackend,
        ThreadedDoclingParsePageBackend,
    )
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument

    configured = DoclingBackend(
        **{**options, "table_mode": "fast", "ocr_languages": ["de"], "do_ocr": True}
    )
    converter = _get_converter(configured.effective_options)
    from docling.datamodel.base_models import InputFormat

    pipeline = converter.format_to_options[InputFormat.PDF].pipeline_options
    assert pipeline.do_ocr is True
    assert pipeline.ocr_options.lang == ["deu"]
    assert pipeline.table_structure_options.mode.value == "fast"
    assert str(pipeline.accelerator_options.device) == "cpu"
    assert pipeline.accelerator_options.num_threads == 2
    assert pipeline.enable_remote_services is False
    assert not pipeline.generate_page_images and not pipeline.generate_picture_images

    original_valid = ThreadedDoclingParsePageBackend.is_valid
    original_unload = ThreadedDoclingParseDocumentBackend.unload
    original_convert = DocumentConverter.convert
    conversions = []
    unloaded = []

    def fail_second(self):
        return False if self.page_no == 2 else original_valid(self)

    def track_unload(self):
        original_unload(self)
        assert self._closed
        unloaded.append(self.document_hash)

    def track_convert(self, *a, **kw):
        result = original_convert(self, *a, **kw)
        conversions.append(
            dict(
                status=result.status.value,
                errors=len(result.errors),
                pages=len(result.pages),
            )
        )
        return result

    with (
        patch.object(ThreadedDoclingParsePageBackend, "is_valid", fail_second),
        patch.object(ThreadedDoclingParseDocumentBackend, "unload", track_unload),
        patch.object(DocumentConverter, "convert", track_convert),
    ):
        try:
            _extract(args.fixtures / "two-pages.pdf", backend.effective_options)
        except RuntimeError as exc:
            assert "did not complete" in str(exc)
            errors["partial"] = str(exc)
        else:
            raise AssertionError("Partial conversion was returned as success")
    assert conversions[-1]["status"] == "partial_success"
    assert conversions[-1]["errors"] > 0
    assert unloaded
    unloaded.clear()

    def export_failure(self, *a, **kw):
        assert unloaded, "PDF handles were still open when export began"
        raise RuntimeError("Controlled Markdown export failure")

    with (
        patch.object(ThreadedDoclingParseDocumentBackend, "unload", track_unload),
        patch.object(DoclingDocument, "export_to_markdown", export_failure),
    ):
        try:
            _extract(args.fixtures / "two-pages.pdf", backend.effective_options)
        except RuntimeError as exc:
            assert "Controlled Markdown export failure" in str(exc)
            errors["export"] = str(exc)
        else:
            raise AssertionError("Export failure was suppressed")
    private_sdk_environment_changes = sorted(
        key
        for key in set(os.environ) | set(before)
        if os.environ.get(key) != before.get(key)
    )
    for name, output in (("public", text), ("controlled", controlled), ("ocr", ocr)):
        (args.output / f"{name}.md").write_text(output)
    package = Path(pdfsmith.__file__).parent
    result = dict(
        evidence="local-e2e; typed SDK fault injection; no quality ranking",
        python=platform.python_version(),
        package_path=str(package),
        version=pdfsmith.__version__,
        options=backend.effective_options,
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
        conversions=conversions,
        sdk_unload_before_export_confirmed=True,
        private_sdk_environment_changes=private_sdk_environment_changes,
        cli_returncode=cli.returncode,
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"outputs": result["outputs"], "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
