"""Installed SDK/API/CLI checks on offline HTTP, never live service verification."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from llama_transport import install_transport

    events, clients = install_transport(args.document, args.output / "sdk-events.json")
    os.environ["LLAMA_CLOUD_API_KEY"] = "synthetic-offline"
    import pdfsmith
    from pdfsmith import get_backend, parse, parse_async

    options = {"tier": "agentic", "version": "2026-09-29"}
    expected = "\n\n".join(f"# Offline page {i}" for i in range(1, 9))
    direct = get_backend("llamaparse", backend_options=options)
    assert direct.parse(args.document) == expected
    assert (
        parse(
            args.document,
            backend="llamaparse",
            backend_options={**options, "disable_cache": False},
        )
        == expected
    )
    assert (
        asyncio.run(
            parse_async(args.document, backend="llamaparse", backend_options=options)
        )
        == expected
    )
    assert [
        event["json"]["disable_cache"]
        for event in events
        if event["path"] == "/api/v2/parse"
    ] == [True, False, True]
    assert all(client.is_closed for client in clients)
    shim = args.output / "shim"
    shim.mkdir(exist_ok=True)
    (shim / "sitecustomize.py").write_text(
        "import os, sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(Path(__file__).parent)!r})\n"
        "from llama_transport import install_transport\n"
        f"install_transport(Path({str(args.document)!r}), "
        "Path(os.environ['OFFLINE_EVENT_LOG']), "
        "fail_cleanup=os.environ.get('OFFLINE_FAIL_CLEANUP') == '1')\n"
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "LANG", "HOME", "LLAMA_CLOUD_API_KEY"}
    }
    env.update(
        PYTHONPATH=str(shim),
        PYTHONDONTWRITEBYTECODE="1",
        OFFLINE_EVENT_LOG=str(args.output / "cli-events.json"),
    )
    cli = [
        str(Path(sys.executable).with_name("pdfsmith")),
        "parse",
        str(args.document),
        "-b",
        "llamaparse",
        "--backend-options",
        json.dumps(options),
    ]
    output = args.output / "cli.md"
    result = subprocess.run(
        cli + ["-o", str(output)], env=env, capture_output=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == expected
    env.update(
        OFFLINE_FAIL_CLEANUP="1",
        OFFLINE_EVENT_LOG=str(args.output / "failure-events.json"),
    )
    result = subprocess.run(
        cli + ["-o", str(output)], env=env, capture_output=True, timeout=60
    )
    assert result.returncode == 1
    assert output.read_text() == expected
    recoveries = list(args.output.glob("pdfsmith-recovery-*.json"))
    assert len(recoveries) == 1
    recovery = json.loads(recoveries[0].read_text())
    assert (
        recovery["recovered_content"] == expected
        and recovery["parse_completed"] is True
    )
    failure_events = json.loads((args.output / "failure-events.json").read_text())
    assert (
        sum(
            e["method"] == "POST" and e["path"] == "/api/v2/parse"
            for e in failure_events
        )
        == 1
    )
    package = Path(pdfsmith.__file__).parent

    def sha(data):
        return hashlib.sha256(data).hexdigest()

    record = {
        "evidence": "offline-contract; no service processing or authentication",
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
        "declared_public_pdf_pages": 8,
        "controlled_response_output_sha256": sha(expected.encode()),
        "last_result_identity": direct.last_result_identity,
        "cli_command": cli,
        "cleanup_failure_exit": result.returncode,
        "recovered_content_sha256": sha(recovery["recovered_content"].encode()),
    }
    (args.output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(platform.python_version(), "offline installed SDK/API/CLI passed", flush=True)


if __name__ == "__main__":
    main()
