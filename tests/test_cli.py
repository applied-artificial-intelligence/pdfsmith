"""Tests for the pdfsmith CLI."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdfsmith.cli import cmd_backends, cmd_parse, main


class TestMain:
    """Tests for the main() entry point."""

    def test_no_args_shows_help(self, capsys):
        """Running with no args should show help and return 0."""
        with patch.object(sys, "argv", ["pdfsmith"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Convert PDF files to Markdown" in captured.out
        assert "Commands" in captured.out

    def test_version_flag(self, capsys):
        """--version should print version and exit."""
        with patch.object(sys, "argv", ["pdfsmith", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "pdfsmith" in captured.out

    def test_parse_command_routes_correctly(self, sample_pdf):
        """parse command should route to cmd_parse."""
        with patch.object(sys, "argv", ["pdfsmith", "parse", str(sample_pdf)]):
            with patch("pdfsmith.cli.cmd_parse", return_value=0) as mock_cmd:
                result = main()

        assert result == 0
        mock_cmd.assert_called_once()

    def test_backends_command_routes_correctly(self):
        """backends command should route to cmd_backends."""
        with patch.object(sys, "argv", ["pdfsmith", "backends"]):
            with patch("pdfsmith.cli.cmd_backends", return_value=0) as mock_cmd:
                result = main()

        assert result == 0
        mock_cmd.assert_called_once()


class TestParseCommand:
    """Tests for the parse command."""

    def test_parse_to_stdout(self, sample_pdf, capsys):
        """Parse without -o should print to stdout."""
        mock_markdown = "# Test Document\n\nHello, pdfsmith!"

        with patch("pdfsmith.cli.parse", return_value=mock_markdown):
            with patch.object(
                sys, "argv", ["pdfsmith", "parse", str(sample_pdf)]
            ):
                result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert mock_markdown in captured.out

    def test_parse_to_file(self, sample_pdf, tmp_path, capsys):
        """Parse with -o should write to file."""
        mock_markdown = "# Test Document\n\nHello, pdfsmith!"
        output_file = tmp_path / "output.md"

        with patch("pdfsmith.cli.parse", return_value=mock_markdown):
            with patch.object(
                sys,
                "argv",
                ["pdfsmith", "parse", str(sample_pdf), "-o", str(output_file)],
            ):
                result = main()

        assert result == 0
        assert output_file.exists()
        assert output_file.read_text() == mock_markdown
        captured = capsys.readouterr()
        assert f"Written to {output_file}" in captured.out

    def test_parse_file_not_found(self, tmp_path, capsys):
        """Parse with non-existent file should error."""
        nonexistent = tmp_path / "nonexistent.pdf"

        with patch.object(
            sys, "argv", ["pdfsmith", "parse", str(nonexistent)]
        ):
            result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: File not found" in captured.err

    def test_parse_with_backend(self, sample_pdf):
        """Parse with -b should pass backend to parse()."""
        with patch("pdfsmith.cli.parse", return_value="# Test") as mock_parse:
            with patch.object(
                sys,
                "argv",
                ["pdfsmith", "parse", str(sample_pdf), "-b", "pypdf"],
            ):
                result = main()

        assert result == 0
        mock_parse.assert_called_once()
        call_kwargs = mock_parse.call_args[1]
        assert call_kwargs["backend"] == "pypdf"

    def test_parse_import_error(self, sample_pdf, capsys):
        """ImportError during parse should be handled gracefully."""
        with patch(
            "pdfsmith.cli.parse",
            side_effect=ImportError("Backend 'marker' not installed"),
        ):
            with patch.object(
                sys, "argv", ["pdfsmith", "parse", str(sample_pdf)]
            ):
                result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "not installed" in captured.err

    def test_parse_generic_error(self, sample_pdf, capsys):
        """Generic exception during parse should be handled gracefully."""
        with patch(
            "pdfsmith.cli.parse",
            side_effect=Exception("PDF is corrupted"),
        ):
            with patch.object(
                sys, "argv", ["pdfsmith", "parse", str(sample_pdf)]
            ):
                result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error parsing PDF:" in captured.err
        assert "corrupted" in captured.err


class TestBackendsCommand:
    """Tests for the backends command."""

    def test_backends_lists_available(self, capsys):
        """backends command should list installed backends."""
        from pdfsmith.backends.registry import BackendInfo

        mock_backends = [
            BackendInfo(
                name="pypdf",
                description="Pure Python PDF library",
                package="pypdf",
                weight="light",
                loader=lambda: MagicMock,
            ),
            BackendInfo(
                name="docling",
                description="IBM document understanding",
                package="docling",
                weight="heavy",
                loader=lambda: MagicMock,
            ),
        ]

        with patch("pdfsmith.cli.available_backends", return_value=mock_backends):
            result = cmd_backends()

        assert result == 0
        captured = capsys.readouterr()
        assert "pypdf" in captured.out
        assert "[light]" in captured.out
        assert "docling" in captured.out
        assert "[heavy]" in captured.out
        assert "Pure Python PDF library" in captured.out

    def test_backends_none_installed(self, capsys):
        """backends with no backends should show installation help."""
        with patch("pdfsmith.cli.available_backends", return_value=[]):
            result = cmd_backends()

        assert result == 0
        captured = capsys.readouterr()
        assert "No backends installed" in captured.out
        assert "pip install pdfsmith[light]" in captured.out
        assert "pip install pdfsmith[recommended]" in captured.out
        assert "pip install pdfsmith[all]" in captured.out

    def test_backends_output_format(self, capsys):
        """backends output should be properly formatted."""
        from pdfsmith.backends.registry import BackendInfo

        mock_backend = BackendInfo(
            name="test_backend",
            description="Test description",
            package="test-package",
            weight="medium",
            loader=lambda: MagicMock,
        )

        with patch("pdfsmith.cli.available_backends", return_value=[mock_backend]):
            result = cmd_backends()

        assert result == 0
        captured = capsys.readouterr()
        # Check formatting: name should be padded, weight in brackets
        assert "test_backend" in captured.out
        assert "[medium]" in captured.out
        assert "Test description" in captured.out


class TestCmdParseDirect:
    """Direct tests for cmd_parse function."""

    def test_cmd_parse_returns_zero_on_success(self, sample_pdf):
        """cmd_parse should return 0 on success."""
        import argparse

        args = argparse.Namespace(
            pdf_file=sample_pdf,
            output=None,
            backend=None,
        )

        with patch("pdfsmith.cli.parse", return_value="# Test"):
            result = cmd_parse(args)

        assert result == 0

    def test_cmd_parse_returns_one_on_file_not_found(self, tmp_path):
        """cmd_parse should return 1 when file doesn't exist."""
        import argparse

        args = argparse.Namespace(
            pdf_file=tmp_path / "nonexistent.pdf",
            output=None,
            backend=None,
        )

        result = cmd_parse(args)
        assert result == 1
