"""Tests for the pdfsmith API."""

from pathlib import Path

import pytest

from pdfsmith import __version__, available_backends, get_backend
from pdfsmith.backends.registry import BACKEND_REGISTRY


def test_version():
    """Version should be a valid semver string."""
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_backend_registry_not_empty():
    """Registry should contain backend definitions."""
    assert len(BACKEND_REGISTRY) > 0
    assert "pypdf" in BACKEND_REGISTRY
    assert "docling" in BACKEND_REGISTRY


def test_available_backends_returns_list():
    """available_backends should return a list."""
    backends = available_backends()
    assert isinstance(backends, list)


def test_backend_info_structure():
    """Backend info should have required attributes."""
    for name, info in BACKEND_REGISTRY.items():
        assert info.name == name
        assert info.description
        assert info.package
        assert info.weight in ("light", "medium", "heavy", "commercial")


def test_get_backend_invalid_name():
    """get_backend should raise ValueError for unknown backend."""
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("nonexistent_backend")


def test_get_backend_not_installed():
    """get_backend should raise ImportError if backend not installed."""
    # Find a backend that's likely not installed
    for name, info in BACKEND_REGISTRY.items():
        if not info.is_available():
            with pytest.raises(ImportError):
                get_backend(name)
            break


class TestWithBackend:
    """Tests that require at least one backend installed."""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """Create a minimal PDF for testing."""
        # Create a simple PDF using reportlab if available, otherwise skip
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            pdf_path = tmp_path / "test.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "Hello, pdfsmith!")
            c.drawString(100, 700, "This is a test document.")
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed, cannot create test PDF")

    def test_get_backend_auto_select(self):
        """get_backend with None should auto-select available backend."""
        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        backend = get_backend(None)
        assert backend is not None
        assert hasattr(backend, "parse")

    def test_parse_returns_string(self, sample_pdf: Path):
        """parse should return a string."""
        from pdfsmith import parse

        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        result = parse(sample_pdf)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_parse_contains_content(self, sample_pdf: Path):
        """parse should extract text content."""
        from pdfsmith import parse

        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        result = parse(sample_pdf)
        # Should contain at least part of our test text
        assert "pdfsmith" in result.lower() or "hello" in result.lower()

    def test_parse_file_not_found(self):
        """parse should raise FileNotFoundError for missing files."""
        from pdfsmith import parse

        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        with pytest.raises(FileNotFoundError):
            parse(Path("/nonexistent/file.pdf"))


class TestBackendSelection:
    """Tests for backend selection and registry behavior."""

    def test_get_backend_returns_singleton(self):
        """get_backend should return same instance for repeated calls."""
        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        backend_name = backends[0].name
        instance1 = get_backend(backend_name)
        instance2 = get_backend(backend_name)

        assert instance1 is instance2

    def test_default_preference_order(self):
        """Available backends should follow preference order."""
        from pdfsmith.api import DEFAULT_PREFERENCE

        backends = available_backends()
        if len(backends) < 2:
            pytest.skip("Need at least 2 backends to test order")

        # Get indices of available backends in preference list
        backend_names = [b.name for b in backends]
        indices = []
        for name in backend_names:
            if name in DEFAULT_PREFERENCE:
                indices.append(DEFAULT_PREFERENCE.index(name))

        # Indices should be in ascending order (higher priority = lower index)
        assert indices == sorted(indices), "Backends not in preference order"

    def test_available_backends_only_returns_installed(self):
        """available_backends should only include installed backends."""
        backends = available_backends()

        for backend in backends:
            assert backend.is_available(), f"{backend.name} not available"

    def test_backend_info_availability_cached(self):
        """Backend availability should be cached."""
        info = BACKEND_REGISTRY.get("pypdf")
        if info is None:
            pytest.skip("pypdf not in registry")

        # First call sets cache
        result1 = info.is_available()
        # Second call should use cache
        result2 = info.is_available()

        assert result1 == result2


class TestNoBackendsScenario:
    """Tests for when no backends are available."""

    def test_no_backends_raises_runtime_error(self, monkeypatch):
        """get_backend with no installed backends should raise RuntimeError."""
        # Mock the registry in the api module where it's imported
        import pdfsmith.api

        mock_registry = {}
        monkeypatch.setattr(pdfsmith.api, "BACKEND_REGISTRY", mock_registry)

        with pytest.raises(RuntimeError, match="No PDF parsing backends"):
            get_backend(None)
