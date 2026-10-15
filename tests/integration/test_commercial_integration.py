"""Live service checks, excluded from ordinary tests regardless of environment flags.

Actual service execution requires a separate authorized input/configuration/spend
protocol. Offline SDK contract tests belong in the ordinary network-denied suite.
"""

import os
from pathlib import Path

import pytest

# Mark all tests in this module as requiring commercial credentials
pytestmark = pytest.mark.integration


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal test PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "integration_test.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)

        # Create a simple test document
        c.drawString(100, 750, "Integration Test Document")
        c.drawString(100, 700, "This document tests commercial PDF parsing APIs.")
        c.drawString(100, 650, "Expected content: Integration Test Document")

        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed")


class TestAWSTextractIntegration:
    """Integration tests for AWS Textract."""

    @pytest.mark.aws
    def test_parse_real_pdf(self, sample_pdf: Path):
        """Test parsing with real AWS Textract API."""
        # Verify credentials
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            pytest.skip("AWS_ACCESS_KEY_ID not set")
        if not os.getenv("AWS_SECRET_ACCESS_KEY"):
            pytest.skip("AWS_SECRET_ACCESS_KEY not set")

        from pdfsmith.backends.aws_textract_backend import AWSTextractBackend

        backend = AWSTextractBackend()
        result = backend.parse(sample_pdf)

        # Verify result
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Integration Test" in result or "test" in result.lower()

        print("\n✓ AWS Textract parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.aws
    def test_multipage_pdf(self, tmp_path: Path):
        """Test multi-page PDF handling."""
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            pytest.skip("AWS credentials not set")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            # Create 2-page PDF
            pdf_path = tmp_path / "multipage.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)

            c.drawString(100, 750, "Page 1 Content")
            c.showPage()
            c.drawString(100, 750, "Page 2 Content")
            c.save()

            from pdfsmith.backends.aws_textract_backend import AWSTextractBackend

            backend = AWSTextractBackend()
            result = backend.parse(pdf_path)

            assert "Page 1" in result or "page" in result.lower()
            print("\n✓ AWS Textract multi-page test passed")

        except ImportError:
            pytest.skip("reportlab not installed")


class TestAzureDocumentIntelligenceIntegration:
    """Integration tests for Azure Document Intelligence."""

    @pytest.mark.azure
    def test_parse_real_pdf(self, sample_pdf: Path):
        """Test parsing with real Azure Document Intelligence API."""
        if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
            pytest.skip("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT not set")
        if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"):
            pytest.skip("AZURE_DOCUMENT_INTELLIGENCE_KEY not set")

        from pdfsmith.backends.azure_document_intelligence_backend import (
            AzureDocumentIntelligenceBackend,
        )

        backend = AzureDocumentIntelligenceBackend()
        result = backend.parse(sample_pdf)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Integration Test" in result or "test" in result.lower()

        print("\n✓ Azure Document Intelligence parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.azure
    def test_large_pdf_handling(self, tmp_path: Path):
        """Test that Azure can handle larger files (within 500MB limit)."""
        if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
            pytest.skip("Azure credentials not set")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            # Create 10-page PDF
            pdf_path = tmp_path / "large.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)

            for i in range(10):
                c.drawString(100, 750, f"Page {i + 1} Content")
                c.showPage()
            c.save()

            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
            )

            backend = AzureDocumentIntelligenceBackend()
            result = backend.parse(pdf_path)

            assert len(result) > 0
            print("\n✓ Azure large PDF test passed")

        except ImportError:
            pytest.skip("reportlab not installed")


class TestGoogleDocumentAIIntegration:
    """Integration tests for Google Document AI."""

    @pytest.mark.google
    def test_parse_real_pdf(self, sample_pdf: Path):
        """Test parsing with real Google Document AI API."""
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set")
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")
        if not os.getenv("GOOGLE_DOCUMENT_AI_PROCESSOR_ID"):
            pytest.skip("GOOGLE_DOCUMENT_AI_PROCESSOR_ID not set")

        from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend

        backend = GoogleDocumentAIBackend()
        result = backend.parse(sample_pdf)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Integration Test" in result or "test" in result.lower()

        print("\n✓ Google Document AI parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.google
    def test_page_limit_enforcement(self, tmp_path: Path):
        """Test that Google enforces 15 page limit for sync API."""
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            pytest.skip("Google credentials not set")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            # Create 20-page PDF (exceeds 15 page limit)
            pdf_path = tmp_path / "overlimit.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)

            for i in range(20):
                c.drawString(100, 750, f"Page {i + 1}")
                c.showPage()
            c.save()

            from pdfsmith.backends.google_document_ai_backend import (
                GoogleDocumentAIBackend,
            )

            backend = GoogleDocumentAIBackend()

            # Should raise ValueError about page limit
            with pytest.raises(ValueError, match="15 pages"):
                backend.parse(pdf_path)

            print("\n✓ Google page limit enforcement working")

        except ImportError:
            pytest.skip("reportlab not installed")


class TestDatabricksIntegration:
    """Integration tests for Databricks."""

    @pytest.mark.databricks
    def test_parse_real_pdf(self, sample_pdf: Path):
        """Test parsing with real Databricks API."""
        if not os.getenv("DATABRICKS_HOST"):
            pytest.skip("DATABRICKS_HOST not set")
        if not os.getenv("DATABRICKS_CLIENT_ID"):
            pytest.skip("DATABRICKS_CLIENT_ID not set")
        if not os.getenv("DATABRICKS_CLIENT_SECRET"):
            pytest.skip("DATABRICKS_CLIENT_SECRET not set")

        from pdfsmith.backends.databricks_backend import DatabricksBackend

        backend = DatabricksBackend()
        result = backend.parse(sample_pdf)

        assert isinstance(result, str)
        assert len(result) > 0

        print("\n✓ Databricks parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.databricks
    def test_warehouse_auto_detection(self):
        """Test that Databricks can auto-detect SQL warehouse."""
        if not os.getenv("DATABRICKS_HOST"):
            pytest.skip("Databricks credentials not set")

        # Remove warehouse ID to test auto-detection
        original_warehouse = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if "DATABRICKS_WAREHOUSE_ID" in os.environ:
            del os.environ["DATABRICKS_WAREHOUSE_ID"]

        try:
            from pdfsmith.backends.databricks_backend import DatabricksBackend

            backend = DatabricksBackend()
            assert backend.warehouse_id is not None

            print(f"\n✓ Databricks auto-detected warehouse: {backend.warehouse_id}")

        finally:
            # Restore original value
            if original_warehouse:
                os.environ["DATABRICKS_WAREHOUSE_ID"] = original_warehouse


class TestCommercialBackendInvocation:
    """Check individual integrations without asserting agreement between parsers."""

    @pytest.mark.parametrize(
        "backend_name, credential_name",
        [
            ("aws_textract", "AWS_ACCESS_KEY_ID"),
            ("azure_document_intelligence", "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            ("google_document_ai", "GOOGLE_APPLICATION_CREDENTIALS"),
            ("databricks", "DATABRICKS_HOST"),
        ],
    )
    def test_explicit_backend_invocation(
        self, sample_pdf, backend_name, credential_name
    ):
        if not os.getenv(credential_name):
            pytest.skip("Provider configuration is unavailable")
        from pdfsmith.backends.registry import BACKEND_REGISTRY

        backend = BACKEND_REGISTRY[backend_name].loader()()
        result = backend.parse(sample_pdf)
        assert isinstance(result, str)
        assert "Integration Test" in result or "test" in result.lower()
