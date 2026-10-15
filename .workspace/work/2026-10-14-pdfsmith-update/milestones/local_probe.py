"""Exercise an installed local integration without test-runner dependencies."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pdfsmith


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("pypdf", "pdfplumber"), required=True)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert len(pdfsmith.registered_backends()) == 19
    assert not any(
        name.startswith("pdfsmith.backends.") and name != "pdfsmith.backends.registry"
        for name in sys.modules
    )
    assert pdfsmith.__version__ == importlib.metadata.version("pdfsmith")
    public = pdfsmith.parse(args.document, backend=args.backend)
    assert "Summary" in public
    assert (
        asyncio.run(pdfsmith.parse_async(args.document, backend=args.backend)) == public
    )
    assert pdfsmith.parse(pdf_path=args.document, backend=args.backend) == public
    assert pdfsmith.parse(args.fixtures / "blank.pdf", backend=args.backend) == ""
    failures = {}
    for label, path, backend, invalid_options in (
        ("missing", args.fixtures / "missing.pdf", args.backend, None),
        ("corrupt", args.fixtures / "corrupt.pdf", args.backend, None),
        ("unknown", args.document, "not-a-parser", None),
        ("invalid_option", args.document, args.backend, {"not_an_option": True}),
        ("unavailable", args.document, "aws_textract", None),
    ):
        try:
            pdfsmith.parse(path, backend=backend, backend_options=invalid_options)
        except Exception as exc:
            failures[label] = {"type": type(exc).__name__, "message": str(exc)}
        else:
            raise AssertionError(f"{label} unexpectedly succeeded")
    assert failures["missing"]["type"] == "FileNotFoundError"
    assert failures["unknown"]["type"] == "ValueError"
    assert "pdfsmith[aws]" in failures["unavailable"]["message"]
    instance = pdfsmith.get_backend(args.backend)
    assert pdfsmith.get_backend(args.backend) is instance
    options: dict[str, Any] = (
        {"layout": True}
        if args.backend == "pdfplumber"
        else {"extraction_mode": "layout"}
    )
    direct = pdfsmith.get_backend(args.backend, backend_options=options)
    plain = instance.parse(args.fixtures / "columns.pdf")
    configured = direct.parse(args.fixtures / "columns.pdf")
    assert "LEFT COLUMN" in configured and "RIGHT COLUMN" in configured
    assert plain != configured
    assert (
        pdfsmith.parse(
            args.fixtures / "columns.pdf", backend=args.backend, backend_options=options
        )
        == configured
    )
    cli_path = args.output / "cli-output.txt"
    cli = subprocess.run(
        [
            str(Path(sys.executable).with_name("pdfsmith")),
            "parse",
            str(args.document),
            "--backend",
            args.backend,
            "--output",
            str(cli_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert cli_path.read_text() == public
    (args.output / "public.txt").write_text(public)
    (args.output / "configured.txt").write_text(configured)
    result = {
        "evidence": "local-e2e",
        "backend": args.backend,
        "python": platform.python_version(),
        "module_version": pdfsmith.__version__,
        "package_path": pdfsmith.__file__,
        "installed_distributions": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
        },
        "input_sha256": sha(args.document.read_bytes()),
        "fixtures": {p.name: sha(p.read_bytes()) for p in args.fixtures.glob("*.pdf")},
        "output_sha256": sha(public.encode()),
        "characters": len(public),
        "configured_options": options,
        "configured_output_sha256": sha(configured.encode()),
        "errors": failures,
        "cli_returncode": cli.returncode,
        "scope": "Local capability only; no quality comparison or provider call",
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "backend": args.backend,
                "python": result["python"],
                "characters": len(public),
                "result": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
