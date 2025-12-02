"""PyMuPDF4LLM backend for pdfsmith."""

from pathlib import Path

try:
    import pymupdf4llm

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PyMuPDF4LLMBackend:
    """PDF parser using PyMuPDF4LLM - optimized for LLM consumption.

    PyMuPDF4LLM builds on PyMuPDF to produce markdown output specifically
    formatted for LLM processing. Good balance of quality and speed.
    """

    name = "pymupdf4llm"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "pymupdf4llm is required. Install with: pip install pdfsmith[light]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        return pymupdf4llm.to_markdown(str(pdf_path))
