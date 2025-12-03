"""Tests for async PDF parsing functionality."""

import asyncio
import functools
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pdfsmith import available_backends, parse_async


def requires_backend(func):
    """Skip test if no backends are installed."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not available_backends():
            pytest.skip("No backends installed")
        return await func(*args, **kwargs)

    return wrapper


@pytest.mark.asyncio
class TestAsyncParsing:
    """Tests for parse_async function."""

    @requires_backend
    async def test_parse_async_basic(self, sample_pdf):
        """parse_async should return markdown string."""
        result = await parse_async(sample_pdf)

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_parse_async_with_backend(self, sample_pdf):
        """parse_async should accept backend parameter."""
        backends = available_backends()
        if not backends:
            pytest.skip("No backends installed")

        backend_name = backends[0].name
        result = await parse_async(sample_pdf, backend=backend_name)

        assert isinstance(result, str)

    async def test_parse_async_file_not_found(self, tmp_path):
        """parse_async should raise FileNotFoundError for missing file."""
        nonexistent = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            await parse_async(nonexistent)

    async def test_parse_async_executor_fallback(self, sample_pdf):
        """parse_async should use executor when backend lacks parse_async."""
        # Create a mock backend without parse_async
        mock_backend = MagicMock()
        mock_backend.parse.return_value = "# Sync Result"
        del mock_backend.parse_async  # Ensure no parse_async method

        with patch("pdfsmith.api.get_backend", return_value=mock_backend):
            result = await parse_async(sample_pdf)

        assert result == "# Sync Result"
        mock_backend.parse.assert_called_once()

    async def test_parse_async_native_async_method(self, sample_pdf):
        """parse_async should use backend's parse_async when available."""
        # Create a mock backend WITH parse_async
        mock_backend = MagicMock()
        mock_backend.parse_async = AsyncMock(return_value="# Async Result")

        with patch("pdfsmith.api.get_backend", return_value=mock_backend):
            result = await parse_async(sample_pdf)

        assert result == "# Async Result"
        mock_backend.parse_async.assert_called_once()
        mock_backend.parse.assert_not_called()

    async def test_parse_async_backend_not_installed(self, sample_pdf):
        """parse_async should raise ImportError for missing backend."""
        with patch(
            "pdfsmith.api.get_backend",
            side_effect=ImportError("Backend not installed"),
        ):
            with pytest.raises(ImportError):
                await parse_async(sample_pdf, backend="nonexistent")

    @requires_backend
    async def test_parse_async_concurrent_multiple_files(self, sample_pdf, multipage_pdf):
        """parse_async should handle concurrent parsing."""
        results = await asyncio.gather(
            parse_async(sample_pdf),
            parse_async(multipage_pdf),
        )

        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)
        assert all(len(r) > 0 for r in results)

    @requires_backend
    async def test_parse_async_with_path_object(self, sample_pdf):
        """parse_async should accept Path object."""
        result = await parse_async(Path(sample_pdf))
        assert isinstance(result, str)

    @requires_backend
    async def test_parse_async_with_string_path(self, sample_pdf):
        """parse_async should accept string path."""
        result = await parse_async(str(sample_pdf))
        assert isinstance(result, str)


@pytest.mark.asyncio
class TestAsyncEdgeCases:
    """Edge case tests for async parsing."""

    @requires_backend
    async def test_parse_async_empty_pdf(self, empty_pdf):
        """parse_async should handle empty PDFs gracefully."""
        # Should not raise, may return empty or minimal string
        result = await parse_async(empty_pdf)
        assert isinstance(result, str)

    async def test_parse_async_error_propagation(self, sample_pdf):
        """Errors from backend should propagate correctly."""
        mock_backend = MagicMock()
        mock_backend.parse.side_effect = RuntimeError("Parse failed")
        del mock_backend.parse_async

        with patch("pdfsmith.api.get_backend", return_value=mock_backend):
            with pytest.raises(RuntimeError, match="Parse failed"):
                await parse_async(sample_pdf)

    async def test_parse_async_async_error_propagation(self, sample_pdf):
        """Errors from async backend should propagate correctly."""
        mock_backend = MagicMock()
        mock_backend.parse_async = AsyncMock(side_effect=RuntimeError("Async failed"))

        with patch("pdfsmith.api.get_backend", return_value=mock_backend):
            with pytest.raises(RuntimeError, match="Async failed"):
                await parse_async(sample_pdf)
