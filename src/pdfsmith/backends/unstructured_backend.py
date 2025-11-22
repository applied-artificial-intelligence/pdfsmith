"""Unstructured backend for pdfsmith."""

from pathlib import Path

try:
    from unstructured.partition.pdf import partition_pdf
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class UnstructuredBackend:
    """PDF parser using Unstructured - versatile document processing.

    Unstructured is a comprehensive document processing library
    designed for preparing data for LLMs. Supports many strategies.
    """

    name = "unstructured"

    def __init__(self, strategy: str = "fast") -> None:
        if not AVAILABLE:
            raise ImportError(
                "unstructured is required. Install with: pip install pdfsmith[unstructured]"
            )
        self.strategy = strategy

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown string."""
        elements = partition_pdf(filename=str(pdf_path), strategy=self.strategy)

        # Convert elements to markdown
        parts = []
        for element in elements:
            text = str(element)
            if text.strip():
                # Add heading markers for titles
                if element.category == "Title":
                    parts.append(f"# {text}")
                elif element.category == "Header":
                    parts.append(f"## {text}")
                else:
                    parts.append(text)

        return "\n\n".join(parts)
