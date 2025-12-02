"""AWS Textract backend for pdfsmith.

AWS Textract provides commercial-grade OCR and text extraction using machine learning.

Requirements:
    - boto3
    - pymupdf (for multi-page support)

Configuration:
    Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables,
    or use AWS_PROFILE for profile-based authentication.

Cost: $1.50 per 1,000 pages (DetectDocumentText API)
Limits: 10 MB file size, 3,000 pages (synchronous API)
"""

from pathlib import Path

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from pdfsmith.backends.registry import BaseBackend


class AWSTextractBackend(BaseBackend):
    """AWS Textract backend for pdfsmith."""

    name = "aws_textract"

    def __init__(self) -> None:
        """Initialize AWS Textract backend."""
        if not AVAILABLE:
            raise ImportError(
                "boto3 is required for AWS Textract. Install with: pip install boto3"
            )

        import os

        # Initialize boto3 client
        aws_profile = os.getenv("AWS_PROFILE")
        region = os.getenv("AWS_REGION", "us-east-1")

        try:
            if aws_profile:
                session = boto3.Session(profile_name=aws_profile, region_name=region)
                self.client = session.client("textract")
            else:
                self.client = boto3.client("textract", region_name=region)
        except BotoCoreError as e:
            raise RuntimeError(f"Failed to initialize AWS Textract client: {e}") from e

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using AWS Textract.

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

        # Check file size (10 MB limit)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 10:
            raise ValueError(
                f"PDF too large ({file_size_mb:.1f} MB). "
                "AWS Textract has 10 MB limit for synchronous API."
            )

        try:
            # Load PDF
            try:
                import fitz  # PyMuPDF
            except ImportError as err:
                raise ImportError(
                    "PyMuPDF (fitz) required for multi-page support. "
                    "Install with: pip install pymupdf"
                ) from err

            pdf_bytes = pdf_path.read_bytes()
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(pdf_doc)

            all_text_blocks = []

            if page_count == 1:
                # Single page - send PDF directly
                pdf_doc.close()
                doc = {"Bytes": pdf_bytes}
                response = self.client.detect_document_text(Document=doc)
                all_text_blocks = self._extract_blocks(response)
            else:
                # Multi-page - convert to PNG per page
                for page_num in range(page_count):
                    page = pdf_doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    png_bytes = pix.tobytes("png")

                    doc = {"Bytes": png_bytes}
                    response = self.client.detect_document_text(Document=doc)
                    page_blocks = self._extract_blocks(response)
                    all_text_blocks.extend(page_blocks)

                pdf_doc.close()

            # Join with paragraph breaks
            return "\n\n".join(all_text_blocks).strip()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ThrottlingException":
                raise RuntimeError(f"AWS Textract rate limit: {error_msg}") from e
            elif error_code == "InvalidParameterException":
                raise ValueError(f"Invalid PDF: {error_msg}") from e
            else:
                msg = f"AWS Textract error ({error_code}): {error_msg}"
                raise RuntimeError(msg) from e

        except BotoCoreError as e:
            raise RuntimeError(f"AWS SDK error: {e}") from e

    def _extract_blocks(self, response: dict) -> list[str]:
        """Extract text blocks from Textract response."""
        text_blocks = []
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                text = block.get("Text", "").strip()
                if text:
                    text_blocks.append(text)
        return text_blocks
