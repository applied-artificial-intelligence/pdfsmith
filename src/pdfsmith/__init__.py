"""PDFsmith's public string-based parsing interface."""

from pdfsmith.api import available_backends, get_backend, parse, parse_async

__version__ = "0.3.0.dev0"
IMAGE_CAPABLE_BACKENDS: set[str] = set()
__all__ = [
    "parse",
    "parse_async",
    "available_backends",
    "get_backend",
    "IMAGE_CAPABLE_BACKENDS",
    "__version__",
]
