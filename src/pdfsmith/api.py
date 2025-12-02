"""
Core API for pdfsmith.

Provides a simple interface to parse PDFs to markdown using various backends.
"""

from pathlib import Path
from typing import Literal

from pdfsmith.backends.registry import BACKEND_REGISTRY, BackendInfo

# Backend preference order (best first, considering quality vs availability)
DEFAULT_PREFERENCE = [
    "docling",      # Best quality, heavy
    "marker",       # Great for academic docs
    "pymupdf4llm",  # Good balance
    "kreuzberg",    # Fast, good quality
    "unstructured", # Versatile
    "pdfplumber",   # Reliable for tables
    "pymupdf",      # Fast, basic
    "pypdf",        # Lightweight fallback
    "pdfminer",     # Legacy but works
    "pypdfium2",    # Alternative
    "extractous",   # Rust-based
]

BackendName = Literal[
    "docling", "marker", "pymupdf4llm", "kreuzberg", "unstructured",
    "pdfplumber", "pymupdf", "pypdf", "pdfminer", "pypdfium2", "extractous"
]


def available_backends() -> list[BackendInfo]:
    """Return list of available (installed) backends with their info."""
    available = []
    for name in DEFAULT_PREFERENCE:
        if name in BACKEND_REGISTRY:
            info = BACKEND_REGISTRY[name]
            if info.is_available():
                available.append(info)
    return available


def get_backend(name: BackendName | None = None):
    """
    Get a backend instance by name, or auto-select the best available.

    Args:
        name: Backend name, or None to auto-select

    Returns:
        Backend instance ready to parse

    Raises:
        ImportError: If specified backend is not installed
        RuntimeError: If no backends are available
    """
    if name is not None:
        if name not in BACKEND_REGISTRY:
            available = list(BACKEND_REGISTRY.keys())
            raise ValueError(f"Unknown backend: {name}. Available: {available}")
        info = BACKEND_REGISTRY[name]
        if not info.is_available():
            raise ImportError(
                f"Backend '{name}' is not installed. "
                f"Install with: pip install pdfsmith[{name}]"
            )
        return info.get_instance()

    # Auto-select best available
    for backend_name in DEFAULT_PREFERENCE:
        if backend_name in BACKEND_REGISTRY:
            info = BACKEND_REGISTRY[backend_name]
            if info.is_available():
                return info.get_instance()

    raise RuntimeError(
        "No PDF parsing backends are installed. "
        "Install with: pip install pdfsmith[light] or pdfsmith[recommended]"
    )


def parse(
    pdf_path: str | Path,
    *,
    backend: BackendName | None = None,
) -> str:
    """
    Parse a PDF file to markdown.

    Args:
        pdf_path: Path to the PDF file
        backend: Backend to use, or None to auto-select best available

    Returns:
        Markdown string extracted from the PDF

    Examples:
        # Auto-select backend
        markdown = parse("document.pdf")

        # Use specific backend
        markdown = parse("document.pdf", backend="docling")
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    backend_instance = get_backend(backend)
    return backend_instance.parse(pdf_path)


async def parse_async(
    pdf_path: str | Path,
    *,
    backend: BackendName | None = None,
) -> str:
    """
    Parse a PDF file to markdown asynchronously.

    Args:
        pdf_path: Path to the PDF file
        backend: Backend to use, or None to auto-select best available

    Returns:
        Markdown string extracted from the PDF
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    backend_instance = get_backend(backend)

    # Use async method if available, otherwise run sync in executor
    if hasattr(backend_instance, "parse_async"):
        return await backend_instance.parse_async(pdf_path)
    else:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, backend_instance.parse, pdf_path)
