"""
Backend registry with lazy loading.

Each backend is only imported when actually used, keeping the base package lightweight.
"""

import sys
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass
class BackendInfo:
    """Static integration metadata; dependency presence is not execution readiness."""

    name: str
    description: str
    package: str
    weight: str
    loader: Callable[[], Any]
    extra: str = ""
    dependencies: tuple[str, ...] = ()
    input_formats: tuple[str, ...] = ("pdf",)
    required_env: tuple[str, ...] = ()
    execution_policy: str = "thread"
    python_minimum: tuple[int, int] | None = None
    python_maximum_exclusive: tuple[int, int] | None = None
    _instance: Any = field(default=None, init=False, repr=False, compare=False)
    _available: bool | None = field(default=None, init=False, repr=False, compare=False)
    _lock: Any = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.extra:
            self.extra = self.name

    def supports_python(self) -> bool:
        version = sys.version_info[:2]
        return (self.python_minimum is None or version >= self.python_minimum) and (
            self.python_maximum_exclusive is None
            or version < self.python_maximum_exclusive
        )

    def require_python(self) -> None:
        if not self.supports_python():
            minimum = ".".join(map(str, self.python_minimum or (3, 10)))
            maximum = ".".join(map(str, self.python_maximum_exclusive or (4, 0)))
            raise ImportError(
                f"Backend '{self.name}' requires Python >={minimum},<{maximum}"
            )

    def is_available(self) -> bool:
        """Inspect distribution metadata without running backend or SDK code."""
        if self._available is not None:
            return self._available
        for distribution in self.dependencies or (self.package,):
            try:
                metadata.distribution(distribution)
            except metadata.PackageNotFoundError:
                return False
        return True

    def get_instance(self, options: dict[str, Any] | None = None) -> Any:
        self.require_python()
        if options is not None:
            return self.loader()(**deepcopy(options))
        with self._lock:
            if self._instance is None:
                instance = self.loader()()
                self._instance = instance
            return self._instance


class BaseBackend:
    """Base class for all backends."""

    name: str = "base"

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown."""
        raise NotImplementedError


def _load_pypdf():
    from pdfsmith.backends.pypdf_backend import PyPDFBackend

    return PyPDFBackend


def _load_pdfplumber():
    from pdfsmith.backends.pdfplumber_backend import PDFPlumberBackend

    return PDFPlumberBackend


def _load_pymupdf():
    from pdfsmith.backends.pymupdf_backend import PyMuPDFBackend

    return PyMuPDFBackend


def _load_pymupdf4llm():
    from pdfsmith.backends.pymupdf4llm_backend import PyMuPDF4LLMBackend

    return PyMuPDF4LLMBackend


def _load_pdfminer():
    from pdfsmith.backends.pdfminer_backend import PDFMinerBackend

    return PDFMinerBackend


def _load_pypdfium2():
    from pdfsmith.backends.pypdfium2_backend import PyPDFium2Backend

    return PyPDFium2Backend


def _load_unstructured():
    from pdfsmith.backends.unstructured_backend import UnstructuredBackend

    return UnstructuredBackend


def _load_kreuzberg():
    from pdfsmith.backends.kreuzberg_backend import KreuzbergBackend

    return KreuzbergBackend


def _load_extractous():
    from pdfsmith.backends.extractous_backend import ExtractousBackend

    return ExtractousBackend


def _load_docling():
    from pdfsmith.backends.docling_backend import DoclingBackend

    return DoclingBackend


def _load_marker():
    from pdfsmith.backends.marker_backend import MarkerBackend

    return MarkerBackend


def _load_aws_textract():
    from pdfsmith.backends.aws_textract_backend import AWSTextractBackend

    return AWSTextractBackend


def _load_azure_document_intelligence():
    from pdfsmith.backends.azure_document_intelligence_backend import (
        AzureDocumentIntelligenceBackend,
    )

    return AzureDocumentIntelligenceBackend


def _load_google_document_ai():
    from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend

    return GoogleDocumentAIBackend


def _load_databricks():
    from pdfsmith.backends.databricks_backend import DatabricksBackend

    return DatabricksBackend


def _load_llamaparse():
    from pdfsmith.backends.llamaparse_backend import LlamaParseBackend

    return LlamaParseBackend


def _load_anthropic():
    from pdfsmith.backends.anthropic_backend import AnthropicBackend

    return AnthropicBackend


def _load_openai():
    from pdfsmith.backends.openai_backend import OpenAIBackend

    return OpenAIBackend


def _load_gemini():
    from pdfsmith.backends.gemini_backend import GeminiBackend

    return GeminiBackend


# Registry of all supported backends
BACKEND_REGISTRY: dict[str, BackendInfo] = {
    "pypdf": BackendInfo(
        name="pypdf",
        description="Pure Python PDF library, lightweight",
        package="pypdf",
        weight="light",
        loader=_load_pypdf,
    ),
    "pdfplumber": BackendInfo(
        name="pdfplumber",
        description="PDF text and table extraction",
        package="pdfplumber",
        weight="light",
        loader=_load_pdfplumber,
    ),
    "pymupdf": BackendInfo(
        name="pymupdf",
        description="Fast MuPDF bindings, good general purpose",
        package="pymupdf",
        weight="light",
        loader=_load_pymupdf,
    ),
    "pymupdf4llm": BackendInfo(
        name="pymupdf4llm",
        description="PyMuPDF optimized for LLM consumption",
        package="pymupdf4llm",
        weight="medium",
        loader=_load_pymupdf4llm,
    ),
    "pdfminer": BackendInfo(
        name="pdfminer",
        description="Mature PDF text extraction library",
        package="pdfminer.six",
        weight="light",
        loader=_load_pdfminer,
    ),
    "pypdfium2": BackendInfo(
        name="pypdfium2",
        description="PDFium bindings, Chrome's PDF engine",
        package="pypdfium2",
        weight="light",
        loader=_load_pypdfium2,
    ),
    "unstructured": BackendInfo(
        name="unstructured",
        description="Document processing for LLMs",
        package="unstructured",
        python_minimum=(3, 11),
        python_maximum_exclusive=(3, 14),
        dependencies=("unstructured", "pypdf", "pikepdf"),
        weight="medium",
        loader=_load_unstructured,
    ),
    "kreuzberg": BackendInfo(
        name="kreuzberg",
        description="Fast Rust-based extraction with OCR",
        package="kreuzberg",
        dependencies=("kreuzberg", "pypdf"),
        weight="medium",
        loader=_load_kreuzberg,
    ),
    "extractous": BackendInfo(
        name="extractous",
        description="Rust-based text extraction",
        package="extractous",
        dependencies=("extractous", "pypdf"),
        weight="medium",
        loader=_load_extractous,
    ),
    "docling": BackendInfo(
        name="docling",
        description="IBM document conversion",
        package="docling",
        dependencies=("docling", "pypdf"),
        weight="heavy",
        loader=_load_docling,
    ),
    "marker": BackendInfo(
        name="marker",
        description="Local document conversion with CPU model inference",
        package="marker-pdf",
        dependencies=("marker-pdf", "pypdf"),
        weight="heavy",
        loader=_load_marker,
    ),
    # Commercial backends
    "aws_textract": BackendInfo(
        name="aws_textract",
        description="AWS Textract, commercial OCR and text extraction",
        package="boto3",
        dependencies=("boto3", "pymupdf", "pypdf"),
        weight="commercial",
        loader=_load_aws_textract,
    ),
    "azure_document_intelligence": BackendInfo(
        name="azure_document_intelligence",
        description="Azure Document Intelligence OCR",
        package="azure-ai-documentintelligence",
        dependencies=("azure-ai-documentintelligence", "pypdf"),
        weight="commercial",
        loader=_load_azure_document_intelligence,
    ),
    "google_document_ai": BackendInfo(
        name="google_document_ai",
        description="Google Document AI, advanced document understanding",
        package="google-cloud-documentai",
        dependencies=("google-cloud-documentai", "google-cloud-storage", "pypdf"),
        weight="commercial",
        loader=_load_google_document_ai,
    ),
    "databricks": BackendInfo(
        name="databricks",
        description="Databricks ai_parse_document via SQL warehouse",
        package="databricks-sdk",
        dependencies=("databricks-sdk", "pypdf"),
        weight="commercial",
        loader=_load_databricks,
    ),
    "llamaparse": BackendInfo(
        name="llamaparse",
        description="LlamaIndex LlamaParse, GenAI-native document parsing",
        package="llama-cloud",
        dependencies=("llama-cloud", "pypdf"),
        weight="commercial",
        loader=_load_llamaparse,
    ),
    # Frontier LLM backends
    "anthropic": BackendInfo(
        name="anthropic",
        description="Anthropic Claude, frontier multimodal PDF parsing",
        package="anthropic",
        dependencies=("anthropic", "pypdf"),
        weight="commercial",
        loader=_load_anthropic,
    ),
    "openai": BackendInfo(
        name="openai",
        description="OpenAI GPT, frontier multimodal PDF parsing",
        package="openai",
        dependencies=("openai", "pypdf"),
        weight="commercial",
        loader=_load_openai,
    ),
    "gemini": BackendInfo(
        name="gemini",
        description="Google Gemini, frontier multimodal PDF parsing",
        package="google-genai",
        weight="commercial",
        loader=_load_gemini,
    ),
}


_EXTRA_NAMES = {
    "aws_textract": "aws",
    "azure_document_intelligence": "azure",
    "google_document_ai": "google",
}
_REQUIRED_ENV = {
    "azure_document_intelligence": (
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    ),
    "google_document_ai": ("GOOGLE_CLOUD_PROJECT", "GOOGLE_DOCUMENT_AI_PROCESSOR_ID"),
    "databricks": ("DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID"),
    "llamaparse": ("LLAMA_CLOUD_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GOOGLE_API_KEY or GEMINI_API_KEY",),
}
for _name, _info in BACKEND_REGISTRY.items():
    _info.extra = _EXTRA_NAMES.get(_name, _name)
    _info.required_env = _REQUIRED_ENV.get(_name, ())
    if _name in {
        "pymupdf",
        "pymupdf4llm",
        "docling",
        "marker",
        "kreuzberg",
        "extractous",
        "unstructured",
    }:
        _info.execution_policy = "process"
    elif _name == "pypdfium2":
        _info.execution_policy = "serialized-pdfium"
