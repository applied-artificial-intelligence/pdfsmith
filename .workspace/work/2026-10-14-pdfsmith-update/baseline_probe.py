"""Record installed-package behavior without contacting parsing services."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import pdfsmith
from pdfsmith import available_backends, get_backend, parse, parse_async


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks = {}

    def observe(label, operation):
        try:
            value = operation()
            if isinstance(value, str):
                (args.output / f"{label}.txt").write_text(value)
                result = {
                    "outcome": "returned_string",
                    "characters": len(value),
                    "sha256": digest(value.encode()),
                    "summary_heading": "Summary" in value,
                }
            else:
                result = {"outcome": "returned_value", "value": value}
        except Exception as exc:
            result = {
                "outcome": "exception",
                "type": type(exc).__name__,
                "message": str(exc),
            }
        checks[label] = result

    for backend in ("pypdf", "pdfplumber"):
        observe(f"public_{backend}", lambda b=backend: parse(args.document, backend=b))
        observe(
            f"async_{backend}",
            lambda b=backend: asyncio.run(parse_async(args.document, backend=b)),
        )
        for fixture in ("text.pdf", "blank.pdf", "corrupt.pdf", "missing.pdf"):
            observe(
                f"{backend}_{fixture}",
                lambda b=backend, f=fixture: parse(args.fixtures / f, backend=b),
            )
    observe("default", lambda: parse(args.document))
    observe("default_backend", lambda: get_backend().name)
    observe("discovery", lambda: [b.name for b in available_backends()])
    observe("singleton", lambda: get_backend("pypdf") is get_backend("pypdf"))
    observe(
        "keyword_compatibility", lambda: parse(pdf_path=args.document, backend="pypdf")
    )
    observe("unknown_backend", lambda: parse(args.document, backend="not-a-parser"))
    observe("missing_integration", lambda: parse(args.document, backend="docling"))
    observe(
        "layout_preset",
        lambda: parse(args.document, backend="pdfplumber", preset="best"),
    )
    observe(
        "invalid_preset", lambda: parse(args.document, backend="pypdf", preset="typo")
    )
    observe("unsupported_ocr", lambda: parse(args.document, backend="pypdf", ocr=True))
    observe(
        "invalid_option",
        lambda: parse(args.document, backend="pypdf", backend_options={"typo": True}),
    )
    observe("directory_input", lambda: parse(args.fixtures, backend="pypdf"))
    cli = {}
    for label, tail in {
        "version": ["--version"],
        "backends": ["backends"],
        "parse": ["parse", str(args.document), "--backend", "pypdf"],
        "corrupt": ["parse", str(args.fixtures / "corrupt.pdf"), "--backend", "pypdf"],
        "blank": ["parse", str(args.fixtures / "blank.pdf"), "--backend", "pypdf"],
        "unknown": ["parse", str(args.document), "--backend", "not-a-parser"],
        "missing": ["parse", str(args.fixtures / "missing.pdf"), "--backend", "pypdf"],
        "options": [
            "parse",
            str(args.document),
            "--backend",
            "pdfplumber",
            "--preset",
            "best",
        ],
    }.items():
        command = [str(Path(sys.executable).with_name("pdfsmith")), *tail]
        cli_result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        for channel in ("stdout", "stderr"):
            (args.output / f"cli_{label}_{channel}.txt").write_text(
                getattr(cli_result, channel)
            )
        cli[label] = {
            "command": command,
            "returncode": cli_result.returncode,
            "stdout_sha256": digest(cli_result.stdout.encode()),
            "stderr_sha256": digest(cli_result.stderr.encode()),
        }
    package = Path(pdfsmith.__file__).parent
    result = {
        "kind": args.kind,
        "python": platform.python_version(),
        "distribution_version": importlib.metadata.version("pdfsmith"),
        "module_version": pdfsmith.__version__,
        "package_path": str(package),
        "module_hashes": {
            str(p.relative_to(package)): digest(p.read_bytes())
            for p in sorted(package.rglob("*.py"))
        },
        "dependencies": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "input_sha256": digest(args.document.read_bytes()),
        "fixture_sha256": {
            p.name: digest(p.read_bytes()) for p in args.fixtures.glob("*.pdf")
        },
        "checks": checks,
        "cli": cli,
        "boundary": "Local capability only; no provider calls or quality comparison.",
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "kind": args.kind,
                "versions": [result["distribution_version"], result["module_version"]],
                "checks": {
                    k: {
                        a: v
                        for a, v in c.items()
                        if a in {"outcome", "type", "value", "characters"}
                    }
                    for k, c in checks.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
