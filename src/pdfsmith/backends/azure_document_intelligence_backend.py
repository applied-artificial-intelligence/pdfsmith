"""Azure Document Intelligence backend for pdfsmith.

Azure Document Intelligence (formerly Form Recognizer) provides commercial-grade
OCR and document understanding using Microsoft's ML models.

Requirements:
    - azure-ai-documentintelligence

Configuration:
    Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY
    environment variables.

Cost: $1.50 per 1,000 pages (Read model, 0-1M pages)
Limits: 500 MB file size, 2,000 pages per document
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure.ai.documentintelligence.models import AnalyzeResult

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeResult
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import HttpResponseError

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from pdfsmith.backends.registry import BaseBackend


class AzureDocumentIntelligenceBackend(BaseBackend):
    """Azure Document Intelligence backend for pdfsmith."""

    name = "azure_document_intelligence"

    def __init__(self) -> None:
        """Initialize Azure Document Intelligence backend."""
        if not AVAILABLE:
            raise ImportError(
                "azure-ai-documentintelligence is required. "
                "Install with: pip install azure-ai-documentintelligence"
            )

        import os

        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not endpoint or not api_key:
            raise RuntimeError(
                "Azure Document Intelligence credentials not found. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
                "AZURE_DOCUMENT_INTELLIGENCE_KEY environment variables."
            )

        try:
            self.client = DocumentIntelligenceClient(
                endpoint=endpoint, credential=AzureKeyCredential(api_key)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Azure client: {e}") from e

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using Azure Document Intelligence.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            ValueError: If PDF exceeds size limits
            RuntimeError: If API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Check file size (500 MB limit)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 500:
            raise ValueError(
                f"PDF too large ({file_size_mb:.1f} MB). "
                "Azure Document Intelligence has 500 MB limit."
            )

        try:
            # Read PDF
            pdf_bytes = pdf_path.read_bytes()

            # Call Azure Document Intelligence API
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                body=pdf_bytes,
                content_type="application/pdf",
            )

            # Wait for result
            result: AnalyzeResult = poller.result()

            # Extract text
            return self._extract_text(result)

        except HttpResponseError as e:
            status_code = e.status_code if hasattr(e, "status_code") else "Unknown"
            error_msg = str(e)

            if status_code == 429:
                raise RuntimeError(f"Azure rate limit exceeded: {error_msg}") from e
            elif status_code == 400:
                raise ValueError(f"Invalid PDF: {error_msg}") from e
            else:
                msg = f"Azure API error ({status_code}): {error_msg}"
                raise RuntimeError(msg) from e

        except Exception as e:
            raise RuntimeError(f"Failed to parse with Azure: {e}") from e

    def _extract_text(self, result: "AnalyzeResult") -> str:
        """Extract text from Azure AnalyzeResult."""
        text_blocks = []

        if result.pages:
            for page in result.pages:
                if page.lines:
                    for line in page.lines:
                        text_blocks.append(line.content)

        return "\n\n".join(text_blocks).strip()
