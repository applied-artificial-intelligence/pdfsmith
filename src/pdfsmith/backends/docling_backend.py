"""Docling backend for pdfsmith.

IBM Docling provides high-quality PDF to markdown conversion with
optional OCR support and table structure extraction.

IMPORTANT - Resource Requirements:
    - Fast mode (no OCR): ~8-12GB RAM per instance, ~2-5 sec/doc
    - Accurate mode (with OCR): ~12-16GB RAM per instance, ~30-60 sec/doc
    - GPU recommended for OCR mode (CUDA or MPS)
    - KNOWN MEMORY LEAK: Docling accumulates memory over conversions
      (see https://github.com/docling-project/docling/issues/2209)

Configuration (in order of precedence):
    1. Constructor arguments: DoclingBackend(do_ocr=True)
    2. Environment variables: DOCLING_OCR=true
    3. Config file: .pdfsmith/docling.yaml or ~/.config/pdfsmith/docling.yaml
    4. Built-in defaults

Example config file (.pdfsmith/docling.yaml):
    do_ocr: false
    do_table_structure: true
    num_threads: 2  # Lower value recommended to limit memory
    device: auto  # auto, cpu, cuda, mps
"""

import gc
import os
from pathlib import Path
from typing import Any

# Set thread limits BEFORE importing docling (affects MKL, OpenMP, etc.)
# See: https://github.com/docling-project/docling-serve/issues/366
_num_threads = os.environ.get("DOCLING_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", _num_threads)
os.environ.setdefault("MKL_NUM_THREADS", _num_threads)
os.environ.setdefault("OPENBLAS_NUM_THREADS", _num_threads)

try:
    import docling  # noqa: F401

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from pdfsmith.config import get_backend_defaults, load_backend_config  # noqa: E402

# Recreate converter every N documents to mitigate memory leaks
# See: https://github.com/docling-project/docling/issues/2209
CONVERTER_RESET_INTERVAL = 10

# Known configuration options for environment variable lookup
KNOWN_OPTIONS = [
    "do_ocr",
    "do_table_structure",
    "num_threads",
    "device",
    "ocr_languages",
    "table_mode",
    "generate_page_images",
    "generate_picture_images",
    "images_scale",
]


class DoclingBackend:
    """PDF parser using IBM Docling - highest quality extraction.

    Docling uses deep learning models for document understanding.
    Best quality output but requires significant resources.

    Configuration sources (in precedence order):
        1. Constructor arguments
        2. Environment variables (DOCLING_<OPTION>)
        3. Config files (.pdfsmith/docling.yaml, ~/.config/pdfsmith/docling.yaml)
        4. Built-in defaults

    By default, OCR is DISABLED for performance. Enable via:
        - Constructor: DoclingBackend(do_ocr=True)
        - Environment: DOCLING_OCR=true
        - Config file: do_ocr: true

    Resource estimates:
        - Fast mode (no OCR): 2-4GB RAM, 2-5 sec/doc
        - Accurate mode (OCR): 8-12GB RAM, 30-60 sec/doc, GPU recommended
    """

    name = "docling"

    def __init__(
        self,
        do_ocr: bool | None = None,
        do_table_structure: bool | None = None,
        num_threads: int | None = None,
        device: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the DoclingBackend.

        Args:
            do_ocr: Enable OCR for scanned documents. Default: False
            do_table_structure: Enable table structure extraction. Default: True
            num_threads: Number of CPU threads. Default: 4
            device: Device selection ("auto", "cpu", "cuda", "mps"). Default: "auto"
            **kwargs: Additional options
        """
        if not AVAILABLE:
            raise ImportError(
                "docling is required. Install with: pip install pdfsmith[docling]"
            )

        # Build explicit options from constructor args
        explicit_options = {k: v for k, v in kwargs.items() if v is not None}
        if do_ocr is not None:
            explicit_options["do_ocr"] = do_ocr
        if do_table_structure is not None:
            explicit_options["do_table_structure"] = do_table_structure
        if num_threads is not None:
            explicit_options["num_threads"] = num_threads
        if device is not None:
            explicit_options["device"] = device

        # Load configuration from all sources
        defaults = get_backend_defaults("docling")
        config = load_backend_config("docling", explicit_options, KNOWN_OPTIONS)

        # Apply defaults, then loaded config
        self._config = {**defaults, **config.options}
        self._config_source = config.source

        # Extract commonly used options
        self._do_ocr = self._config.get("do_ocr", False)
        self._do_table_structure = self._config.get("do_table_structure", True)
        self._num_threads = self._config.get("num_threads", 2)  # Lower for memory
        self._device = self._config.get("device", "auto")

        # Lazy-loaded converter (created on first use)
        self._converter: Any = None
        # Counter for memory leak mitigation
        self._conversion_count = 0

    def _get_converter(self) -> Any:
        """Get or create the document converter with configured options."""
        if self._converter is not None:
            return self._converter

        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self._do_ocr
        pipeline_options.do_table_structure = self._do_table_structure

        # Configure additional options from config
        if self._config.get("generate_page_images"):
            pipeline_options.generate_page_images = True
        if self._config.get("generate_picture_images"):
            pipeline_options.generate_picture_images = True
        if self._config.get("images_scale"):
            pipeline_options.images_scale = float(self._config["images_scale"])

        # Configure accelerator options
        try:
            from docling.datamodel.accelerator_options import (
                AcceleratorDevice,
                AcceleratorOptions,
            )

            device_map = {
                "auto": AcceleratorDevice.AUTO,
                "cpu": AcceleratorDevice.CPU,
                "cuda": AcceleratorDevice.CUDA,
                "mps": AcceleratorDevice.MPS,
            }
            device = device_map.get(self._device.lower(), AcceleratorDevice.AUTO)

            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=self._num_threads,
                device=device,
            )
        except ImportError:
            pass  # Older docling version

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        return self._converter

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string.

        Includes memory cleanup to mitigate known docling memory leaks.
        See: https://github.com/docling-project/docling/issues/2209
        """
        # Reset converter periodically to mitigate memory leaks
        if self._conversion_count >= CONVERTER_RESET_INTERVAL:
            self._converter = None
            gc.collect()
            self._conversion_count = 0

        converter = self._get_converter()
        result = converter.convert(pdf_path)
        markdown_text = result.document.export_to_markdown()

        # Memory cleanup: call unload() on backends to release resources
        # See: https://github.com/docling-project/docling-serve/issues/366
        try:
            # Primary cleanup path: result.input._backend.unload()
            if hasattr(result, "input") and hasattr(result.input, "_backend"):
                backend = result.input._backend
                if hasattr(backend, "unload"):
                    backend.unload()
            # Fallback: try document._backend
            elif hasattr(result, "document") and hasattr(result.document, "_backend"):
                backend = result.document._backend
                if hasattr(backend, "unload"):
                    backend.unload()
            # Also try result-level unload
            if hasattr(result, "unload"):
                result.unload()
        except Exception:
            pass  # Best effort cleanup

        self._conversion_count += 1
        gc.collect()

        return markdown_text
