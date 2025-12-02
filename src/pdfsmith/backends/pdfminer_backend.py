"""PDFMiner backend for pdfsmith."""

from io import StringIO
from pathlib import Path

try:
    from pdfminer.high_level import extract_text_to_fp
    from pdfminer.layout import LAParams

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PDFMinerBackend:
    """PDF parser using PDFMiner - mature text extraction.

    PDFMiner is a mature, pure-Python PDF text extraction library.
    Good for text-heavy documents, handles various encodings well.
    """

    name = "pdfminer"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "pdfminer.six is required. Install with: pip install pdfsmith[pdfminer]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        output = StringIO()
        with open(pdf_path, "rb") as f:
            extract_text_to_fp(f, output, laparams=LAParams())
        return output.getvalue().strip()
