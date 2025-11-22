"""PyPDF backend for pdfsmith."""

from pathlib import Path

try:
    import pypdf
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PyPDFBackend:
    """PDF parser using PyPDF for text extraction.

    PyPDF is a pure-python library - lightweight with no binary dependencies.
    Good for simple text extraction, not ideal for complex layouts or tables.
    """

    name = "pypdf"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "pypdf is required. Install with: pip install pdfsmith[pypdf]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))

        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())

        return "\n\n".join(text_parts)
