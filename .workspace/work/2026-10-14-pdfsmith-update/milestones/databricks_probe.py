"""Installed Databricks extra with the actual SDK and offline HTTP transport."""

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
    from pdfsmith.backends.databricks_backend import DatabricksBackend as cls

    options = {
        "host": "https://offline.databricks.invalid",
        "warehouse_id": "warehouse",
        "poll_interval": 0.001,
    }
    instance = cls(**options)
    assert "databricks.sdk" not in sys.modules
    spec = importlib.util.spec_from_file_location(
        "offline_databricks_wire", args.transport
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def denied(*a, **kw):
        raise RuntimeError("No network in installed Databricks verification")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    current = "complete"
    wires = []

    def create(self):
        client, wire = module.databricks_client(current)
        wires.append(wire)
        return client

    path = args.fixtures / "two-pages.pdf"
    text = "FIRST PAGE SENTINEL\n\nFINAL PAGE SENTINEL"
    records = []
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
            "pending",
            "blank",
            "page-error",
            "missing-pages",
            "missing-text",
            "wrong-version",
            "wrong-order",
            "failed",
            "truncated",
            "missing-result",
            "empty-result",
            "extra-result",
            "malformed-json",
            "timeout",
            "cancel-complete",
            "cancel-error",
            "close-error",
            "ambiguous-submit",
            "missing-identity",
        ]:
            current = case
            settings = {
                **options,
                "max_wait": 0.02
                if case in {"timeout", "cancel-complete", "cancel-error"}
                else 5,
            }
            try:
                result = pdfsmith.parse(
                    path, backend=cls.name, backend_options=settings
                )
            except Exception as exc:
                assert case not in {"pending", "blank", "missing-result"}
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
                if case == "close-error":
                    assert row["parse_completed"] and exc.recovered_content == text
                if case in {
                    "timeout",
                    "cancel-error",
                    "ambiguous-submit",
                    "missing-identity",
                }:
                    assert row["completion_unknown"]
                if case == "cancel-complete":
                    assert not row["completion_unknown"]
                records.append(row)
            else:
                assert case in {"pending", "blank", "missing-result"}
                assert result == ("" if case == "blank" else text)
            assert wires[-1].closed
            posts = [
                call
                for call in wires[-1].calls
                if call["path"] == "/api/2.0/sql/statements"
            ]
            assert len(posts) == 1 and not posts[0].get("legacy_sql")
    os.environ["DATABRICKS_TOKEN"] = "offline-token"
    configured = cls(**options)
    client, wire = module.databricks_client(create=configured._create_client)
    with patch.object(configured, "_create_client", return_value=client):
        assert configured.parse(path) == text
    assert wire.closed
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
from databricks_transport import databricks_client
from pdfsmith.backends.databricks_backend import DatabricksBackend as cls
def denied(*a,**kw):raise RuntimeError("Databricks console network disabled")
socket.socket.connect=denied;socket.getaddrinfo=denied
def client(self):
 return databricks_client(os.getenv("_PDFSMITH_DATABRICKS_CASE","complete"))[0]
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
        env = {**os.environ, "_PDFSMITH_DATABRICKS_CASE": "close-error"}
        failure = subprocess.run(
            [*command, "-o", str(destination)], env=env, capture_output=True, timeout=60
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
        "evidence": (
            "offline real SDK contracts; "
            "SQL engine acceptance and live service unverified"
        ),
        "python": platform.python_version(),
        "version": pdfsmith.__version__,
        "options": instance.effective_options,
        "package_path": str(package),
        "dependencies": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "source_hashes": {
            str(p.relative_to(package)): digest(p.read_bytes())
            for p in package.rglob("*.py")
        },
        "inputs": {path.name: digest(path.read_bytes())},
        "output_sha256": digest(text.encode()),
        "errors": records,
        "console_returncode": console.returncode,
        "recovery_returncode": failure.returncode,
        "wire_calls": [wire.calls for wire in wires],
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"python": result["python"], "sdk_contracts": "passed"}))


if __name__ == "__main__":
    main()
