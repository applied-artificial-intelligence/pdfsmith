"""Marker backend for pdfsmith."""

from pathlib import Path

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class MarkerBackend:
    """PDF parser using Marker - deep learning for academic PDFs.

    Marker uses deep learning models optimized for academic papers
    and technical documents. Excellent for LaTeX-heavy content.
    """

    name = "marker"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "marker-pdf is required. Install with: pip install pdfsmith[marker]"
            )
        self._models = create_model_dict()
        self._converter = PdfConverter(artifact_dict=self._models)

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        result = self._converter(str(pdf_path))
        return result.markdown
