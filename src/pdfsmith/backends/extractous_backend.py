"""Validated extractous PDF extraction in an isolated native worker."""

import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("extractous") is not None


class ExtractousBackend:
    name = "extractous"
    options_schema: dict[str, Option] = {}

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)


def _extract(path: Path, options: dict[str, Any]) -> str:
    from pdfsmith._documents import pdf_page_count

    count = pdf_page_count(path)
    from extractous import Extractor, PdfOcrStrategy, PdfParserConfig

    config = PdfParserConfig().set_ocr_strategy(PdfOcrStrategy.NO_OCR)
    extractor = Extractor().set_pdf_config(config)
    reader, metadata = extractor.extract_file(str(path))
    buffer = bytearray(65536)
    parts = []
    while True:
        size = reader.readinto(buffer)
        if not size:
            break
        parts.append(bytes(buffer[:size]))
    errors = [key for key in metadata if "exception" in key.lower()]
    if errors:
        raise RuntimeError(f"Extractous reported incomplete extraction: {errors}")
    if metadata.get("xmpTPg:NPages") != [str(count)]:
        raise RuntimeError("Extractous returned incomplete page metadata")
    return b"".join(parts).decode("utf-8").strip()
