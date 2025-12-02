"""PyPDFium2 backend for pdfsmith."""

from pathlib import Path

try:
    import pypdfium2 as pdfium

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PyPDFium2Backend:
    """PDF parser using PyPDFium2 - Chrome's PDF engine.

    PyPDFium2 wraps PDFium, the PDF rendering engine used in Chrome.
    Fast and reliable for text extraction.
    """

    name = "pypdfium2"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "pypdfium2 is required. Install with: pip install pdfsmith[pypdfium2]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        pdf = pdfium.PdfDocument(pdf_path)

        pages_text = []
        for page in pdf:
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            if text.strip():
                pages_text.append(text.strip())

        return "\n\n".join(pages_text)
