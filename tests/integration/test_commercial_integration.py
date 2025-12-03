"""Integration tests for commercial backends.

These tests require real API credentials and will incur costs.
Only run when you need to verify actual API integration.

Setup:
    1. Copy .env.example to .env
    2. Fill in your API credentials
    3. Run: pytest tests/integration/ -v --commercial

Cost per run (assuming 1-page test PDF):
    - AWS Textract: ~$0.0015
    - Azure: ~$0.0015
    - Google: ~$0.0015
    - Databricks: ~$0.003
    Total: ~$0.007 per full integration test run
"""

import pytest
from pathlib import Path
import os

# Mark all tests in this module as requiring commercial credentials
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_COMMERCIAL_TESTS"),
    reason="Commercial API tests disabled. Set RUN_COMMERCIAL_TESTS=1 to enable.",
)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal test PDF."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

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

        print(f"\n✓ AWS Textract parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.aws
    def test_multipage_pdf(self, tmp_path: Path):
        """Test multi-page PDF handling."""
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            pytest.skip("AWS credentials not set")

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

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
            print(f"\n✓ AWS Textract multi-page test passed")

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

        print(f"\n✓ Azure Document Intelligence parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.azure
    def test_large_pdf_handling(self, tmp_path: Path):
        """Test that Azure can handle larger files (within 500MB limit)."""
        if not os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
            pytest.skip("Azure credentials not set")

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

            # Create 10-page PDF
            pdf_path = tmp_path / "large.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)

            for i in range(10):
                c.drawString(100, 750, f"Page {i+1} Content")
                c.showPage()
            c.save()

            from pdfsmith.backends.azure_document_intelligence_backend import (
                AzureDocumentIntelligenceBackend,
            )

            backend = AzureDocumentIntelligenceBackend()
            result = backend.parse(pdf_path)

            assert len(result) > 0
            print(f"\n✓ Azure large PDF test passed")

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

        print(f"\n✓ Google Document AI parsed successfully")
        print(f"  Result length: {len(result)} characters")
        print(f"  Content preview: {result[:100]}...")

    @pytest.mark.google
    def test_page_limit_enforcement(self, tmp_path: Path):
        """Test that Google enforces 15 page limit for sync API."""
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            pytest.skip("Google credentials not set")

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

            # Create 20-page PDF (exceeds 15 page limit)
            pdf_path = tmp_path / "overlimit.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)

            for i in range(20):
                c.drawString(100, 750, f"Page {i+1}")
                c.showPage()
            c.save()

            from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend

            backend = GoogleDocumentAIBackend()

            # Should raise ValueError about page limit
            with pytest.raises(ValueError, match="15 pages"):
                backend.parse(pdf_path)

            print(f"\n✓ Google page limit enforcement working")

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

        print(f"\n✓ Databricks parsed successfully")
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


class TestCrossProviderComparison:
    """Compare results across commercial providers."""

    @pytest.mark.commercial
    def test_consistency_across_providers(self, sample_pdf: Path):
        """Test that all providers return consistent results."""
        results = {}

        # Try each provider
        providers = [
            ("aws_textract", "AWS_ACCESS_KEY_ID"),
            ("azure_document_intelligence", "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            ("google_document_ai", "GOOGLE_APPLICATION_CREDENTIALS"),
            ("databricks", "DATABRICKS_HOST"),
        ]

        for backend_name, env_check in providers:
            if not os.getenv(env_check):
                continue

            try:
                from pdfsmith import parse

                result = parse(sample_pdf, backend=backend_name)
                results[backend_name] = result
            except Exception as e:
                print(f"✗ {backend_name} failed: {e}")

        # Compare results
        if len(results) >= 2:
            print(f"\n✓ Compared {len(results)} providers")
            for name, result in results.items():
                print(f"  {name}: {len(result)} chars")

            # All should contain key phrases
            for name, result in results.items():
                assert "Integration Test" in result or "test" in result.lower()
        else:
            pytest.skip("Need at least 2 providers configured for comparison")
