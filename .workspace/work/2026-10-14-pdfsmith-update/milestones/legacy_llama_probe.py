"""Reproduce the preserved legacy ERROR-to-empty defect without service calls.

Requires the legacy distributions recorded in 05-llamaparse/legacy-sdk-inspection.json.
Exit 1 with the regression assertion is the expected preserved-source outcome.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import socket
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for key in tuple(os.environ):
        if key.startswith(
            (
                "AWS_",
                "AZURE_",
                "GOOGLE_",
                "GEMINI_",
                "ANTHROPIC_",
                "OPENAI_",
                "LLAMA_",
                "DATABRICKS_",
                "PDFSMITH_",
            )
        ):
            os.environ.pop(key)
    os.environ["LLAMA_CLOUD_API_KEY"] = "synthetic-offline"

    def denied(*args, **kwargs):
        raise RuntimeError("Network outside strict legacy offline transport forbidden")

    for name in ("connect", "connect_ex"):
        setattr(socket.socket, name, denied)
    socket.create_connection = denied
    socket.getaddrinfo = denied
    import httpx
    from llama_parse import LlamaParse

    spec = importlib.util.spec_from_file_location(
        "legacy_pdfsmith_wrapper", args.wrapper
    )
    assert spec is not None and spec.loader is not None
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    events = []

    async def transport(request):
        body = await request.aread()
        route = request.method, request.url.path
        events.append(
            {
                "method": request.method,
                "path": request.url.path,
                "selected_controls_present": {
                    name: ('name="' + name + '"').encode() in body
                    for name in (
                        "parse_mode",
                        "parsing_mode",
                        "tier",
                        "version",
                        "disable_cache",
                        "do_not_cache",
                        "invalidate_cache",
                        "target_pages",
                    )
                },
            }
        )
        if route == ("POST", "/api/parsing/upload"):
            return httpx.Response(200, json={"id": "controlled-job"})
        if route == ("GET", "/api/parsing/job/controlled-job"):
            return httpx.Response(
                200,
                json={
                    "id": "controlled-job",
                    "status": "ERROR",
                    "error_code": "CONTROLLED",
                    "error_message": "controlled service failure",
                },
            )
        raise AssertionError(f"Unexpected legacy endpoint: {route}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(transport))

    def factory(**kwargs):
        return LlamaParse(
            **kwargs,
            custom_client=client,
            check_for_updates=False,
            check_interval=0,
            max_timeout=5,
        )

    wrapper.LlamaParse = factory
    backend = wrapper.LlamaParseBackend(parsing_mode="premium")
    result = backend.parse(args.document)
    assert result == ""
    assert len(events) == 2 and not events[0]["selected_controls_present"]["parse_mode"]
    args.output.write_text(
        json.dumps(
            {
                "evidence": "offline legacy SDK regression; no service requests",
                "wrapper_sha256": hashlib.sha256(args.wrapper.read_bytes()).hexdigest(),
                "requested_parsing_mode": "premium",
                "sdk_parse_mode": backend.client.parse_mode,
                "sdk_ignore_errors": backend.client.ignore_errors,
                "returned_output": result,
                "events": events,
            },
            indent=2,
        )
        + "\n"
    )
    asyncio.run(client.aclose())
    raise AssertionError(
        "REGRESSION: explicit service ERROR was reported as successful empty output"
    )


if __name__ == "__main__":
    main()
