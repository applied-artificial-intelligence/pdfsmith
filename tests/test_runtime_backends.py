"""Real SDK regressions for native wrappers and complete local extraction."""

import asyncio
import subprocess
import sys

import pytest

from pdfsmith import parse
from pdfsmith.backends.registry import BACKEND_REGISTRY


@pytest.mark.parametrize(
    "backend,sdk",
    [
        ("kreuzberg", "kreuzberg"),
        ("extractous", "extractous"),
        ("unstructured", "unstructured.partition.pdf"),
    ],
)
def test_runtime_constructor_does_not_initialize_sdk(backend, sdk):
    code = (
        "import sys;from pdfsmith.backends.registry import BACKEND_REGISTRY;"
        f"BACKEND_REGISTRY[{backend!r}].loader()();"
        f"assert {sdk!r} not in sys.modules, 'SDK initialized before parse'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("backend", ["kreuzberg", "extractous", "unstructured"])
def test_runtime_wrapper_validates_input_before_loading_sdk(backend, tmp_path):
    with pytest.raises(FileNotFoundError):
        BACKEND_REGISTRY[backend].loader()().parse(tmp_path / "missing.pdf")


def test_current_kreuzberg_sdk_parses_and_sync_works_inside_event_loop(sample_pdf):
    pytest.importorskip("kreuzberg")
    cls = BACKEND_REGISTRY["kreuzberg"].loader()

    async def run():
        assert "pdfsmith" in cls().parse(sample_pdf)
        assert "pdfsmith" in await cls().parse_async(sample_pdf)

    asyncio.run(run())


def test_extractous_preserves_text_beyond_default_half_million_limit(tmp_path):
    pytest.importorskip("extractous")
    from reportlab.pdfgen import canvas

    path = tmp_path / "long.pdf"
    document = canvas.Canvas(str(path), invariant=1)
    for page in range(110):
        text = document.beginText(30, 760)
        text.setFont("Courier", 5)
        text.setLeading(8)
        for row in range(80):
            text.textLine(
                f"PAGE {page:03d} ROW {row:03d} "
                "complete document content must be retained in every extraction route."
            )
        if page == 109:
            text.textLine("FINAL DOCUMENT SENTINEL")
        document.drawText(text)
        document.showPage()
    document.save()
    result = parse(path, backend="extractous")
    assert len(result) > 500_000
    assert "FINAL DOCUMENT SENTINEL" in result


def test_unstructured_font_failure_cannot_become_successful_empty_output(
    sample_pdf, tmp_path
):
    pytest.importorskip("unstructured.partition.pdf")
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject

    path = tmp_path / "malformed-font.pdf"
    with sample_pdf.open("rb") as stream:
        reader = PdfReader(stream)
        page = reader.pages[0]
        font = page["/Resources"]["/Font"]["/F1"].get_object()
        font[NameObject("/Subtype")] = NameObject("/Type0")
        writer = PdfWriter()
        writer.add_page(page)
        with path.open("wb") as destination:
            writer.write(destination)
    with pytest.raises(RuntimeError, match="coverage"):
        parse(path, backend="unstructured")


@pytest.mark.parametrize(
    "backend,options",
    [
        ("kreuzberg", {"force_ocr": "maybe"}),
        ("extractous", {"unknown": True}),
        ("unstructured", {"strategy": "unknown"}),
    ],
)
def test_runtime_invalid_options_are_rejected_before_initialization(backend, options):
    with pytest.raises(ValueError):
        BACKEND_REGISTRY[backend].loader()(**options)
