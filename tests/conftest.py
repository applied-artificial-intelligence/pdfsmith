"""Shared test fixtures and configuration for pdfsmith tests."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF for testing.

    Creates a simple single-page PDF with test text using reportlab.
    Skips the test if reportlab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "test.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Hello, pdfsmith!")
        c.drawString(100, 700, "This is a test document.")
        c.drawString(100, 650, "Page 1 of 1")
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed, cannot create test PDF")


@pytest.fixture
def multipage_pdf(tmp_path: Path) -> Path:
    """Create a multi-page PDF for testing pagination handling."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "multipage.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)

        for i in range(3):
            c.drawString(100, 750, f"Page {i + 1} Header")
            c.drawString(100, 700, f"Content for page {i + 1}")
            c.drawString(100, 650, f"This is page {i + 1} of 3")
            c.showPage()

        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed, cannot create test PDF")


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create an empty PDF (no text content) for edge case testing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "empty.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.showPage()  # Empty page
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not installed, cannot create test PDF")


@contextmanager
def env_vars(**kwargs) -> Generator[None, None, None]:
    """Context manager to temporarily set environment variables.

    Restores original values (or removes if not present) on exit.

    Usage:
        with env_vars(PDFSMITH_DOCLING_OCR="true"):
            # test code here
    """
    original = {}
    for key, value in kwargs.items():
        original[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    try:
        yield
    finally:
        for key, orig_value in original.items():
            if orig_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = orig_value


@pytest.fixture
def isolated_env(monkeypatch):
    """Fixture that clears all PDFSMITH_* environment variables."""
    # Find and remove all PDFSMITH_ prefixed env vars
    pdfsmith_vars = [k for k in os.environ if k.startswith("PDFSMITH_")]
    for var in pdfsmith_vars:
        monkeypatch.delenv(var, raising=False)

    # Also clear backend-specific vars that might interfere
    backend_vars = [
        "DOCLING_OCR",
        "KREUZBERG_OCR",
        "UNSTRUCTURED_STRATEGY",
    ]
    for var in backend_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def temp_config_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary config directory structure.

    Creates .pdfsmith/ directory and patches Path.home() to use tmp_path.
    """
    config_dir = tmp_path / ".pdfsmith"
    config_dir.mkdir()

    # Patch home directory to use tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    return config_dir


@pytest.fixture
def mock_backend():
    """Create a mock backend instance for testing."""
    mock = MagicMock()
    mock.name = "mock_backend"
    mock.parse.return_value = "# Mock Output\n\nThis is mock markdown."
    return mock


@pytest.fixture
def mock_backend_registry(monkeypatch):
    """Fixture to replace the backend registry with a mock version."""
    from pdfsmith.backends.registry import BackendInfo

    mock_registry = {
        "mock_light": BackendInfo(
            name="mock_light",
            description="Mock light backend",
            package="mock-light",
            weight="light",
            loader=lambda: MagicMock,
        ),
        "mock_heavy": BackendInfo(
            name="mock_heavy",
            description="Mock heavy backend",
            package="mock-heavy",
            weight="heavy",
            loader=lambda: MagicMock,
        ),
    }

    monkeypatch.setattr(
        "pdfsmith.backends.registry.BACKEND_REGISTRY", mock_registry
    )
    return mock_registry
