"""Kreuzberg backend for pdfsmith."""

from pathlib import Path
import asyncio

try:
    from kreuzberg import extract_file
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class KreuzbergBackend:
    """PDF parser using Kreuzberg - fast Rust-based extraction.

    Kreuzberg is a high-performance document extraction library with
    a Rust core. Fast, lightweight, with built-in OCR support.
    """

    name = "kreuzberg"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "kreuzberg is required. Install with: pip install pdfsmith[kreuzberg]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        # Kreuzberg is async, so we need to run it in an event loop
        return asyncio.run(self._parse_async(pdf_path))

    async def _parse_async(self, pdf_path: Path) -> str:
        """Async implementation."""
        result = await extract_file(pdf_path)
        return result.content

    async def parse_async(self, pdf_path: Path) -> str:
        """Native async parsing."""
        result = await extract_file(pdf_path)
        return result.content
