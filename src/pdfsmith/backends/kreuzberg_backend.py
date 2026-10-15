"""Validated kreuzberg PDF extraction in an isolated native worker."""

import asyncio
import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("kreuzberg") is not None


class KreuzbergBackend:
    name = "kreuzberg"
    options_schema = {
        "force_ocr": Option(False, bool),
        "output_format": Option("plain", str, ("plain", "markdown")),
    }

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)

    async def parse_async(self, pdf_path: Path) -> str:
        return await asyncio.to_thread(self.parse, pdf_path)


def _extract(path: Path, options: dict[str, Any]) -> str:
    from pdfsmith._documents import pdf_page_count

    count = pdf_page_count(path)
    from kreuzberg import ExtractionConfig, OcrConfig, PageConfig, extract_file_sync

    force_ocr = options["force_ocr"]
    # The 4.10.4 constructor accepts disable_ocr; its type stub omits that field.
    configuration: dict[str, Any] = {
        "force_ocr": force_ocr,
        "disable_ocr": not force_ocr,
        "ocr": OcrConfig(backend="tesseract", language="eng") if force_ocr else None,
        "use_cache": False,
        "output_format": options["output_format"],
        "pages": PageConfig(extract_pages=True),
    }
    config = ExtractionConfig(**configuration)
    result = extract_file_sync(path, mime_type="application/pdf", config=config)
    if result.llm_usage:
        raise RuntimeError("Unexpected LLM augmentation in local Kreuzberg extraction")
    pages = result.pages
    if pages is None or len(pages) != count:
        raise RuntimeError("Kreuzberg returned incomplete page coverage")
    for index, page in enumerate(pages, 1):
        if page.get("page_number") != index or not isinstance(page.get("content"), str):
            raise RuntimeError("Kreuzberg returned missing, reordered or invalid pages")
    if not isinstance(result.content, str):
        raise RuntimeError("Kreuzberg did not return complete text")
    return result.content.strip()
