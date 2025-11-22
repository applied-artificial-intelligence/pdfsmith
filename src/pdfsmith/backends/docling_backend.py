"""Docling backend for pdfsmith."""

from pathlib import Path

try:
    from docling.document_converter import DocumentConverter
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class DoclingBackend:
    """PDF parser using IBM Docling - highest quality extraction.

    Docling uses deep learning models for document understanding.
    Best quality output but requires significant resources (GPU recommended).
    """

    name = "docling"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "docling is required. Install with: pip install pdfsmith[docling]"
            )
        self._converter = DocumentConverter()

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        result = self._converter.convert(pdf_path)
        return result.document.export_to_markdown()
