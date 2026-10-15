"""PDFium text extraction serialized across all PDFsmith instances."""

import importlib.util
from pathlib import Path
from threading import RLock
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.config import normalize_options

AVAILABLE = importlib.util.find_spec("pypdfium2") is not None
PDFIUM_LOCK = RLock()


class PyPDFium2Backend:
    name = "pypdfium2"

    def __init__(self, **options: Any) -> None:
        normalize_options(self.name, options, {})

    @property
    def effective_options(self) -> dict[str, Any]:
        return {}

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        with PDFIUM_LOCK:
            import pypdfium2 as pdfium

            with pdfium.PdfDocument(path) as document:
                parts = []
                for page in document:
                    try:
                        textpage = page.get_textpage()
                        try:
                            text = textpage.get_text_range().strip()
                            if text:
                                parts.append(text)
                        finally:
                            textpage.close()
                    finally:
                        page.close()
                return "\n\n".join(parts)
