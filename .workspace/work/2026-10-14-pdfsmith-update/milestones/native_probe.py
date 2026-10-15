"""Installed-wheel native integration evidence using public and controlled PDFs."""

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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from pdfsmith.backends.registry import BACKEND_REGISTRY

    cls = BACKEND_REGISTRY[args.backend].loader()
    instance = cls()
    assert not any(
        module in sys.modules
        for module in (
            "fitz",
            "pymupdf",
            "pymupdf4llm",
            "pdfminer.high_level",
            "pypdfium2",
            "kreuzberg",
            "extractous",
            "unstructured.partition.pdf",
        )
    )
    public = pdfsmith.parse(args.document, backend=args.backend)
    assert "Summary" in public
    assert instance.parse(args.document) == public

    async def concurrent():
        results = await asyncio.gather(
            *(
                pdfsmith.parse_async(args.document, backend=args.backend)
                for _ in range(3)
            )
        )
        assert results == [public] * 3
        assert instance.parse(args.document) == public

    asyncio.run(concurrent())
    assert instance.parse(args.fixtures / "blank.pdf") == ""
    errors = {}
    for label, path in [
        ("missing", args.fixtures / "missing.pdf"),
        ("corrupt", args.fixtures / "corrupt.pdf"),
    ]:
        try:
            instance.parse(path)
        except Exception as exc:
            errors[label] = dict(type=type(exc).__name__, message=str(exc))
        else:
            raise AssertionError(f"{label} succeeded")
    options = {
        "pymupdf": {"sort": True},
        "pymupdf4llm": {"use_layout": True},
        "pdfminer": {"char_margin": 100.0},
        "pypdfium2": {},
        "kreuzberg": {"output_format": "markdown"},
        "extractous": {},
        "unstructured": {"include_page_breaks": True},
    }[args.backend]
    configured = cls(**options).parse(args.document)
    assert configured == pdfsmith.parse(
        args.document, backend=args.backend, backend_options=options
    )
    if options:
        assert public != configured, "configured extraction did not change output"
    output = args.output / "cli.md"
    command = [
        str(Path(sys.executable).with_name("pdfsmith")),
        "parse",
        str(args.document),
        "-b",
        args.backend,
        "--backend-options",
        json.dumps(options),
        "-o",
        str(output),
    ]
    cli = subprocess.run(command, capture_output=True, timeout=90)
    assert cli.returncode == 0, cli.stderr
    assert output.read_bytes() == configured.encode()
    (args.output / "public.txt").write_text(public)
    (args.output / "configured.txt").write_text(configured)
    package = Path(pdfsmith.__file__).parent
    result = {
        "evidence": "local-e2e",
        "backend": args.backend,
        "python": platform.python_version(),
        "package_path": pdfsmith.__file__,
        "module_version": pdfsmith.__version__,
        "installed_distributions": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "module_hashes": {
            str(p.relative_to(package)): sha(p.read_bytes())
            for p in package.rglob("*.py")
        },
        "input_sha256": sha(args.document.read_bytes()),
        "fixtures": {p.name: sha(p.read_bytes()) for p in args.fixtures.glob("*.pdf")},
        "output_sha256": sha(public.encode()),
        "output_bytes": len(public.encode()),
        "configured_options": options,
        "configured_sha256": sha(configured.encode()),
        "effective_defaults": instance.effective_options,
        "errors": errors,
        "cli_command": command,
        "scope": "Actual local parsing; no quality comparison or live provider calls",
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(args.backend, platform.python_version(), "passed", flush=True)


if __name__ == "__main__":
    main()
