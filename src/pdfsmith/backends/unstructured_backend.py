"""Unstructured backend for pdfsmith.

Supports multiple strategies:
- "fast": Quick extraction without OCR (default)
- "hi_res": High-resolution with OCR and table detection

IMPORTANT: The "hi_res" strategy requires:
1. unstructured-pytesseract: pip install unstructured-pytesseract
2. tesseract-ocr system package:
    Ubuntu/Debian: sudo apt-get install tesseract-ocr
    macOS: brew install tesseract
    Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
"""

from pathlib import Path

try:
    from unstructured.partition.pdf import partition_pdf

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class UnstructuredBackend:
    """PDF parser using Unstructured - versatile document processing.

    Unstructured is a comprehensive document processing library
    designed for preparing data for LLMs. Supports many strategies.
    """

    name = "unstructured"

    def __init__(self, strategy: str = "fast") -> None:
        if not AVAILABLE:
            raise ImportError(
                "unstructured required. Install: pip install pdfsmith[unstructured]"
            )
        self.strategy = strategy

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        elements = partition_pdf(filename=str(pdf_path), strategy=self.strategy)

        # Convert elements to markdown
        parts = []
        for element in elements:
            text = str(element)
            if text.strip():
                # Add heading markers for titles
                if element.category == "Title":
                    parts.append(f"# {text}")
                elif element.category == "Header":
                    parts.append(f"## {text}")
                else:
                    parts.append(text)

        return "\n\n".join(parts)
