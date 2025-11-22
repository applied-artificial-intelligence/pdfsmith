"""Extractous backend for pdfsmith."""

from pathlib import Path

try:
    from extractous import Extractor
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class ExtractousBackend:
    """PDF parser using Extractous - Rust-based extraction.

    Extractous is a Rust-based text extraction library with
    Python bindings. Fast and efficient.
    """

    name = "extractous"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "extractous is required. Install with: pip install pdfsmith[extractous]"
            )
        self._extractor = Extractor()

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        result = self._extractor.extract_file_to_string(str(pdf_path))
        return result.strip()
