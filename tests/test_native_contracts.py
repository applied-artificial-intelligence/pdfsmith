"""Exercise real native SDK boundaries without concurrent unsafe engine calls."""

import asyncio
import importlib
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from pdfsmith import parse, parse_async


@pytest.mark.parametrize("backend", ["pymupdf", "pymupdf4llm", "pdfminer", "pypdfium2"])
def test_constructor_does_not_import_or_initialize_native_sdk(backend):
    packages = {
        "pymupdf": "fitz",
        "pymupdf4llm": "pymupdf4llm",
        "pdfminer": "pdfminer.high_level",
        "pypdfium2": "pypdfium2",
    }
    code = (
        "import sys; from pdfsmith.backends.registry import BACKEND_REGISTRY; "
        f"BACKEND_REGISTRY[{backend!r}].loader()(); "
        f"assert {packages[backend]!r} not in sys.modules, 'SDK loaded before parse'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("backend", ["pymupdf", "pymupdf4llm"])
def test_direct_and_async_native_extraction_avoid_parent_runtime(
    backend, sample_pdf, monkeypatch
):
    fitz = pytest.importorskip("fitz")

    def forbidden_parent_runtime(*args, **kwargs):
        raise RuntimeError("Native extraction entered parent runtime")

    monkeypatch.setattr(fitz, "open", forbidden_parent_runtime)
    monkeypatch.setattr(
        importlib.import_module("pymupdf"), "open", forbidden_parent_runtime
    )
    assert "pdfsmith" in parse(sample_pdf, backend=backend)
    assert "pdfsmith" in asyncio.run(parse_async(sample_pdf, backend=backend))


def test_pdfium_serializes_distinct_instances_and_closes_document_handles(
    sample_pdf, monkeypatch
):
    pdfium = pytest.importorskip("pypdfium2")
    original = pdfium.PdfDocument
    documents = []
    active = 0
    guard = threading.Lock()

    def observed_document(*args, **kwargs):
        nonlocal active
        with guard:
            active += 1
            if active != 1:
                active -= 1
                raise RuntimeError("Overlapping PDFium runtime calls")
        try:
            time.sleep(0.03)
            document = original(*args, **kwargs)
            documents.append(document)
            return document
        finally:
            with guard:
                active -= 1

    monkeypatch.setattr(pdfium, "PdfDocument", observed_document)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: parse(sample_pdf, backend="pypdfium2"), range(8))
        )
    assert all("pdfsmith" in text for text in results)
    assert len(documents) == 8
    assert all(document.raw is None for document in documents)


@pytest.mark.parametrize("backend", ["pymupdf", "pymupdf4llm", "pdfminer", "pypdfium2"])
def test_direct_backend_checks_input_before_sdk_loading(backend, tmp_path, monkeypatch):
    from pdfsmith.backends.registry import BACKEND_REGISTRY

    backend_type = BACKEND_REGISTRY[backend].loader()
    monkeypatch.setattr(
        importlib, "import_module", lambda *args: pytest.fail("SDK load")
    )
    with pytest.raises(FileNotFoundError):
        backend_type().parse(tmp_path / "missing.pdf")


@pytest.mark.parametrize(
    "backend, options",
    [
        ("pymupdf", {"sort": "maybe"}),
        ("pymupdf4llm", {"use_llm": True}),
        ("pdfminer", {"char_margin": -1}),
        ("pypdfium2", {"typo": True}),
    ],
)
def test_native_options_fail_before_parsing(backend, options):
    from pdfsmith.backends.registry import BACKEND_REGISTRY

    with pytest.raises(ValueError):
        BACKEND_REGISTRY[backend].loader()(**options)


def test_pdfium_closes_document_after_real_extraction_failure(sample_pdf, monkeypatch):
    pdfium = pytest.importorskip("pypdfium2")
    documents = []
    original_document = pdfium.PdfDocument
    original_extract = pdfium.PdfTextPage.get_text_range

    def document(*args, **kwargs):
        result = original_document(*args, **kwargs)
        documents.append(result)
        return result

    def failed_textpage(self, *args, **kwargs):
        assert "pdfsmith" in original_extract(self, *args, **kwargs)
        raise RuntimeError("controlled extraction failure")

    monkeypatch.setattr(pdfium, "PdfDocument", document)
    monkeypatch.setattr(pdfium.PdfTextPage, "get_text_range", failed_textpage)
    with pytest.raises(RuntimeError, match="controlled extraction failure"):
        parse(sample_pdf, backend="pypdfium2")
    assert documents and documents[0].raw is None


@pytest.mark.parametrize("backend", ["pymupdf", "pymupdf4llm", "pdfminer", "pypdfium2"])
def test_owner_only_encryption_stays_readable_and_user_password_is_rejected(
    backend, tmp_path
):
    from reportlab.lib.pdfencrypt import StandardEncryption
    from reportlab.pdfgen import canvas

    dependencies = {
        "pymupdf": "pymupdf",
        "pymupdf4llm": "pymupdf4llm",
        "pdfminer": "pdfminer",
        "pypdfium2": "pypdfium2",
    }
    pytest.importorskip(dependencies[backend])
    error_type: type[Exception] = ValueError
    if backend == "pdfminer":
        from pdfminer.pdfdocument import PDFPasswordIncorrect

        error_type = PDFPasswordIncorrect
    elif backend == "pypdfium2":
        from pypdfium2 import PdfiumError

        error_type = PdfiumError
    for password in ("", "controlled-user-password"):
        path = tmp_path / ("owner.pdf" if not password else "protected.pdf")
        encryption = StandardEncryption(password, ownerPassword="controlled-owner")
        document = canvas.Canvas(str(path), encrypt=encryption, invariant=1)
        document.drawString(72, 720, "OWNER PERMISSIONS DOCUMENT")
        document.save()
        if password:
            with pytest.raises(error_type):
                parse(path, backend=backend)
        else:
            assert "OWNER PERMISSIONS" in parse(path, backend=backend)
