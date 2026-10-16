"""Actual Anthropic SDK serialization with a network-free HTTPX transport."""

import base64
import hashlib
import json
from unittest.mock import patch


def anthropic_client(case="complete", create=None):
    import anthropic
    import httpx2 as httpx

    class Wire(httpx.MockTransport):
        def __init__(self):
            self.calls = []
            self.closed = False
            super().__init__(self.respond)

        def close(self):
            self.closed = True
            if case == "close-error":
                raise RuntimeError("Controlled Anthropic transport close error")
            super().close()

        def respond(self, request):
            assert request.method == "POST" and request.url.path == "/v1/messages"
            body = json.loads(request.content)
            document = body["messages"][0]["content"][0]
            assert document["type"] == "document"
            assert document["source"]["media_type"] == "application/pdf"
            raw = base64.b64decode(document["source"]["data"], validate=True)
            assert raw.startswith(b"%PDF-")
            self.calls.append(
                {
                    "model": body["model"],
                    "max_tokens": body["max_tokens"],
                    "input_sha256": hashlib.sha256(raw).hexdigest(),
                    "request_bytes": len(request.content),
                }
            )
            if case == "server-error":
                return httpx.Response(
                    500,
                    json={
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": "Controlled server failure",
                        },
                    },
                )
            result = {
                "id": "msg-owned",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "content": [
                    {"type": "text", "text": "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"}
                ],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 13, "output_tokens": 7},
            }
            if case in {"max_tokens", "refusal", "tool_use", "pause_turn"}:
                result["stop_reason"] = case
            if case == "missing-stop":
                result["stop_reason"] = None
            if case == "missing-content":
                result["content"] = []
            if case == "blank":
                result["content"][0]["text"] = ""
            if case == "wrong-role":
                result["role"] = "user"
            if case == "missing-usage":
                result["usage"] = None
            return httpx.Response(
                200, json=result, headers={"request-id": "offline-request"}
            )

    wire = Wire()
    if create is None:
        client = anthropic.Anthropic(
            api_key="offline-key",
            max_retries=0,
            http_client=httpx.Client(transport=wire),
        )
    else:
        original = anthropic.Anthropic.__init__

        def initialize(self, *args, **kwargs):
            kwargs["http_client"] = httpx.Client(transport=wire)
            original(self, *args, **kwargs)

        with patch.object(anthropic.Anthropic, "__init__", initialize):
            client = create()
    return client, wire
