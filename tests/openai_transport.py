"""Actual OpenAI SDK upload/completion/delete requests on an offline transport."""

import hashlib
import json
from email.parser import BytesParser
from unittest.mock import patch


def openai_client(case="complete", create=None):
    import httpx2
    import openai

    class Wire(httpx2.MockTransport):
        def __init__(self):
            self.calls = []
            self.closed = False
            super().__init__(self.respond)

        def close(self):
            self.closed = True
            if case == "close-error":
                raise RuntimeError("Controlled OpenAI client close failure")
            super().close()

        def respond(self, request):
            entry = {"method": request.method, "path": request.url.path}
            self.calls.append(entry)
            if request.method == "POST" and request.url.path == "/v1/files":
                message = BytesParser().parsebytes(
                    (
                        "Content-Type: " + request.headers["content-type"] + "\r\n\r\n"
                    ).encode()
                    + request.content
                )
                fields = {
                    part.get_param(
                        "name", header="content-disposition"
                    ): part.get_payload(decode=True)
                    for part in message.walk()
                    if part.get_content_disposition() == "form-data"
                }
                assert fields["purpose"] == b"user_data" and fields["file"].startswith(
                    b"%PDF-"
                )
                entry["input_sha256"] = hashlib.sha256(fields["file"]).hexdigest()
                body = {
                    "id": "file-owned",
                    "object": "file",
                    "bytes": len(fields["file"]),
                    "created_at": 0,
                    "filename": "document.pdf",
                    "purpose": "user_data",
                    "status": "processed",
                }
                if case == "upload-error":
                    return httpx2.Response(
                        500,
                        json={
                            "error": {
                                "message": "Controlled upload ambiguity",
                                "type": "server_error",
                            }
                        },
                    )
            elif (
                request.method == "POST" and request.url.path == "/v1/chat/completions"
            ):
                sent = json.loads(request.content)
                entry["model"] = sent["model"]
                entry["max_completion_tokens"] = sent.get("max_completion_tokens")
                assert sent["messages"][0]["content"][0] == {
                    "type": "file",
                    "file": {"file_id": "file-owned"},
                }
                if case in {
                    "generation-error",
                    "ambiguous-generation",
                    "generation-and-delete-error",
                }:
                    return httpx2.Response(
                        500 if case == "ambiguous-generation" else 400,
                        json={
                            "error": {
                                "message": "Controlled generation error",
                                "type": "invalid_request_error",
                            }
                        },
                    )
                body = {
                    "id": "chat-owned",
                    "object": "chat.completion",
                    "created": 0,
                    "model": sent["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL",
                                "refusal": None,
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 13,
                        "completion_tokens": 7,
                        "total_tokens": 20,
                    },
                }
                if case in {"length", "content_filter", "tool_calls"}:
                    body["choices"][0]["finish_reason"] = case
                if case == "refusal":
                    body["choices"][0]["message"]["refusal"] = "Controlled refusal"
                if case == "blank":
                    body["choices"][0]["message"]["content"] = ""
                if case == "missing-content":
                    body["choices"][0]["message"]["content"] = None
                if case == "missing-choices":
                    body["choices"] = []
                if case == "missing-usage":
                    body["usage"] = None
                if case == "extra-choice":
                    body["choices"].append(
                        {
                            "index": 1,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "extra"},
                        }
                    )
            elif (
                request.method == "DELETE"
                and request.url.path == "/v1/files/file-owned"
            ):
                if case in {"delete-error", "generation-and-delete-error"}:
                    return httpx2.Response(
                        403,
                        json={
                            "error": {
                                "message": "Controlled delete failure",
                                "type": "permission_error",
                            }
                        },
                    )
                body = {
                    "id": "file-owned",
                    "object": "file",
                    "deleted": case != "delete-unconfirmed",
                }
            else:
                raise AssertionError(
                    f"Unexpected OpenAI request: {request.method} {request.url.path}"
                )
            return httpx2.Response(
                200, json=body, headers={"x-request-id": "offline-request"}
            )

    wire = Wire()
    if create is None:
        client = openai.OpenAI(
            api_key="offline-key",
            max_retries=0,
            http_client=httpx2.Client(transport=wire),
        )
    else:
        original = openai.OpenAI.__init__

        def initialize(self, *args, **kwargs):
            kwargs["http_client"] = httpx2.Client(transport=wire)
            original(self, *args, **kwargs)

        with patch.object(openai.OpenAI, "__init__", initialize):
            client = create()
    return client, wire
