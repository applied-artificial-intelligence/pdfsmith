"""Google Document AI backend for pdfsmith.

Google Cloud Document AI provides commercial-grade OCR and document understanding.

Requirements:
    - google-cloud-documentai
    - google-cloud-storage (for async batch processing)

Configuration:
    Set GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON),
    GOOGLE_CLOUD_PROJECT (project ID), and optionally
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID.

Cost: $1.50 per 1,000 pages (Document OCR)
Limits: 15 pages (synchronous), 500 pages (async with GCS)

Note: This backend uses synchronous API only (15 page limit).
For larger documents, use async batch processing in pdf-bench.
"""

from pathlib import Path

try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai_v1 as documentai

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from pdfsmith.backends.registry import BaseBackend


class GoogleDocumentAIBackend(BaseBackend):
    """Google Document AI backend for pdfsmith."""

    name = "google_document_ai"

    def __init__(self) -> None:
        """Initialize Google Document AI backend."""
        if not AVAILABLE:
            raise ImportError(
                "google-cloud-documentai is required for Google Document AI. "
                "Install with: pip install google-cloud-documentai"
            )

        import os

        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        processor_id = os.getenv("GOOGLE_DOCUMENT_AI_PROCESSOR_ID")

        if not credentials_path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS must be set. "
                "Point it to your service account JSON file."
            )

        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set")

        if not processor_id:
            raise RuntimeError(
                "GOOGLE_DOCUMENT_AI_PROCESSOR_ID must be set. "
                "Create an OCR processor in Google Cloud Console."
            )

        # Initialize client
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)

        # Store processor name
        self.processor_name = (
            f"projects/{project_id}/locations/{location}/processors/{processor_id}"
        )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using Google Document AI.

        Note: Synchronous API has 15 page limit. For larger documents,
        the API will fail with an error.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            ValueError: If PDF exceeds 15 pages or size limits
            RuntimeError: If API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Check file size (20 MB limit for synchronous)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 20:
            raise ValueError(
                f"PDF too large ({file_size_mb:.1f} MB). "
                "Google Document AI has 20 MB limit for synchronous API."
            )

        # Check page count
        try:
            import fitz  # PyMuPDF

            pdf_doc = fitz.open(pdf_path)
            page_count = len(pdf_doc)
            pdf_doc.close()

            if page_count > 15:
                raise ValueError(
                    f"PDF has {page_count} pages. "
                    "Synchronous API limited to 15 pages. "
                    "Use async batch processing for larger documents."
                )
        except ImportError:
            pass  # Skip page check if pymupdf not available

        try:
            # Read PDF
            pdf_content = pdf_path.read_bytes()

            # Create request
            raw_document = documentai.RawDocument(
                content=pdf_content, mime_type="application/pdf"
            )

            request = documentai.ProcessRequest(
                name=self.processor_name, raw_document=raw_document
            )

            # Call API
            result = self.client.process_document(request=request)

            # Extract text
            return self._extract_text(result.document)

        except Exception as e:
            error_msg = str(e)
            if "INVALID_ARGUMENT" in error_msg:
                raise ValueError(f"Invalid PDF: {error_msg}") from e
            elif "RESOURCE_EXHAUSTED" in error_msg:
                raise RuntimeError(f"Google rate limit exceeded: {error_msg}") from e
            else:
                raise RuntimeError(f"Google Document AI error: {error_msg}") from e

    def _extract_text(self, document) -> str:
        """Extract text from Document AI response."""
        text_blocks = []

        if document.pages:
            for page in document.pages:
                if page.lines:
                    for line in page.lines:
                        # Get text from layout
                        text = self._get_text_from_layout(line.layout, document.text)
                        if text:
                            text_blocks.append(text)

        return "\n\n".join(text_blocks).strip()

    def _get_text_from_layout(self, layout, document_text: str) -> str:
        """Extract text from layout using text anchors."""
        if not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""

        text_parts = []
        for segment in layout.text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index) if segment.end_index else len(document_text)
            text_parts.append(document_text[start:end])

        return "".join(text_parts)
