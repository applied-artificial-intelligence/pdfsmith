"""Installed Google extra through actual SDKs and strict offline HTTP adapters."""

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


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--transport", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    from pdfsmith.backends.google_document_ai_backend import (
        GoogleDocumentAIBackend as cls,
    )

    options = {
        "project_id": "offline",
        "processor_id": "processor",
        "gcs_bucket": "offline-bucket",
        "poll_interval": 0.001,
    }
    instance = cls(**options)
    assert "google.cloud.documentai_v1" not in sys.modules
    module_spec = importlib.util.spec_from_file_location(
        "offline_google_wire", args.transport
    )
    wire_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(wire_module)

    def denied(*a, **kw):
        raise RuntimeError("No network in installed Google verification")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    current = "complete"
    wires = []

    def create(self):
        client, storage, wire = wire_module.google_clients(current)
        self._offline_storage = storage
        wires.append(wire)
        return client

    def storage(self):
        return self._offline_storage

    errors = []
    text = "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
    with (
        patch.object(cls, "_create_client", create),
        patch.object(cls, "_create_storage", storage),
    ):
        path = args.fixtures / "two-pages.pdf"
        assert pdfsmith.parse(path, backend=cls.name, backend_options=options) == text
        assert instance.parse(path) == text

        async def run():
            assert (
                await pdfsmith.parse_async(
                    path, backend=cls.name, backend_options=options
                )
                == text
            )

        asyncio.run(run())
        for name in ["two-pages.pdf", "sixteen-pages.pdf", "large-upload.pdf"]:
            assert (
                pdfsmith.parse(
                    args.fixtures / name,
                    backend=cls.name,
                    backend_options={**options, "mode": "batch"},
                )
                == text
            )
            assert not wires[-1].objects and wires[-1].closed == 3
        current = "blank"
        assert (
            pdfsmith.parse(
                args.fixtures / "blank.pdf", backend=cls.name, backend_options=options
            )
            == ""
        )
        for case in [
            "individual-error",
            "document-error",
            "wrong-destination",
            "missing-shard",
            "duplicate-shard",
            "metadata-failed",
            "missing-status",
            "wrong-source",
            "terminal-error",
            "missing-response",
            "text-gap",
            "duplicate-page",
            "timeout",
            "cancel-complete",
            "cancel-error",
            "wrong-operation",
            "ambiguous-submit",
            "submit-error",
            "close-error",
            "delete-error",
        ]:
            current = case
            settings = {
                **options,
                "mode": "batch",
                "max_wait": 0.02
                if case in {"timeout", "cancel-error", "cancel-complete"}
                else 5,
            }
            try:
                pdfsmith.parse(path, backend=cls.name, backend_options=settings)
            except Exception as exc:
                row = {
                    "case": case,
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "cause": str(exc.__cause__),
                    "parse_completed": getattr(exc, "parse_completed", False),
                    "completion_unknown": getattr(exc, "completion_unknown", False),
                    "resources": getattr(exc, "resource_ids", {}),
                    "cleanup_errors": getattr(exc, "cleanup_errors", ()),
                }
                if case in {"close-error", "delete-error"}:
                    assert row["parse_completed"] and exc.recovered_content == text
                if case in {
                    "timeout",
                    "cancel-error",
                    "wrong-operation",
                    "ambiguous-submit",
                }:
                    assert row["completion_unknown"]
                    assert not any(
                        call["method"] == "DELETE" for call in wires[-1].calls
                    )
                if case == "cancel-complete":
                    assert not row["completion_unknown"] and not wires[-1].objects
                errors.append(row)
            else:
                raise AssertionError(f"Case {case} returned false success")
            assert wires[-1].closed == 3

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
    assert not hook.exists()
    bootstrap = f"""import socket,sys,os
sys.path.insert(0,{str(args.transport.parent)!r})
from google_transport import google_clients
from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend as cls
def denied(*a,**kw):raise RuntimeError("Google console network disabled")
socket.socket.connect=denied;socket.getaddrinfo=denied
def client(self):
 c,s,w=google_clients(os.getenv("_PDFSMITH_GOOGLE_CASE","complete"))
 self._offline_storage=s
 return c
cls._create_client=client
cls._create_storage=lambda self:self._offline_storage
"""
    command = [
        str(Path(sys.executable).with_name("pdfsmith")),
        "parse",
        str(path),
        "-b",
        cls.name,
        "--backend-options",
        json.dumps(options),
    ]
    try:
        hook.write_text(bootstrap)
        console = subprocess.run(command, capture_output=True, timeout=60)
        assert console.returncode == 0, console.stderr
        assert console.stdout == text.encode()
        batch_command = [*command[:-1], json.dumps({**options, "mode": "batch"})]
        batch = subprocess.run(batch_command, capture_output=True, timeout=60)
        assert batch.returncode == 0 and batch.stdout == text.encode(), batch.stderr
        destination = args.output / "protected.txt"
        destination.write_text("previous output")
        env = {**os.environ, "_PDFSMITH_GOOGLE_CASE": "delete-error"}
        failure = subprocess.run(
            [*batch_command, "-o", str(destination)],
            env=env,
            capture_output=True,
            timeout=60,
        )
        assert failure.returncode != 0 and destination.read_text() == "previous output"
        recovery = list(args.output.glob("pdfsmith-recovery-*.json"))
        assert len(recovery) == 1, failure.stderr
        assert recovery[0].stat().st_mode & 0o777 == 0o600
        assert json.loads(recovery[0].read_text())["recovered_content"] == text
    finally:
        hook.unlink(missing_ok=True)
    (args.output / "content.txt").write_text(text)
    package = Path(pdfsmith.__file__).parent
    result = {
        "evidence": "offline real SDK contracts; no live-service proof",
        "python": platform.python_version(),
        "version": pdfsmith.__version__,
        "package_path": str(package),
        "options": instance.effective_options,
        "dependencies": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "source_hashes": {
            str(p.relative_to(package)): digest(p.read_bytes())
            for p in package.rglob("*.py")
        },
        "inputs": {p.name: digest(p.read_bytes()) for p in args.fixtures.glob("*.pdf")},
        "output_sha256": digest(text.encode()),
        "errors": errors,
        "console_returncode": console.returncode,
        "batch_console_returncode": batch.returncode,
        "recovery_returncode": failure.returncode,
        "wire_calls": [wire.calls for wire in wires],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"python": result["python"], "sdk_contracts": "passed"}))


if __name__ == "__main__":
    main()
