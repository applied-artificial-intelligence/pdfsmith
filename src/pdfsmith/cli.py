"""Command-line interface for pdfsmith."""

import argparse
import contextlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from pdfsmith import (
    BackendOperationError,
    __version__,
    available_backends,
    parse,
    registered_backends,
)


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

    parse_parser.add_argument(
        "--backend-options",
        type=_json_options,
        help="JSON object of validated backend constructor options",
    )

    inventory = subparsers.add_parser(
        "backends", help="Inspect backend dependency metadata"
    )
    inventory.add_argument(
        "--all", action="store_true", help="Include every registered integration"
    )

    args = parser.parse_args()

    if args.command == "parse":
        return cmd_parse(args)
    elif args.command == "backends":
        return cmd_backends(all_registered=True) if args.all else cmd_backends()
    else:
        parser.print_help()
        return 0


def _json_options(value: str) -> dict[str, Any]:
    try:
        options = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid backend-options JSON: {exc}"
        ) from exc
    if not isinstance(options, dict):
        raise argparse.ArgumentTypeError("backend-options must be a JSON object")
    return options


def _diagnostic(message: str) -> None:
    with contextlib.suppress(OSError, ValueError):
        print(message, file=sys.stderr)


def _recover_completed(error: BackendOperationError, directory: Path | None) -> None:
    record = {
        "parse_completed": error.parse_completed,
        "recovered_content": error.recovered_content,
        "resource_ids": error.resource_ids,
        "completion_unknown": error.completion_unknown,
        "cleanup_errors": error.cleanup_errors,
    }
    recovery = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix="pdfsmith-recovery-",
            suffix=".json",
            delete=False,
        ) as stream:
            recovery = Path(stream.name)
            json.dump(record, stream, ensure_ascii=True)
        _diagnostic(f"Completed content and cleanup details saved to {recovery}")
    except (OSError, ValueError) as exc:
        _diagnostic(f"Could not save completed content at {recovery}: {exc}")


def cmd_parse(args: argparse.Namespace) -> int:
    """Commit complete file output only after successful parsing and encoding."""
    if not args.pdf_file.exists():
        _diagnostic(f"Error: File not found: {args.pdf_file}")
        return 1
    staged: Path | None = None

    def content() -> str:
        options = getattr(args, "backend_options", None)
        if options is None:
            return parse(args.pdf_file, backend=args.backend)
        return parse(args.pdf_file, backend=args.backend, backend_options=options)

    try:
        if args.output:
            output = Path(args.output)
            if output.resolve() == args.pdf_file.resolve() or (
                output.exists() and output.samefile(args.pdf_file)
            ):
                raise ValueError("Output must not overwrite the input file or an alias")
            if output.exists() and not output.is_file():
                raise ValueError("Output must be a regular file")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=output.parent, prefix=f".{output.name}.", delete=False
            ) as stream:
                staged = Path(stream.name)
                data = content().encode("utf-8")
                stream.write(data)
            if output.exists():
                staged.chmod(stat.S_IMODE(output.stat().st_mode))
            os.replace(staged, output)
            staged = None
            _diagnostic(f"Written to {output}")
        else:
            text = content()
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(text.encode("utf-8"))
            else:
                sys.stdout.write(text)
        return 0
    except BackendOperationError as exc:
        _diagnostic(f"Error parsing PDF: {exc}")
        if exc.resource_ids:
            _diagnostic(
                "Operation resource identifiers: " + json.dumps(exc.resource_ids)
            )
        if exc.completion_unknown:
            _diagnostic("Remote completion is unknown; active resources were retained")
        if exc.parse_completed and exc.recovered_content is not None:
            _recover_completed(exc, Path(args.output).parent if args.output else None)
        return 1
    except ImportError as exc:
        _diagnostic(f"Error: {exc}")
        return 1
    except Exception as exc:
        _diagnostic(f"Error parsing PDF: {exc}")
        return 1
    finally:
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError as exc:
                _diagnostic(f"Temporary output remains at {staged}: {exc}")


def cmd_backends(*, all_registered: bool = False) -> int:
    """Handle backends command."""
    if all_registered:
        for info in registered_backends():
            state = "present" if info.is_available() else "missing"
            print(
                f"{info.name}: registered; dependencies {state}; "
                "configuration not checked"
            )
            if info.required_env:
                print("  Required environment names: " + ", ".join(info.required_env))
        return 0
    backends = available_backends()

    if not backends:
        print("No backends installed in the default local set.")
        print("\nInstall backends with:")
        print("  pip install pdfsmith[light]       # Lightweight backends")
        print("  pip install pdfsmith[recommended] # Recommended set")
        print("  pip install pdfsmith[all]         # Local optional bundle")
        return 0

    print("Available backends (dependency presence only):\n")
    for info in backends:
        print(f"  {info.name:<15} [{info.weight}]")
        print(f"    {info.description}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
