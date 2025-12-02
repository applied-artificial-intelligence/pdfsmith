"""Tests for individual backends."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF for testing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "test.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Test Document Title")
        c.drawString(100, 700, "This is paragraph one with some text content.")
        c.drawString(100, 650, "This is paragraph two with more content.")
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed")


class TestPyPDFBackend:
    """Tests for PyPDF backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.pypdf_backend import PyPDFBackend

            assert PyPDFBackend is not None
        except ImportError:
            pytest.skip("pypdf not installed")

    def test_parse(self, sample_pdf: Path):
        """Backend should parse PDF to text."""
        try:
            from pdfsmith.backends.pypdf_backend import AVAILABLE, PyPDFBackend

            if not AVAILABLE:
                pytest.skip("pypdf not installed")

            backend = PyPDFBackend()
            result = backend.parse(sample_pdf)
            assert isinstance(result, str)
            assert "Test" in result or "Document" in result
        except ImportError:
            pytest.skip("pypdf not installed")


class TestPDFPlumberBackend:
    """Tests for pdfplumber backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.pdfplumber_backend import PDFPlumberBackend

            assert PDFPlumberBackend is not None
        except ImportError:
            pytest.skip("pdfplumber not installed")

    def test_parse(self, sample_pdf: Path):
        """Backend should parse PDF to text."""
        try:
            from pdfsmith.backends.pdfplumber_backend import (
                AVAILABLE,
                PDFPlumberBackend,
            )

            if not AVAILABLE:
                pytest.skip("pdfplumber not installed")

            backend = PDFPlumberBackend()
            result = backend.parse(sample_pdf)
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("pdfplumber not installed")


class TestPyMuPDFBackend:
    """Tests for PyMuPDF backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.pymupdf_backend import PyMuPDFBackend

            assert PyMuPDFBackend is not None
        except ImportError:
            pytest.skip("pymupdf not installed")

    def test_parse(self, sample_pdf: Path):
        """Backend should parse PDF to text."""
        try:
            from pdfsmith.backends.pymupdf_backend import AVAILABLE, PyMuPDFBackend

            if not AVAILABLE:
                pytest.skip("pymupdf not installed")

            backend = PyMuPDFBackend()
            result = backend.parse(sample_pdf)
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("pymupdf not installed")


class TestPyMuPDF4LLMBackend:
    """Tests for PyMuPDF4LLM backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.pymupdf4llm_backend import PyMuPDF4LLMBackend

            assert PyMuPDF4LLMBackend is not None
        except ImportError:
            pytest.skip("pymupdf4llm not installed")


class TestDoclingBackend:
    """Tests for Docling backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.docling_backend import DoclingBackend

            assert DoclingBackend is not None
        except ImportError:
            pytest.skip("docling not installed")


class TestKreuzbergBackend:
    """Tests for Kreuzberg backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.kreuzberg_backend import KreuzbergBackend

            assert KreuzbergBackend is not None
        except ImportError:
            pytest.skip("kreuzberg not installed")
