"""PDFMiner text extraction with constructor-bound layout options."""

import importlib.util
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("pdfminer") is not None


class PDFMinerBackend:
    name = "pdfminer"
    options_schema = {
        "char_margin": Option(2.0, float, minimum=0),
        "line_margin": Option(0.5, float, minimum=0),
        "word_margin": Option(0.1, float, minimum=0),
        "detect_vertical": Option(False, bool),
        "all_texts": Option(False, bool),
    }

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams

        with StringIO() as output, path.open("rb") as stream:
            extract_text_to_fp(stream, output, laparams=LAParams(**self._options))
            return output.getvalue().strip()
