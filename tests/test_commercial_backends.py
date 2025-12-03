"""Tests for commercial backends.

These tests use mocking to avoid requiring real API credentials.
For integration testing with real APIs, see tests/integration/test_commercial_integration.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        pdf_path = tmp_path / "test.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Test Document Title")
        c.drawString(100, 700, "This is paragraph one with some text content.")
        c.drawString(100, 650, "This is paragraph two with more content.")
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed")


@pytest.fixture
def env_vars():
    """Store and restore environment variables."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestAWSTextractBackend:
    """Tests for AWS Textract backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            assert AWSTextractBackend is not None
        except ImportError:
            pytest.skip("boto3 not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without AWS credentials."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            # Clear AWS env vars
            for key in list(os.environ.keys()):
                if key.startswith("AWS_"):
                    del os.environ[key]

            # Mock boto3 client creation
            with patch("boto3.client") as mock_client:
                mock_client.return_value = Mock()
                backend = AWSTextractBackend()
                assert backend.client is not None

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_initialization_with_profile(self, env_vars):
        """Backend should initialize with AWS_PROFILE."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            os.environ["AWS_PROFILE"] = "test-profile"

            with patch("boto3.Session") as mock_session:
                mock_session_instance = Mock()
                mock_session_instance.client.return_value = Mock()
                mock_session.return_value = mock_session_instance

                backend = AWSTextractBackend()
                assert backend.client is not None
                mock_session.assert_called_once_with(
                    profile_name="test-profile", region_name="us-east-1"
                )

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_single_page(self, sample_pdf: Path):
        """Backend should parse single-page PDF."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            # Mock boto3.client inside the test to avoid import issues
            with patch("boto3.client") as mock_boto_client:
                # Mock Textract response
                mock_client = Mock()
                mock_client.detect_document_text.return_value = {
                    "Blocks": [
                        {
                            "BlockType": "LINE",
                            "Text": "Test Document Title",
                            "Confidence": 99.5,
                        },
                        {
                            "BlockType": "LINE",
                            "Text": "This is paragraph one with some text content.",
                            "Confidence": 99.5,
                        },
                    ]
                }
                mock_boto_client.return_value = mock_client

                backend = AWSTextractBackend()
                result = backend.parse(sample_pdf)

                assert isinstance(result, str)
                assert "Test Document Title" in result
                assert mock_client.detect_document_text.called

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_file_not_found(self, tmp_path: Path):
        """Backend should raise FileNotFoundError for missing file."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_boto_client.return_value = Mock()
                backend = AWSTextractBackend()

                with pytest.raises(FileNotFoundError):
                    backend.parse(tmp_path / "nonexistent.pdf")

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_file_too_large(self, tmp_path: Path):
        """Backend should raise ValueError for files over 10 MB."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            # Create a large file (mock by creating small file and mocking stat)
            large_pdf = tmp_path / "large.pdf"
            large_pdf.write_bytes(b"fake pdf content")

            with patch("boto3.client") as mock_boto_client:
                mock_boto_client.return_value = Mock()
                backend = AWSTextractBackend()

                # Mock file size to appear as 15 MB
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = Mock(st_size=15 * 1024 * 1024)

                    with pytest.raises(ValueError, match="10 MB limit"):
                        backend.parse(large_pdf)

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_multipage_pdf(self, tmp_path: Path):
        """Backend should handle multi-page PDFs."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            # Create multi-page PDF
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter

                pdf_path = tmp_path / "multipage.pdf"
                c = canvas.Canvas(str(pdf_path), pagesize=letter)
                for i in range(3):
                    c.drawString(100, 750, f"Page {i + 1}")
                    c.showPage()
                c.save()
            except ImportError:
                pytest.skip("reportlab not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_client = Mock()
                mock_client.detect_document_text.return_value = {
                    "Blocks": [
                        {"BlockType": "LINE", "Text": "Page content"},
                    ]
                }
                mock_boto_client.return_value = mock_client

                backend = AWSTextractBackend()
                result = backend.parse(pdf_path)

                assert isinstance(result, str)
                # Should call API multiple times for multi-page
                assert mock_client.detect_document_text.call_count == 3

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_throttling_error(self, sample_pdf: Path):
        """Backend should handle throttling errors."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )
            from botocore.exceptions import ClientError

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_client = Mock()
                mock_client.detect_document_text.side_effect = ClientError(
                    {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
                    "DetectDocumentText",
                )
                mock_boto_client.return_value = mock_client

                backend = AWSTextractBackend()

                with pytest.raises(RuntimeError, match="rate limit"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_parse_invalid_parameter_error(self, sample_pdf: Path):
        """Backend should handle invalid parameter errors."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )
            from botocore.exceptions import ClientError

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_client = Mock()
                mock_client.detect_document_text.side_effect = ClientError(
                    {"Error": {"Code": "InvalidParameterException", "Message": "Invalid PDF"}},
                    "DetectDocumentText",
                )
                mock_boto_client.return_value = mock_client

                backend = AWSTextractBackend()

                with pytest.raises(ValueError, match="Invalid PDF"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_extract_blocks_filters_non_line(self):
        """_extract_blocks should only extract LINE blocks."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_boto_client.return_value = Mock()
                backend = AWSTextractBackend()

                response = {
                    "Blocks": [
                        {"BlockType": "PAGE", "Text": "Page 1"},
                        {"BlockType": "LINE", "Text": "Line 1"},
                        {"BlockType": "WORD", "Text": "Word"},
                        {"BlockType": "LINE", "Text": "Line 2"},
                        {"BlockType": "LINE", "Text": ""},  # Empty line
                    ]
                }

                blocks = backend._extract_blocks(response)
                assert blocks == ["Line 1", "Line 2"]

        except ImportError:
            pytest.skip("boto3 not installed")

    def test_extract_blocks_empty_response(self):
        """_extract_blocks should handle empty response."""
        try:
            from pdfsmith.backends.aws_textract_backend import (
                AWSTextractBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("boto3 not installed")

            with patch("boto3.client") as mock_boto_client:
                mock_boto_client.return_value = Mock()
                backend = AWSTextractBackend()

                response = {"Blocks": []}
                blocks = backend._extract_blocks(response)
                assert blocks == []

                response = {}
                blocks = backend._extract_blocks(response)
                assert blocks == []

        except ImportError:
            pytest.skip("boto3 not installed")


class TestAzureDocumentIntelligenceBackend:
    """Tests for Azure Document Intelligence backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            assert AzureDocumentIntelligenceBackend is not None
        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without Azure credentials."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            # Clear Azure env vars
            for key in ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "AZURE_DOCUMENT_INTELLIGENCE_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            with pytest.raises(RuntimeError, match="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
                AzureDocumentIntelligenceBackend()

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_initialization_missing_key(self, env_vars):
        """Backend should fail without API key."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            # Set endpoint but not key
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            for key in ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            with pytest.raises(RuntimeError, match="AZURE_DOCUMENT_INTELLIGENCE"):
                AzureDocumentIntelligenceBackend()

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_parse_with_mocked_client(self, sample_pdf: Path, env_vars):
        """Backend should parse PDF with mocked Azure client."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            # Set required env vars
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key-32-characters-long-key"

            # Mock Azure client
            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_poller = Mock()

                # Mock result structure
                mock_result = Mock()
                mock_result.pages = [
                    Mock(
                        lines=[
                            Mock(content="Test Document Title"),
                            Mock(content="This is paragraph one with some text content."),
                        ]
                    )
                ]
                mock_poller.result.return_value = mock_result
                mock_client.begin_analyze_document.return_value = mock_poller
                mock_client_class.return_value = mock_client

                backend = AzureDocumentIntelligenceBackend()
                result = backend.parse(sample_pdf)

                assert isinstance(result, str)
                assert len(result) > 0

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_parse_file_not_found(self, tmp_path: Path, env_vars):
        """Backend should raise FileNotFoundError for missing file."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"

            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ):
                backend = AzureDocumentIntelligenceBackend()

                with pytest.raises(FileNotFoundError):
                    backend.parse(tmp_path / "nonexistent.pdf")

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_parse_file_too_large(self, tmp_path: Path, env_vars):
        """Backend should raise ValueError for files over 500 MB."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            large_pdf = tmp_path / "large.pdf"
            large_pdf.write_bytes(b"fake pdf content")

            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"

            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ):
                backend = AzureDocumentIntelligenceBackend()

                # Mock file size to appear as 600 MB
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = Mock(st_size=600 * 1024 * 1024)

                    with pytest.raises(ValueError, match="500 MB limit"):
                        backend.parse(large_pdf)

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_parse_rate_limit_error(self, sample_pdf: Path, env_vars):
        """Backend should handle rate limit errors."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )
            from azure.core.exceptions import HttpResponseError

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"

            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ) as mock_client_class:
                mock_client = Mock()
                error = HttpResponseError(message="Rate limit exceeded")
                error.status_code = 429
                mock_client.begin_analyze_document.side_effect = error
                mock_client_class.return_value = mock_client

                backend = AzureDocumentIntelligenceBackend()

                with pytest.raises(RuntimeError, match="rate limit"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_parse_invalid_pdf_error(self, sample_pdf: Path, env_vars):
        """Backend should handle invalid PDF errors."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )
            from azure.core.exceptions import HttpResponseError

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"

            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ) as mock_client_class:
                mock_client = Mock()
                error = HttpResponseError(message="Invalid document format")
                error.status_code = 400
                mock_client.begin_analyze_document.side_effect = error
                mock_client_class.return_value = mock_client

                backend = AzureDocumentIntelligenceBackend()

                with pytest.raises(ValueError, match="Invalid PDF"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")

    def test_extract_text_empty_pages(self, env_vars):
        """_extract_text should handle empty pages."""
        try:
            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("azure-ai-documentintelligence not installed")

            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                "https://test.cognitiveservices.azure.com/"
            )
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "test-key"

            with patch(
                "pdfsmith.backends.azure_document_intelligence_backend.DocumentIntelligenceClient"
            ):
                backend = AzureDocumentIntelligenceBackend()

                # Test with None pages
                mock_result = Mock()
                mock_result.pages = None
                assert backend._extract_text(mock_result) == ""

                # Test with empty pages list
                mock_result.pages = []
                assert backend._extract_text(mock_result) == ""

                # Test with pages but no lines
                mock_result.pages = [Mock(lines=None)]
                assert backend._extract_text(mock_result) == ""

        except ImportError:
            pytest.skip("azure-ai-documentintelligence not installed")


class TestGoogleDocumentAIBackend:
    """Tests for Google Document AI backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            assert GoogleDocumentAIBackend is not None
        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without Google credentials."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            # Clear Google env vars
            for key in [
                "GOOGLE_APPLICATION_CREDENTIALS",
                "GOOGLE_CLOUD_PROJECT",
                "GOOGLE_DOCUMENT_AI_PROCESSOR_ID",
            ]:
                if key in os.environ:
                    del os.environ[key]

            with pytest.raises(RuntimeError, match="GOOGLE_APPLICATION_CREDENTIALS"):
                GoogleDocumentAIBackend()

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_initialization_missing_project(self, env_vars):
        """Backend should fail without project ID."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            for key in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_DOCUMENT_AI_PROCESSOR_ID"]:
                if key in os.environ:
                    del os.environ[key]

            with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
                GoogleDocumentAIBackend()

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_initialization_missing_processor(self, env_vars):
        """Backend should fail without processor ID."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            if "GOOGLE_DOCUMENT_AI_PROCESSOR_ID" in os.environ:
                del os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"]

            with pytest.raises(RuntimeError, match="GOOGLE_DOCUMENT_AI_PROCESSOR_ID"):
                GoogleDocumentAIBackend()

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_with_mocked_client(self, sample_pdf: Path, env_vars):
        """Backend should parse PDF with mocked client."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ) as mock_client_class:
                mock_client = Mock()

                # Mock result
                mock_document = Mock()
                mock_layout = Mock()
                mock_segment = Mock()
                mock_segment.start_index = 0
                mock_segment.end_index = 10
                mock_layout.text_anchor = Mock()
                mock_layout.text_anchor.text_segments = [mock_segment]

                mock_line = Mock()
                mock_line.layout = mock_layout

                mock_page = Mock()
                mock_page.lines = [mock_line]

                mock_document.pages = [mock_page]
                mock_document.text = "Test text content"

                mock_response = Mock()
                mock_response.document = mock_document
                mock_client.process_document.return_value = mock_response
                mock_client_class.return_value = mock_client

                backend = GoogleDocumentAIBackend()
                result = backend.parse(sample_pdf)

                assert isinstance(result, str)

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_file_not_found(self, tmp_path: Path, env_vars):
        """Backend should raise FileNotFoundError for missing file."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ):
                backend = GoogleDocumentAIBackend()

                with pytest.raises(FileNotFoundError):
                    backend.parse(tmp_path / "nonexistent.pdf")

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_file_too_large(self, tmp_path: Path, env_vars):
        """Backend should raise ValueError for files over 20 MB."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            large_pdf = tmp_path / "large.pdf"
            large_pdf.write_bytes(b"fake pdf content")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ):
                backend = GoogleDocumentAIBackend()

                # Mock file size to appear as 25 MB
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = Mock(st_size=25 * 1024 * 1024)

                    with pytest.raises(ValueError, match="20 MB limit"):
                        backend.parse(large_pdf)

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_page_limit_exceeded(self, tmp_path: Path, env_vars):
        """Backend should raise ValueError for PDFs over 15 pages."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            # Create a real PDF file with 20 pages
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter

                pdf_path = tmp_path / "manypage.pdf"
                c = canvas.Canvas(str(pdf_path), pagesize=letter)
                for i in range(20):
                    c.drawString(100, 750, f"Page {i + 1}")
                    c.showPage()
                c.save()
            except ImportError:
                pytest.skip("reportlab not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ):
                backend = GoogleDocumentAIBackend()

                # The real fitz will read the 20-page PDF and raise ValueError
                with pytest.raises(ValueError, match="15 pages"):
                    backend.parse(pdf_path)

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_invalid_argument_error(self, sample_pdf: Path, env_vars):
        """Backend should handle INVALID_ARGUMENT errors."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.process_document.side_effect = Exception("INVALID_ARGUMENT: Bad PDF")
                mock_client_class.return_value = mock_client

                backend = GoogleDocumentAIBackend()

                with pytest.raises(ValueError, match="Invalid PDF"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_parse_rate_limit_error(self, sample_pdf: Path, env_vars):
        """Backend should handle RESOURCE_EXHAUSTED errors."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.process_document.side_effect = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
                mock_client_class.return_value = mock_client

                backend = GoogleDocumentAIBackend()

                with pytest.raises(RuntimeError, match="rate limit"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_extract_text_empty_pages(self, env_vars):
        """_extract_text should handle empty document."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ):
                backend = GoogleDocumentAIBackend()

                # Test with None pages
                mock_document = Mock()
                mock_document.pages = None
                assert backend._extract_text(mock_document) == ""

                # Test with empty pages
                mock_document.pages = []
                assert backend._extract_text(mock_document) == ""

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_get_text_from_layout_no_anchor(self, env_vars):
        """_get_text_from_layout should handle missing text_anchor."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-creds.json"
            os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
            os.environ["GOOGLE_DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"

            with patch(
                "pdfsmith.backends.google_document_ai_backend.documentai.DocumentProcessorServiceClient"
            ):
                backend = GoogleDocumentAIBackend()

                # Test with no text_anchor
                mock_layout = Mock()
                mock_layout.text_anchor = None
                assert backend._get_text_from_layout(mock_layout, "test") == ""

                # Test with no text_segments
                mock_layout.text_anchor = Mock()
                mock_layout.text_anchor.text_segments = None
                assert backend._get_text_from_layout(mock_layout, "test") == ""

        except ImportError:
            pytest.skip("google-cloud-documentai not installed")


class TestDatabricksBackend:
    """Tests for Databricks backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            assert DatabricksBackend is not None
        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without Databricks credentials."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            # Clear Databricks env vars
            for key in list(os.environ.keys()):
                if key.startswith("DATABRICKS_"):
                    del os.environ[key]

            with pytest.raises(RuntimeError, match="DATABRICKS_HOST"):
                DatabricksBackend()

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_initialization_missing_client_credentials(self, env_vars):
        """Backend should fail without client credentials."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            # Clear all and set only host
            for key in list(os.environ.keys()):
                if key.startswith("DATABRICKS_"):
                    del os.environ[key]
            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"

            with pytest.raises(RuntimeError, match="DATABRICKS_CLIENT_ID"):
                DatabricksBackend()

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_with_mocked_client(self, sample_pdf: Path, env_vars):
        """Backend should parse PDF with mocked Databricks client."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )
            from databricks.sdk.service.sql import StatementState

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            # Set required env vars
            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            # Mock Databricks SDK
            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()

                # Mock statement execution response
                mock_status = Mock()
                mock_status.state = StatementState.SUCCEEDED
                mock_status.error = None

                mock_result = Mock()
                mock_result.data_array = [['{"elements": [{"text": "Test Document"}]}']]

                mock_statement = Mock()
                mock_statement.status = mock_status
                mock_statement.result = mock_result

                mock_client.statement_execution.execute_statement.return_value = (
                    mock_statement
                )
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()
                result = backend.parse(sample_pdf)

                assert isinstance(result, str)
                assert "Test Document" in result

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_file_not_found(self, tmp_path: Path, env_vars):
        """Backend should raise FileNotFoundError for missing file."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()

                with pytest.raises(FileNotFoundError):
                    backend.parse(tmp_path / "nonexistent.pdf")

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_sql_execution_failure(self, sample_pdf: Path, env_vars):
        """Backend should handle SQL execution failures."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )
            from databricks.sdk.service.sql import StatementState

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()

                # Mock failed statement
                mock_error = Mock()
                mock_error.message = "SQL execution failed"

                mock_status = Mock()
                mock_status.state = StatementState.FAILED
                mock_status.error = mock_error

                mock_statement = Mock()
                mock_statement.status = mock_status
                mock_statement.result = None

                mock_client.statement_execution.execute_statement.return_value = (
                    mock_statement
                )
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()

                with pytest.raises(RuntimeError, match="SQL execution failed"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_empty_result(self, sample_pdf: Path, env_vars):
        """Backend should handle empty results gracefully."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )
            from databricks.sdk.service.sql import StatementState

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()

                mock_status = Mock()
                mock_status.state = StatementState.SUCCEEDED

                mock_result = Mock()
                mock_result.data_array = None  # Empty result

                mock_statement = Mock()
                mock_statement.status = mock_status
                mock_statement.result = mock_result

                mock_client.statement_execution.execute_statement.return_value = (
                    mock_statement
                )
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()
                result = backend.parse(sample_pdf)

                assert result == ""

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_get_warehouse_id_prefers_serverless(self, env_vars):
        """_get_warehouse_id should prefer serverless warehouses."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            # Don't set warehouse ID to test auto-detection

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()

                # Create mock warehouses
                mock_serverless = Mock()
                mock_serverless.name = "Serverless Warehouse"
                mock_serverless.id = "serverless-id"

                mock_standard = Mock()
                mock_standard.name = "Standard Warehouse"
                mock_standard.id = "standard-id"

                mock_client.warehouses.list.return_value = [mock_standard, mock_serverless]
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()
                assert backend.warehouse_id == "serverless-id"

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_get_warehouse_id_no_warehouses(self, env_vars):
        """_get_warehouse_id should raise if no warehouses found."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            # Don't set warehouse ID

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="No SQL warehouses found"):
                    DatabricksBackend()

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_result_json(self, env_vars):
        """_parse_result should handle valid JSON."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()

                # Test valid JSON with elements
                result = backend._parse_result(
                    '{"elements": [{"text": "Line 1"}, {"text": "Line 2"}]}'
                )
                assert "Line 1" in result
                assert "Line 2" in result

                # Test empty elements
                result = backend._parse_result('{"elements": []}')
                assert result == ""

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_parse_result_invalid_json(self, env_vars):
        """_parse_result should handle non-JSON strings."""
        try:
            from pdfsmith.backends.databricks_backend import (
                DatabricksBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("databricks-sdk not installed")

            os.environ["DATABRICKS_HOST"] = "https://test.cloud.databricks.com"
            os.environ["DATABRICKS_CLIENT_ID"] = "test-client-id"
            os.environ["DATABRICKS_CLIENT_SECRET"] = "test-secret"
            os.environ["DATABRICKS_WAREHOUSE_ID"] = "test-warehouse"

            with patch(
                "pdfsmith.backends.databricks_backend.WorkspaceClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.warehouses.list.return_value = []
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()

                # Invalid JSON should return as-is
                result = backend._parse_result("Plain text result")
                assert result == "Plain text result"

        except ImportError:
            pytest.skip("databricks-sdk not installed")


class TestLlamaParseBackend:
    """Tests for LlamaParse backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            assert LlamaParseBackend is not None
        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_missing_api_key(self, env_vars):
        """Backend should fail without API key."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            # Clear API key
            os.environ.pop("LLAMA_CLOUD_API_KEY", None)

            with pytest.raises(ValueError, match="LLAMA_CLOUD_API_KEY"):
                LlamaParseBackend()

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_invalid_parsing_mode(self, env_vars):
        """Backend should reject invalid parsing mode."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse"):
                with pytest.raises(ValueError, match="Invalid parsing_mode"):
                    LlamaParseBackend(parsing_mode="invalid")

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_initialization_with_api_key(self, env_vars):
        """Backend should initialize with API key."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_class.return_value = mock_client

                backend = LlamaParseBackend()
                assert backend.client is mock_client
                assert backend.parsing_mode == "cost_effective"

                # Verify LlamaParse was called with correct params
                mock_class.assert_called_once_with(
                    api_key="test-api-key",
                    result_type="markdown",
                    language="en",
                    verbose=False,
                )

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_initialization_with_custom_params(self, env_vars):
        """Backend should accept custom parsing mode and language."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_class.return_value = mock_client

                backend = LlamaParseBackend(parsing_mode="premium", language="de")
                assert backend.parsing_mode == "premium"
                assert backend.language == "de"

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parse_file_not_found(self, env_vars, tmp_path):
        """Backend should raise FileNotFoundError for missing file."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse"):
                backend = LlamaParseBackend()

                with pytest.raises(FileNotFoundError):
                    backend.parse(tmp_path / "nonexistent.pdf")

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parse_with_mocked_client(self, env_vars, sample_pdf):
        """Backend should parse PDF using LlamaParse."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            # Create mock document objects
            mock_doc1 = Mock()
            mock_doc1.text = "# Document Title\n\nFirst paragraph."

            mock_doc2 = Mock()
            mock_doc2.text = "Second paragraph with more content."

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_client.load_data.return_value = [mock_doc1, mock_doc2]
                mock_class.return_value = mock_client

                backend = LlamaParseBackend()
                result = backend.parse(sample_pdf)

                assert "# Document Title" in result
                assert "First paragraph" in result
                assert "Second paragraph" in result

                mock_client.load_data.assert_called_once_with(str(sample_pdf))

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parse_with_content_attribute(self, env_vars, sample_pdf):
        """Backend should handle documents with content attribute."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            # Create mock document with content instead of text
            mock_doc = Mock(spec=[])  # No text attribute
            mock_doc.content = "Content from content attribute"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_client.load_data.return_value = [mock_doc]
                mock_class.return_value = mock_client

                backend = LlamaParseBackend()
                result = backend.parse(sample_pdf)

                assert "Content from content attribute" in result

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parse_empty_documents(self, env_vars, sample_pdf):
        """Backend should handle empty document list."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_client.load_data.return_value = []
                mock_class.return_value = mock_client

                backend = LlamaParseBackend()
                result = backend.parse(sample_pdf)

                assert result == ""

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parse_api_error(self, env_vars, sample_pdf):
        """Backend should wrap API errors in RuntimeError."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"

            with patch("pdfsmith.backends.llamaparse_backend.LlamaParse") as mock_class:
                mock_client = Mock()
                mock_client.load_data.side_effect = Exception("API rate limit exceeded")
                mock_class.return_value = mock_client

                backend = LlamaParseBackend()

                with pytest.raises(RuntimeError, match="LlamaParse processing failed"):
                    backend.parse(sample_pdf)

        except ImportError:
            pytest.skip("llama-parse not installed")

    def test_parsing_modes(self):
        """Backend should define correct parsing modes."""
        try:
            from pdfsmith.backends.llamaparse_backend import (
                LlamaParseBackend,
                AVAILABLE,
            )

            if not AVAILABLE:
                pytest.skip("llama-parse not installed")

            assert "fast" in LlamaParseBackend.PARSING_MODES
            assert "cost_effective" in LlamaParseBackend.PARSING_MODES
            assert "agentic" in LlamaParseBackend.PARSING_MODES
            assert "premium" in LlamaParseBackend.PARSING_MODES

            # Verify costs
            assert LlamaParseBackend.PARSING_MODES["fast"] == 0.001
            assert LlamaParseBackend.PARSING_MODES["cost_effective"] == 0.003
            assert LlamaParseBackend.PARSING_MODES["agentic"] == 0.01
            assert LlamaParseBackend.PARSING_MODES["premium"] == 0.09

        except ImportError:
            pytest.skip("llama-parse not installed")


class TestCommercialBackendRegistry:
    """Tests for commercial backend registration."""

    def test_commercial_backends_registered(self):
        """All commercial backends should be in registry."""
        from pdfsmith.backends.registry import BACKEND_REGISTRY

        commercial_backends = [
            "aws_textract",
            "azure_document_intelligence",
            "google_document_ai",
            "databricks",
            "llamaparse",
        ]

        for backend_name in commercial_backends:
            assert backend_name in BACKEND_REGISTRY
            info = BACKEND_REGISTRY[backend_name]
            assert info.weight == "commercial"

    def test_commercial_backend_availability_check(self):
        """Commercial backends should report availability correctly."""
        from pdfsmith.backends.registry import BACKEND_REGISTRY

        # Check each commercial backend
        for backend_name in [
            "aws_textract",
            "azure_document_intelligence",
            "google_document_ai",
            "databricks",
            "llamaparse",
        ]:
            info = BACKEND_REGISTRY[backend_name]
            # Should not raise error, just return True/False
            available = info.is_available()
            assert isinstance(available, bool)
