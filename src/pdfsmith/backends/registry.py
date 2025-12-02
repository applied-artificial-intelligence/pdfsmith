"""
Backend registry with lazy loading.

Each backend is only imported when actually used, keeping the base package lightweight.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BackendInfo:
    """Information about a parsing backend."""

    name: str
    description: str
    package: str  # PyPI package name for installation
    weight: str  # "light", "medium", "heavy"
    loader: Callable[[], Any]  # Function to load the backend class

    _instance: Any = None
    _available: bool | None = None

    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""
        if self._available is None:
            try:
                backend_class = self.loader()
                # Check the AVAILABLE flag if it exists
                import importlib

                mod = importlib.import_module(backend_class.__module__)
                self._available = getattr(mod, "AVAILABLE", True)
            except ImportError:
                self._available = False
        return self._available

    def get_instance(self):
        """Get or create a backend instance."""
        if self._instance is None:
            backend_class = self.loader()
            self._instance = backend_class()
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
        description="Detailed PDF parsing, excellent for tables",
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
        weight="medium",
        loader=_load_unstructured,
    ),
    "kreuzberg": BackendInfo(
        name="kreuzberg",
        description="Fast Rust-based extraction with OCR",
        package="kreuzberg",
        weight="medium",
        loader=_load_kreuzberg,
    ),
    "extractous": BackendInfo(
        name="extractous",
        description="Rust-based text extraction",
        package="extractous",
        weight="medium",
        loader=_load_extractous,
    ),
    "docling": BackendInfo(
        name="docling",
        description="IBM's document understanding, best quality",
        package="docling",
        weight="heavy",
        loader=_load_docling,
    ),
    "marker": BackendInfo(
        name="marker",
        description="Deep learning PDF to markdown, great for academic",
        package="marker-pdf",
        weight="heavy",
        loader=_load_marker,
    ),
    # Commercial backends
    "aws_textract": BackendInfo(
        name="aws_textract",
        description="AWS Textract, commercial OCR and text extraction",
        package="boto3",
        weight="commercial",
        loader=_load_aws_textract,
    ),
    "azure_document_intelligence": BackendInfo(
        name="azure_document_intelligence",
        description="Azure Document Intelligence, high-accuracy OCR",
        package="azure-ai-documentintelligence",
        weight="commercial",
        loader=_load_azure_document_intelligence,
    ),
    "google_document_ai": BackendInfo(
        name="google_document_ai",
        description="Google Document AI, advanced document understanding",
        package="google-cloud-documentai",
        weight="commercial",
        loader=_load_google_document_ai,
    ),
    "databricks": BackendInfo(
        name="databricks",
        description="Databricks ai_parse_document via SQL warehouse",
        package="databricks-sdk",
        weight="commercial",
        loader=_load_databricks,
    ),
    "llamaparse": BackendInfo(
        name="llamaparse",
        description="LlamaIndex LlamaParse, GenAI-native document parsing",
        package="llama-parse",
        weight="commercial",
        loader=_load_llamaparse,
    ),
    # Frontier LLM backends
    "anthropic": BackendInfo(
        name="anthropic",
        description="Anthropic Claude, frontier multimodal PDF parsing",
        package="anthropic",
        weight="commercial",
        loader=_load_anthropic,
    ),
    "openai": BackendInfo(
        name="openai",
        description="OpenAI GPT, frontier multimodal PDF parsing",
        package="openai",
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
