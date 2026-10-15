"""Tests for commercial backends.

These tests use mocking to avoid requiring real API credentials.
Live runs require separate authorization; see tests/integration/.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF for testing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

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


class TestGoogleDocumentAIBackend:
    """Tests for Google Document AI backend."""

    def test_import(self):
        """Backend should be importable."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
            )

            assert GoogleDocumentAIBackend is not None
        except ImportError:
            pytest.skip("google-cloud-documentai not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without Google credentials."""
        try:
            from pdfsmith.backends.google_document_ai_backend import (
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
            )

            if not AVAILABLE:
                pytest.skip("google-cloud-documentai not installed")

            # Create a real PDF file with 20 pages
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas

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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                mock_client.process_document.side_effect = Exception(
                    "INVALID_ARGUMENT: Bad PDF"
                )
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                mock_client.process_document.side_effect = Exception(
                    "RESOURCE_EXHAUSTED: Quota exceeded"
                )
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
                AVAILABLE,
                GoogleDocumentAIBackend,
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
            )

            assert DatabricksBackend is not None
        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_initialization_requires_credentials(self, env_vars):
        """Backend should fail without Databricks credentials."""
        try:
            from pdfsmith.backends.databricks_backend import (
                AVAILABLE,
                DatabricksBackend,
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
                AVAILABLE,
                DatabricksBackend,
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
            from databricks.sdk.service.sql import StatementState

            from pdfsmith.backends.databricks_backend import (
                AVAILABLE,
                DatabricksBackend,
            )

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
                AVAILABLE,
                DatabricksBackend,
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
            from databricks.sdk.service.sql import StatementState

            from pdfsmith.backends.databricks_backend import (
                AVAILABLE,
                DatabricksBackend,
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
            from databricks.sdk.service.sql import StatementState

            from pdfsmith.backends.databricks_backend import (
                AVAILABLE,
                DatabricksBackend,
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
                AVAILABLE,
                DatabricksBackend,
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

                mock_client.warehouses.list.return_value = [
                    mock_standard,
                    mock_serverless,
                ]
                mock_client_class.return_value = mock_client

                backend = DatabricksBackend()
                assert backend.warehouse_id == "serverless-id"

        except ImportError:
            pytest.skip("databricks-sdk not installed")

    def test_get_warehouse_id_no_warehouses(self, env_vars):
        """_get_warehouse_id should raise if no warehouses found."""
        try:
            from pdfsmith.backends.databricks_backend import (
                AVAILABLE,
                DatabricksBackend,
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
                AVAILABLE,
                DatabricksBackend,
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
                AVAILABLE,
                DatabricksBackend,
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
