"""Validated unstructured PDF extraction in an isolated native worker."""

import importlib.metadata
import importlib.util
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.backends.registry import BACKEND_REGISTRY
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("unstructured") is not None


class UnstructuredBackend:
    name = "unstructured"
    options_schema = {
        "strategy": Option("fast", str, ("fast", "hi_res", "ocr_only")),
        "include_page_breaks": Option(False, bool),
    }

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)
        BACKEND_REGISTRY[self.name].require_python()

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)


def _extract(path: Path, options: dict[str, Any]) -> str:
    from pdfsmith._documents import pdf_page_count

    count = pdf_page_count(path)
    try:
        model_version = importlib.metadata.version("en-core-web-sm")
    except importlib.metadata.PackageNotFoundError:
        model_version = None
    if model_version != "3.8.0":
        raise ImportError(
            "Unstructured requires the en_core_web_sm 3.8.0 spaCy model. "
            "Preinstall it before parsing; PDFsmith does not install it implicitly."
        )
    import spacy

    try:
        spacy.load("en_core_web_sm", exclude=["ner", "lemmatizer", "attribute_ruler"])
    except OSError as exc:
        raise ImportError(
            "Unstructured cannot load the installed en_core_web_sm 3.8.0 model. "
            "Repair the model installation before parsing; "
            "PDFsmith does not download or repair it implicitly."
        ) from exc
    os.environ.pop("UNSTRUCTURED_DEFAULT_MODEL_NAME", None)
    os.environ.pop("UNSTRUCTURED_DEFAULT_MODEL_INITIALIZE_PARAMS_JSON_PATH", None)
    from unstructured.partition.pdf import partition_pdf

    elements = partition_pdf(
        filename=str(path),
        strategy=options["strategy"],
        hi_res_model_name="yolox",
        include_page_breaks=True,
        languages=["eng"],
        ocr_agent=(
            "unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract"
        ),
        table_ocr_agent=(
            "unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract"
        ),
    )
    breaks = sum(element.category == "PageBreak" for element in elements)
    if breaks != count:
        raise RuntimeError(
            "Unstructured returned incomplete page coverage; check local model assets "
            "and parser dependencies"
        )
    parts = []
    page_number = 1
    for element in elements:
        if element.category == "PageBreak":
            if options["include_page_breaks"]:
                parts.append("---")
            page_number += 1
            continue
        if element.metadata.page_number != page_number:
            raise RuntimeError("Unstructured returned invalid page order")
        text = str(element).strip()
        if text:
            if element.category == "Title":
                parts.append(f"# {text}")
            elif element.category == "Header":
                parts.append(f"## {text}")
            else:
                parts.append(text)
    return "\n\n".join(parts)
