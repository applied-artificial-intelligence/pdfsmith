"""PyPDF text extraction with validated constructor-bound options."""

import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("pypdf") is not None


class PyPDFBackend:
    name = "pypdf"
    options_schema = {"extraction_mode": Option("plain", str, ("plain", "layout"))}

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        from pypdf import PdfReader

        with path.open("rb") as stream:
            reader = PdfReader(stream)
            parts = []
            for page in reader.pages:
                text = page.extract_text(**self._options)
                if text and text.strip():
                    parts.append(text.strip())
            return "\n\n".join(parts)
