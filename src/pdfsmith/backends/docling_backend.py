"""Docling PDF conversion with frozen configuration and isolated model execution."""

import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import (
    Option,
    get_backend_defaults,
    load_backend_config,
    normalize_options,
)

AVAILABLE = importlib.util.find_spec("docling") is not None


class DoclingBackend:
    name = "docling"
    options_schema = {
        "do_ocr": Option(False, bool),
        "do_table_structure": Option(True, bool),
        "num_threads": Option(4, int, minimum=1),
        "device": Option("auto", str, ("auto", "cpu", "cuda", "mps")),
        "ocr_languages": Option(["en"], list),
        "table_mode": Option("accurate", str, ("fast", "accurate")),
        "artifacts_path": Option(None, str, allow_none=True),
    }

    def __init__(
        self,
        do_ocr: bool | None = None,
        do_table_structure: bool | None = None,
        num_threads: int | None = None,
        device: str | None = None,
        **options: Any,
    ) -> None:
        explicit = dict(options)
        for key, value in (
            ("do_ocr", do_ocr),
            ("do_table_structure", do_table_structure),
            ("num_threads", num_threads),
            ("device", device),
        ):
            if value is not None:
                explicit[key] = value
        config = load_backend_config(self.name, explicit, list(self.options_schema))
        merged = {**get_backend_defaults(self.name), **config.options}
        if isinstance(merged.get("ocr_languages"), str):
            try:
                merged["ocr_languages"] = json.loads(merged["ocr_languages"])
            except ValueError as exc:
                raise ValueError("docling.ocr_languages must be a JSON list") from exc
        self._options = normalize_options(self.name, merged, self.options_schema)
        languages = self._options["ocr_languages"]
        if not languages or any(
            not isinstance(lang, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", lang)
            for lang in languages
        ):
            raise ValueError("docling.ocr_languages requires nonempty language codes")
        aliases = {"en": "eng", "de": "deu", "fr": "fra", "es": "spa"}
        self._options["ocr_languages"] = [aliases.get(lang, lang) for lang in languages]
        if self._options["artifacts_path"] is not None:
            if not self._options["artifacts_path"].strip():
                raise ValueError("docling.artifacts_path must be a nonempty path")
            self._options["artifacts_path"] = str(
                Path(self._options["artifacts_path"]).expanduser().absolute()
            )

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)


def _get_converter(options: dict[str, Any]) -> Any:
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        TableStructureOptions,
        TesseractCliOcrOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    artifacts = options["artifacts_path"]
    if artifacts is not None and not Path(artifacts).is_dir():
        raise ValueError("docling.artifacts_path must be an existing model directory")
    pipeline = PdfPipelineOptions(
        do_ocr=options["do_ocr"],
        do_table_structure=options["do_table_structure"],
        accelerator_options=AcceleratorOptions(
            num_threads=options["num_threads"], device=options["device"]
        ),
        ocr_options=TesseractCliOcrOptions(lang=options["ocr_languages"]),
        table_structure_options=TableStructureOptions(
            mode=TableFormerMode(options["table_mode"])
        ),
        artifacts_path=Path(artifacts) if artifacts else None,
        enable_remote_services=False,
        generate_page_images=False,
        generate_picture_images=False,
    )
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)},
    )


def _extract(path: Path, options: dict[str, Any]) -> str:
    from pdfsmith._documents import pdf_page_count

    count = pdf_page_count(path)
    from docling.datamodel.base_models import ConversionStatus

    converter = _get_converter(options)
    # The SDK's pipeline unloads input and page handles in its own finally block.
    # The fresh worker owns model memory, including conversion/export failures.
    result = converter.convert(path)
    if result.status != ConversionStatus.SUCCESS or result.errors:
        raise RuntimeError(f"Docling conversion did not complete: {result.status}")
    expected = list(range(1, count + 1))
    if [page.page_no for page in result.pages] != expected or sorted(
        result.document.pages
    ) != expected:
        raise RuntimeError("Docling returned incomplete page coverage")
    text = result.document.export_to_markdown()
    if not isinstance(text, str):
        raise RuntimeError("Docling did not return Markdown text")
    return text
