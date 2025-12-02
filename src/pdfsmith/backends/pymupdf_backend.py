"""PyMuPDF backend for pdfsmith."""

from pathlib import Path

try:
    import fitz  # PyMuPDF

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PyMuPDFBackend:
    """PDF parser using PyMuPDF (fitz) - fast and reliable.

    PyMuPDF provides fast, reliable text extraction with good
    handling of various PDF formats. A solid general-purpose choice.
    """

    name = "pymupdf"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "PyMuPDF is required. Install with: pip install pdfsmith[pymupdf]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        doc = fitz.open(pdf_path)

        try:
            if doc.is_encrypted:
                raise RuntimeError(f"PDF is password-protected: {pdf_path}")

            pages_text = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    pages_text.append(page_text.strip())

            text = "\n\n".join(pages_text)

            # Clean up whitespace
            lines = text.split("\n")
            cleaned_lines = [" ".join(line.split()) for line in lines]
            text = "\n".join(cleaned_lines)

            # Normalize paragraph breaks
            while "\n\n\n" in text:
                text = text.replace("\n\n\n", "\n\n")

            return text.strip()

        finally:
            doc.close()
