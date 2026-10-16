"""Static commercial registry checks; SDK contracts live in provider tests."""


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
