"""
pdfsmith - PDF to Markdown conversion with multiple backend support.

A unified interface to 10+ PDF parsing libraries. Pick the right tool for the job,
or let pdfsmith choose for you.

Basic usage:
    from pdfsmith import parse

    # Auto-select best available backend
    markdown = parse("document.pdf")

    # Use specific backend
    markdown = parse("document.pdf", backend="docling")

    # List available backends
    from pdfsmith import available_backends
    print(available_backends())
"""

from pdfsmith.api import available_backends, get_backend, parse, parse_async

__version__ = "0.2.0"
__all__ = ["parse", "parse_async", "available_backends", "get_backend", "__version__"]
