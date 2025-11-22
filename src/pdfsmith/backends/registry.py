"""
Backend registry with lazy loading.

Each backend is only imported when actually used, keeping the base package lightweight.
"""

from dataclasses import dataclass
from typing import Callable, Any
from pathlib import Path
import importlib


@dataclass
class BackendInfo:
    """Information about a parsing backend."""

    name: str
    description: str
    package: str  # PyPI package name for installation
    weight: str   # "light", "medium", "heavy"
    loader: Callable[[], Any]  # Function to load the backend class

    _instance: Any = None
    _available: bool | None = None

    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""
        if self._available is None:
            try:
                backend_class = self.loader()
                # Check the AVAILABLE flag if it exists
                module = backend_class.__module__
                import importlib
                mod = importlib.import_module(module)
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
}
