"""pdfplumber backend for pdfsmith."""

from pathlib import Path
from typing import Any

try:
    import pdfplumber
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class PDFPlumberBackend:
    """PDF parser using pdfplumber - excellent for tables.

    pdfplumber uses visual layout analysis to detect and extract tables
    with high accuracy. Good choice for documents with tabular data.
    """

    name = "pdfplumber"

    def __init__(self) -> None:
        if not AVAILABLE:
            raise ImportError(
                "pdfplumber is required. Install with: pip install pdfsmith[pdfplumber]"
            )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string with table extraction."""
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return ""

            pages_content = []
            for page in pdf.pages:
                page_content = self._extract_page(page)
                if page_content.strip():
                    pages_content.append(page_content.strip())

            return "\n\n".join(pages_content)

    def _extract_page(self, page: Any) -> str:
        """Extract content from a single page."""
        content_parts = []

        # Extract tables
        tables = page.extract_tables()
        if tables:
            for table in tables:
                table_md = self._table_to_markdown(table)
                if table_md:
                    content_parts.append(table_md)

        # Extract text
        text = page.extract_text()
        if text and text.strip():
            content_parts.append(text.strip())

        return "\n\n".join(content_parts)

    def _table_to_markdown(self, table: list[list[str | None]]) -> str:
        """Convert table to GitHub Flavored Markdown."""
        if not table or len(table) < 2:
            return ""

        # Filter empty rows
        table = [row for row in table if any(cell for cell in row if cell)]
        if not table:
            return ""

        max_cols = max(len(row) for row in table)
        if max_cols == 0:
            return ""

        # Normalize rows
        normalized: list[list[str]] = []
        for row in table:
            padded = row + [None] * (max_cols - len(row))
            normalized.append([
                str(cell).strip() if cell is not None else ""
                for cell in padded
            ])

        lines = []
        # Header
        lines.append("| " + " | ".join(normalized[0]) + " |")
        # Separator
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        # Data rows
        for row in normalized[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)
