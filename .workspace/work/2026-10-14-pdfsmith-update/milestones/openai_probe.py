"""Installed OpenAI extra with real SDK serialization and offline HTTP transport."""

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
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--transport", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    from pdfsmith.backends.openai_backend import OpenAIBackend as cls

    options = {"model": "future-pdf-model", "max_completion_tokens": 1234}
    instance = cls(**options)
    assert "openai" not in sys.modules
    spec = importlib.util.spec_from_file_location("offline_openai_wire", args.transport)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def denied(*a, **kw):
        raise RuntimeError("No network in installed OpenAI verification")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    current = "complete"
    wires = []

    def create(self):
        client, wire = module.openai_client(current)
        wires.append(wire)
        return client

    path = args.fixtures / "two-pages.pdf"
    text = "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
    errors = []
    with patch.object(cls, "_create_client", create):
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
        for case in [
            "blank",
            "missing-usage",
            "length",
            "content_filter",
            "tool_calls",
            "refusal",
            "missing-content",
            "missing-choices",
            "extra-choice",
            "generation-error",
            "ambiguous-generation",
            "upload-error",
            "delete-error",
            "delete-unconfirmed",
            "close-error",
            "generation-and-delete-error",
        ]:
            current = case
            try:
                result = pdfsmith.parse(path, backend=cls.name, backend_options=options)
            except Exception as exc:
                assert case not in {"blank", "missing-usage"}
                row = {
                    "case": case,
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "cause": str(exc.__cause__),
                    "parse_completed": getattr(exc, "parse_completed", False),
                    "completion_unknown": getattr(exc, "completion_unknown", False),
                    "resources": getattr(exc, "resource_ids", {}),
                }
                if case in {"close-error", "delete-error", "delete-unconfirmed"}:
                    assert row["parse_completed"] and exc.recovered_content == text
                if case in {"upload-error", "ambiguous-generation"}:
                    assert row["completion_unknown"]
                errors.append(row)
            else:
                assert case in {"blank", "missing-usage"}
                assert result == ("" if case == "blank" else text)
            assert wires[-1].closed
    os.environ["OPENAI_API_KEY"] = "offline-key"
    configured = cls(**options)
    client, wire = module.openai_client(
        "upload-error", create=configured._create_client
    )
    with patch.object(configured, "_create_client", return_value=client):
        try:
            configured.parse(path)
        except pdfsmith.BackendOperationError as exc:
            assert exc.completion_unknown
        else:
            raise AssertionError("Ambiguous request returned success")
    assert wire.closed and len(wire.calls) == 1
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
from openai_transport import openai_client
from pdfsmith.backends.openai_backend import OpenAIBackend as cls
def denied(*a,**kw):raise RuntimeError("OpenAI console network disabled")
socket.socket.connect=denied;socket.getaddrinfo=denied
def client(self):
 return openai_client(os.getenv("_PDFSMITH_OPENAI_CASE","complete"))[0]
cls._create_client=client
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
        assert (
            console.returncode == 0 and console.stdout == text.encode()
        ), console.stderr
        destination = args.output / "protected.txt"
        destination.write_text("previous output")
        failed = subprocess.run(
            [*command, "-o", str(destination)],
            env={**os.environ, "_PDFSMITH_OPENAI_CASE": "close-error"},
            capture_output=True,
            timeout=60,
        )
        assert failed.returncode != 0 and destination.read_text() == "previous output"
        recovery = list(args.output.glob("pdfsmith-recovery-*.json"))
        assert len(recovery) == 1, failed.stderr
        assert recovery[0].stat().st_mode & 0o777 == 0o600
        assert json.loads(recovery[0].read_text())["recovered_content"] == text
    finally:
        hook.unlink(missing_ok=True)
    (args.output / "content.txt").write_text(text)
    package = Path(pdfsmith.__file__).parent
    result = {
        "evidence": "offline actual SDK contracts; no live model or service proof",
        "python": platform.python_version(),
        "version": pdfsmith.__version__,
        "options": instance.effective_options,
        "package_path": str(package),
        "dependencies": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "source_hashes": {
            str(p.relative_to(package)): sha(p.read_bytes())
            for p in package.rglob("*.py")
        },
        "inputs": {path.name: sha(path.read_bytes())},
        "output_sha256": sha(text.encode()),
        "errors": errors,
        "console_returncode": console.returncode,
        "recovery_returncode": failed.returncode,
        "wire_calls": [wire.calls for wire in wires],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"python": result["python"], "sdk_contracts": "passed"}))


if __name__ == "__main__":
    main()
