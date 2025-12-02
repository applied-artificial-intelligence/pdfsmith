"""Command-line interface for pdfsmith."""

import argparse
import sys
from pathlib import Path

from pdfsmith import __version__, available_backends, parse


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pdfsmith",
        description="Convert PDF files to Markdown",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pdfsmith {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a PDF file to Markdown")
    parse_parser.add_argument("pdf_file", type=Path, help="Path to PDF file")
    parse_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    parse_parser.add_argument(
        "-b",
        "--backend",
        help="Backend to use (default: auto-select)",
    )

    # Backends command
    subparsers.add_parser("backends", help="List available backends")

    args = parser.parse_args()

    if args.command == "parse":
        return cmd_parse(args)
    elif args.command == "backends":
        return cmd_backends()
    else:
        parser.print_help()
        return 0


def cmd_parse(args: argparse.Namespace) -> int:
    """Handle parse command."""
    if not args.pdf_file.exists():
        print(f"Error: File not found: {args.pdf_file}", file=sys.stderr)
        return 1

    try:
        markdown = parse(args.pdf_file, backend=args.backend)

        if args.output:
            args.output.write_text(markdown, encoding="utf-8")
            print(f"Written to {args.output}")
        else:
            print(markdown)

        return 0

    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error parsing PDF: {e}", file=sys.stderr)
        return 1


def cmd_backends() -> int:
    """Handle backends command."""
    backends = available_backends()

    if not backends:
        print("No backends installed.")
        print("\nInstall backends with:")
        print("  pip install pdfsmith[light]       # Lightweight backends")
        print("  pip install pdfsmith[recommended] # Recommended set")
        print("  pip install pdfsmith[all]         # All backends")
        return 0

    print("Available backends:\n")
    for info in backends:
        print(f"  {info.name:<15} [{info.weight}]")
        print(f"    {info.description}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
