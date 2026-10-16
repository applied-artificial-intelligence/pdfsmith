"""Controlled LlamaCloud HTTP transport. This never contacts the service."""

import hashlib
import json
import socket
from email import policy
from email.parser import BytesParser
from pathlib import Path


def install_transport(document: Path, log: Path, *, fail_cleanup=False):
    import httpx
    import llama_cloud

    def denied(*args, **kwargs):
        raise RuntimeError(
            "Networking outside the strict offline transport is forbidden"
        )

    for name in ("connect", "connect_ex"):
        setattr(socket.socket, name, denied)
    socket.create_connection = denied
    socket.getaddrinfo = denied
    real_client = llama_cloud.LlamaCloud
    events = []
    clients = []
    expected = document.read_bytes()
    pages = [
        {"page_number": i, "success": True, "markdown": f"# Offline page {i}"}
        for i in range(1, 9)
    ]

    def transport(request):
        route = (request.method, request.url.path)
        event = {"method": request.method, "path": request.url.path}
        events.append(event)
        if route == ("POST", "/api/v1/beta/files"):
            mime = BytesParser(policy=policy.default).parsebytes(
                (
                    "Content-Type: " + request.headers["content-type"] + "\r\n\r\n"
                ).encode()
                + request.read()
            )
            payload = next(
                part.get_payload(decode=True)
                for part in mime.iter_parts()
                if part.get_param("name", header="content-disposition") == "file"
            )
            assert payload == expected
            event["uploaded_sha256"] = hashlib.sha256(payload).hexdigest()
            response = httpx.Response(
                200,
                json={
                    "id": "file-controlled",
                    "name": document.name,
                    "project_id": "project-controlled",
                },
            )
        elif route == ("POST", "/api/v2/parse"):
            event["json"] = json.loads(request.read())
            assert event["json"]["tier"] == "agentic"
            assert event["json"]["version"] == "2026-09-29"
            response = httpx.Response(
                200,
                json={
                    "id": "job-controlled",
                    "status": "PENDING",
                    "project_id": "project-controlled",
                },
            )
        elif route == ("GET", "/api/v2/parse/job-controlled"):
            assert request.url.params.get_list("expand") == ["markdown"]
            response = httpx.Response(
                200,
                json={
                    "job": {
                        "id": "job-controlled",
                        "status": "COMPLETED",
                        "tier": "agentic",
                        "project_id": "project-controlled",
                    },
                    "markdown": {"pages": pages},
                },
            )
        elif route == ("DELETE", "/api/v2/parse/job-controlled"):
            response = httpx.Response(
                200, json={"id": "job-controlled", "project_id": "project-controlled"}
            )
        elif route == ("DELETE", "/api/v1/beta/files/file-controlled"):
            response = (
                httpx.Response(503, json={"detail": "controlled cleanup failure"})
                if fail_cleanup
                else httpx.Response(204)
            )
        else:
            raise AssertionError(f"Unexpected SDK endpoint {route}")
        log.write_text(json.dumps(events, indent=2) + "\n")
        return response

    def factory(**kwargs):
        assert kwargs["api_key"] == "synthetic-offline"
        assert kwargs["max_retries"] == 0
        assert kwargs["_strict_response_validation"] is True
        http = httpx.Client(transport=httpx.MockTransport(transport))
        clients.append(http)
        return real_client(**kwargs, http_client=http)

    llama_cloud.LlamaCloud = factory
    return events, clients
