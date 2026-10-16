"""PDFsmith's public string-based parsing interface."""

from pdfsmith.api import (
    IMAGE_CAPABLE_BACKENDS,
    available_backends,
    get_backend,
    parse,
    parse_async,
    registered_backends,
)
from pdfsmith.errors import BackendOperationError

__version__ = "0.3.0.dev0"
__all__ = [
    "parse",
    "parse_async",
    "available_backends",
    "registered_backends",
    "get_backend",
    "IMAGE_CAPABLE_BACKENDS",
    "BackendOperationError",
    "__version__",
]
