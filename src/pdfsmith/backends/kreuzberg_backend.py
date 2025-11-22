"""Kreuzberg backend for pdfsmith.

NOTE: By default, this backend disables OCR to avoid loading heavy ML models
(~50GB memory). For OCR-based extraction, use force_ocr=True.
"""

from pathlib import Path
import asyncio

try:
    from kreuzberg import extract_file, ExtractionConfig
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    ExtractionConfig = None  # type: ignore[misc,assignment]


class KreuzbergBackend:
    """PDF parser using Kreuzberg - fast Rust-based extraction.

    Kreuzberg is a high-performance document extraction library with
    a Rust core. Fast, lightweight, with built-in OCR support.

    By default, OCR is disabled for performance. Enable with force_ocr=True.
    """

    name = "kreuzberg"

    def __init__(self, force_ocr: bool = False) -> None:
        """Initialize Kreuzberg backend.

        Args:
            force_ocr: If True, enable OCR for scanned documents (memory-intensive)
        """
        if not AVAILABLE:
            raise ImportError(
                "kreuzberg is required. Install with: pip install pdfsmith[kreuzberg]"
            )
        self._force_ocr = force_ocr

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        # Kreuzberg is async, so we need to run it in an event loop
        return asyncio.run(self._parse_async(pdf_path))

    def _get_config(self) -> "ExtractionConfig":
        """Get extraction config based on OCR setting."""
        if self._force_ocr:
            return ExtractionConfig(force_ocr=True)
        # Text-only mode: no OCR backend, much faster and lighter
        return ExtractionConfig(ocr_backend=None, force_ocr=False)

    async def _parse_async(self, pdf_path: Path) -> str:
        """Async implementation."""
        config = self._get_config()
        result = await extract_file(pdf_path, config=config)
        return result.content

    async def parse_async(self, pdf_path: Path) -> str:
        """Native async parsing."""
        config = self._get_config()
        result = await extract_file(pdf_path, config=config)
        return result.content
