"""Installed extra-only SDK/API/async/console OCR checks, all transport-offline."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pdfsmith


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--transport", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from pdfsmith.backends.registry import BACKEND_REGISTRY

    cls = BACKEND_REGISTRY[args.backend].loader()
    options = (
        {
            "endpoint": "https://offline.azure.invalid",
            "poll_interval": 0.001,
            "max_wait": 5,
        }
        if args.backend.startswith("azure")
        else {}
    )
    instance = cls(**options)
    assert not any(
        name in sys.modules
        for name in ("boto3", "azure.ai.documentintelligence", "pymupdf")
    )
    spec = importlib.util.spec_from_file_location("offline_ocr_wire", args.transport)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = (
        module.aws_client if args.backend == "aws_textract" else module.azure_client
    )

    def denied(*a, **kw):
        raise RuntimeError("No network in installed OCR verification")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    records = []
    current = "complete"
    transports = []

    def client(self):
        sdk, transport = factory(current)
        transports.append(transport)
        return sdk

    with patch.object(cls, "_create_client", client):
        path = args.fixtures / "two-pages.pdf"
        text = pdfsmith.parse(path, backend=args.backend, backend_options=options)
        assert "FIRST PAGE SENTINEL" in text and "FINAL PAGE SENTINEL" in text
        assert instance.parse(path) == text

        async def run():
            assert (
                await pdfsmith.parse_async(
                    path, backend=args.backend, backend_options=options
                )
                == text
            )

        asyncio.run(run())
        cases = (
            [
                "missing-pages",
                "missing-text",
                "late-error",
                "close-error",
                "late-and-close-error",
            ]
            if args.backend == "aws_textract"
            else [
                "running",
                "missing-pages",
                "missing-text",
                "timeout",
                "failed",
                "delete-error",
                "close-error",
                "wrong-location",
                "failed-and-delete-error",
                "timeout-and-close-error",
            ]
        )
        for case in cases:
            current = case
            configured = dict(options)
            if case.startswith("timeout"):
                configured["max_wait"] = 0.02
            try:
                result = pdfsmith.parse(
                    path, backend=args.backend, backend_options=configured
                )
            except Exception as exc:
                assert case != "running"
                entry = dict(
                    case=case,
                    type=type(exc).__name__,
                    message=str(exc),
                    parse_completed=getattr(exc, "parse_completed", False),
                    completion_unknown=getattr(exc, "completion_unknown", False),
                    recovered_content=getattr(exc, "recovered_content", None),
                    resource_ids=getattr(exc, "resource_ids", {}),
                )
                if case in {"close-error", "delete-error"}:
                    assert (
                        entry["parse_completed"]
                        and "FINAL PAGE SENTINEL" in entry["recovered_content"]
                    )
                if case.startswith("timeout") or case == "wrong-location":
                    assert entry["completion_unknown"]
                    assert not any(
                        call.get("method") == "DELETE" for call in transports[-1].calls
                    )
                records.append(entry)
            else:
                assert case == "running" and result == text
            assert transports[-1].closed
        current = "blank"
        assert (
            pdfsmith.parse(
                args.fixtures / "blank.pdf",
                backend=args.backend,
                backend_options=options,
            )
            == ""
        )
        if args.backend.startswith("azure"):
            current = "complete"
            markdown = {
                **options,
                "model_id": "prebuilt-layout",
                "output_format": "markdown",
            }
            assert pdfsmith.parse(
                path, backend=args.backend, backend_options=markdown
            ).startswith("# FIRST PAGE SENTINEL")
    assert all(transport.closed for transport in transports)

    site = Path(
        subprocess.check_output(
            [
                sys.executable,
                "-I",
                "-c",
                "import sysconfig;print(sysconfig.get_paths()['purelib'])",
            ],
            text=True,
        ).strip()
    )
    hook = site / "sitecustomize.py"
    assert not hook.exists(), "Do not overwrite an existing bootstrap file"
    factory_name = "aws_client" if args.backend == "aws_textract" else "azure_client"
    source = f"""import sys,os,socket
sys.path.insert(0,{str(args.transport.parent)!r})
from ocr_transport import {factory_name}
from pdfsmith.backends.registry import BACKEND_REGISTRY
def denied(*a,**kw):raise RuntimeError("Network disabled in OCR console verification")
socket.socket.connect=denied;socket.getaddrinfo=denied
cls=BACKEND_REGISTRY[{args.backend!r}].loader()
def client(self):return {factory_name}(os.getenv("_PDFSMITH_OCR_CASE","complete"))[0]
cls._create_client=client
"""
    command = [
        str(Path(sys.executable).with_name("pdfsmith")),
        "parse",
        str(path),
        "-b",
        args.backend,
        "--backend-options",
        json.dumps(options),
    ]
    try:
        hook.write_text(source)
        console = subprocess.run(command, capture_output=True, timeout=60)
        assert console.returncode == 0, console.stderr
        assert console.stdout == text.encode()
        destination = args.output / "protected.txt"
        destination.write_text("previous output")
        environment = os.environ.copy()
        environment["_PDFSMITH_OCR_CASE"] = "close-error"
        failed = subprocess.run(
            [*command, "-o", str(destination)],
            env=environment,
            capture_output=True,
            timeout=60,
        )
        assert failed.returncode != 0
        assert destination.read_text() == "previous output"
        recovery = list(args.output.glob("pdfsmith-recovery-*.json"))
        assert len(recovery) == 1, failed.stderr
        assert recovery[0].stat().st_mode & 0o777 == 0o600
        saved = json.loads(recovery[0].read_text())
        assert "FINAL PAGE SENTINEL" in saved["recovered_content"]
    finally:
        hook.unlink(missing_ok=True)
    (args.output / "content.txt").write_text(text)
    package = Path(pdfsmith.__file__).parent
    result = dict(
        evidence="offline installed SDK contracts; no live service proof",
        backend=args.backend,
        python=platform.python_version(),
        version=pdfsmith.__version__,
        package_path=str(package),
        options=instance.effective_options,
        dependencies={
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        source_hashes={
            str(p.relative_to(package)): sha(p.read_bytes())
            for p in package.rglob("*.py")
        },
        inputs={str(path): sha(path.read_bytes())},
        output_sha256=sha(text.encode()),
        error_cases=records,
        console_returncode=console.returncode,
        recovery_returncode=failed.returncode,
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        args.backend,
        platform.python_version(),
        "offline SDK/API/async/CLI checks passed",
    )


if __name__ == "__main__":
    main()
