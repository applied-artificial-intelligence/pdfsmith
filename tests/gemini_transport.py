"""Actual Google GenAI SDK requests and typed responses with offline HTTPX."""

import base64
import hashlib
import json
from unittest.mock import patch


def gemini_client(case="complete", create=None):
    import httpx
    from google import genai
    from google.genai import types

    class Wire(httpx.MockTransport):
        def __init__(self):
            self.calls = []
            self.closed = False
            self.async_closed = False
            super().__init__(self.respond)

        def close(self):
            self.closed = True
            if case == "close-error":
                raise RuntimeError("Controlled Gemini sync close failure")
            super().close()

        async def aclose(self):
            self.async_closed = True
            if case == "async-close-error":
                raise RuntimeError("Controlled Gemini async close failure")
            await super().aclose()

        def respond(self, request):
            assert request.method == "POST" and request.url.path.endswith(
                ":generateContent"
            )
            body = json.loads(request.content)
            parts = body["contents"][0]["parts"]
            document = parts[0]["inlineData"]
            assert (
                document.get("mimeType", document.get("mime_type")) == "application/pdf"
            )
            raw = base64.b64decode(document["data"], altchars=b"-_", validate=True)
            assert raw.startswith(b"%PDF-")
            self.calls.append(
                {
                    "path": request.url.path,
                    "input_sha256": hashlib.sha256(raw).hexdigest(),
                    "generation_config": body.get("generationConfig"),
                }
            )
            if case == "server-error":
                return httpx.Response(
                    500,
                    json={
                        "error": {
                            "code": 500,
                            "status": "INTERNAL",
                            "message": "Controlled generation failure",
                        }
                    },
                )
            result = {
                "candidates": [
                    {
                        "index": 0,
                        "finishReason": "STOP",
                        "content": {
                            "role": "model",
                            "parts": [
                                {"text": "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"}
                            ],
                        },
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 13,
                    "candidatesTokenCount": 7,
                    "totalTokenCount": 20,
                },
                "modelVersion": "reported-model-version",
                "responseId": "owned-response",
            }
            if case in {"MAX_TOKENS", "SAFETY", "RECITATION"}:
                result["candidates"][0]["finishReason"] = case
            if case == "blocked":
                result["promptFeedback"] = {"blockReason": "SAFETY"}
                result["candidates"] = []
            if case == "missing-candidates":
                result["candidates"] = []
            if case == "missing-content":
                result["candidates"][0].pop("content")
            if case == "missing-finish":
                result["candidates"][0].pop("finishReason")
            if case == "blank":
                result["candidates"][0]["content"]["parts"][0]["text"] = ""
            if case == "non-text":
                result["candidates"][0]["content"]["parts"] = [
                    {"functionCall": {"name": "unrequested_tool", "args": {}}}
                ]
            if case == "thoughts-only":
                result["candidates"][0]["content"]["parts"] = [
                    {"thought": True, "text": "reasoning is not extracted text"}
                ]
            if case == "thoughts":
                result["candidates"][0]["content"]["parts"].insert(
                    0, {"thought": True, "text": "reasoning is not extracted text"}
                )
            if case == "missing-usage":
                result.pop("usageMetadata")
            if case == "zero-usage":
                result["usageMetadata"] = {
                    "promptTokenCount": 0,
                    "candidatesTokenCount": 0,
                    "totalTokenCount": 0,
                }
            return httpx.Response(200, json=result)

    wire = Wire()
    options = types.HttpOptions(
        client_args={"transport": wire},
        async_client_args={"transport": wire},
        retry_options=types.HttpRetryOptions(attempts=1),
    )
    if create is None:
        client = genai.Client(
            api_key="offline-key", enterprise=False, http_options=options
        )
    else:
        original = genai.Client.__init__

        def initialize(self, *args, **kwargs):
            http_options = kwargs["http_options"]
            http_options.client_args = {"transport": wire}
            http_options.async_client_args = {"transport": wire}
            original(self, *args, **kwargs)

        with patch.object(genai.Client, "__init__", initialize):
            client = create()
    return client, wire
