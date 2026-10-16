"""Real local-inference SDK protocol checks; no model or live service execution."""

import json
import socket
from unittest.mock import patch

import httpx
from openai import OpenAI
from PIL import Image
from surya.inference.backends import openai_client
from surya.inference.schema import BatchInputItem

from pdfsmith.backends.marker_backend import _completion_guard


def run():
    def denied(*a, **kw):
        raise RuntimeError("No network in Marker SDK transport checks")

    socket.socket.connect = denied
    socket.getaddrinfo = denied
    image = Image.new("RGB", (32, 32), "white")
    items = [
        BatchInputItem(
            image=image,
            prompt_type="high_accuracy_bbox",
            max_tokens=1,
            metadata={"page_idx": i},
        )
        for i in range(2)
    ]
    original = openai_client._generate_one
    results = []
    for label, finish, content, status in [
        ("complete", "stop", "<div>complete</div>", 200),
        ("blank", "stop", "", 200),
        ("truncated", "length", "<div", 200),
        ("unavailable", "stop", "", 503),
    ]:
        requests = []

        def handle(
            request, *, recorded=requests, code=status, reason=finish, text=content
        ):
            body = json.loads(request.content)
            assert body["max_tokens"] == 1
            assert body["model"] == "datalab-to/surya-ocr-2"
            assert body["messages"][0]["content"][0]["image_url"]["url"].startswith(
                "data:image/png;base64,"
            )
            recorded.append(body)
            if code != 200:
                return httpx.Response(
                    code,
                    json={
                        "error": {
                            "message": "Controlled local server failure",
                            "type": "server_error",
                            "code": "unavailable",
                        }
                    },
                )
            return httpx.Response(
                200,
                json={
                    "id": "local-model-response",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "datalab-to/surya-ocr-2",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": reason,
                            "message": {"role": "assistant", "content": text},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 1,
                        "total_tokens": 11,
                    },
                },
            )

        with OpenAI(
            api_key="offline-local-placeholder",
            base_url="http://127.0.0.1:12345/v1",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        ) as client:
            before = original(
                items[0],
                client=client,
                model_name="datalab-to/surya-ocr-2",
                max_tokens_default=1,
                temperature=0,
                top_p=0.1,
                timeout=1,
                request_logprobs_default=False,
            )
            if label == "truncated":
                assert before.error is False and before.raw == "<div"
            requests.clear()
            with patch.object(
                openai_client, "_generate_one", _completion_guard(original)
            ):
                try:
                    after = openai_client.chat_completions_batch(
                        items,
                        client=client,
                        model_name="datalab-to/surya-ocr-2",
                        max_workers=1,
                        max_retries=3,
                        request_logprobs_default=False,
                    )
                except RuntimeError as exc:
                    assert label in {"truncated", "unavailable"}
                    assert len(requests) == 1, "Failed generation was retried or queued"
                    outcome = dict(error=str(exc), requests=len(requests))
                else:
                    assert label in {"complete", "blank"}
                    assert len(after) == 2 and all(not entry.error for entry in after)
                    assert all(entry.raw == content for entry in after)
                    outcome = dict(raw=content, requests=len(requests))
        results.append(
            dict(
                case=label,
                before_error=before.error,
                before_raw=before.raw,
                after=outcome,
            )
        )
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
