"""Validated PDF extraction in a fresh native worker process."""

import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("pymupdf4llm") is not None


class PyMuPDF4LLMBackend:
    name = "pymupdf4llm"
    options_schema = {
        "use_layout": Option(False, bool),
        "table_strategy": Option(
            "lines_strict", str, ("lines", "lines_strict", "text")
        ),
        "force_text": Option(True, bool),
        "ignore_images": Option(False, bool),
        "use_ocr": Option(False, bool),
    }

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)
        if self._options["use_layout"]:
            for key in ("ignore_images", "table_strategy"):
                if key in options:
                    raise ValueError(f"pymupdf4llm.{key} requires use_layout=False")
                self._options.pop(key)
        else:
            if "use_ocr" in options:
                raise ValueError("pymupdf4llm.use_ocr requires use_layout=True")
            self._options.pop("use_ocr")

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)
