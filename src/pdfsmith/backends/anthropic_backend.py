"""Anthropic PDF requests with explicit completion and reported usage."""

import base64
import hashlib
import importlib.metadata
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.backends._cleanup import close_client
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("anthropic")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False


class AnthropicBackend:
    name = "anthropic"
    options_schema = {
        "model": Option("claude-haiku-4-5-20251001", str),
        "max_tokens": Option(8192, int, minimum=1),
        "request_timeout": Option(180.0, float, minimum=0.001),
    }

    def __init__(
        self, model: str = "claude-haiku-4-5-20251001", **options: Any
    ) -> None:
        self._options = normalize_options(
            self.name, {"model": model, **options}, self.options_schema
        )
        if not self._options["model"].strip():
            raise ValueError("anthropic.model must be nonempty")
        self._last_usage: dict[str, Any] | None = None

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        import anthropic

        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Set ANTHROPIC_API_KEY before Anthropic parsing")
        return anthropic.Anthropic(
            api_key=key, max_retries=0, timeout=self._options["request_timeout"]
        )

    def get_cost_info(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "model": self._options["model"],
            "pricing": None,
            "last_parsing_cost": None,
            "total_cost": None,
            "usage": deepcopy(self._last_usage),
        }

    def parse(self, pdf_path: Path) -> str:
        self._last_usage = None
        path = validate_input(pdf_path)
        if path.stat().st_size * 4 // 3 > 32_000_000:
            raise ValueError("Anthropic base64 PDF exceeds the 32MB request limit")
        count = pdf_page_count(path)
        if count > 100:
            raise ValueError("This Anthropic wrapper supports at most 100 PDF pages")
        raw = path.read_bytes()
        data = base64.b64encode(raw).decode("ascii")
        request = {
            "model": self._options["model"],
            "max_tokens": self._options["max_tokens"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": data,
                            },
                        },
                        {"type": "text", "text": PDF_TO_MARKDOWN_PROMPT},
                    ],
                }
            ],
        }
        if len(json.dumps(request, separators=(",", ":")).encode()) > 32_000_000:
            raise ValueError("Anthropic PDF and prompt exceed the 32MB request limit")
        client = self._create_client()
        content = None
        resources = {}
        try:
            message = client.messages.create(**request)
            if isinstance(message.id, str) and message.id:
                resources["message_id"] = message.id
            usage = message.usage
            self._last_usage = {
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "requested_model": self._options["model"],
                "response_model": message.model,
                "message_id": message.id,
                "tokens": usage.model_dump(mode="json", exclude_none=True)
                if usage is not None
                else None,
            }
            if message.role != "assistant" or message.stop_reason != "end_turn":
                raise RuntimeError(
                    f"Anthropic did not complete extraction: {message.stop_reason}"
                )
            if not resources or not message.content:
                raise RuntimeError("Anthropic omitted message identity or text content")
            parts = []
            for block in message.content:
                if block.type != "text" or not isinstance(block.text, str):
                    raise RuntimeError(
                        "Anthropic returned unexpected non-text extraction content"
                    )
                parts.append(block.text)
            content = "".join(parts)
            return content
        except Exception as exc:
            import anthropic

            if isinstance(exc, anthropic.APIConnectionError) or (
                isinstance(exc, anthropic.APIStatusError)
                and (exc.status_code >= 500 or exc.status_code == 408)
            ):
                raise BackendOperationError(
                    "Anthropic response completion is unknown; request was not retried",
                    resource_ids=resources,
                    completion_unknown=True,
                ) from exc
            raise
        finally:
            close_client(
                client,
                self.name,
                content=content,
                resource_ids=resources,
                primary=sys.exc_info()[1],
            )


PDF_TO_MARKDOWN_PROMPT = """Convert this PDF document to clean Markdown.

Instructions:
1. Preserve the document structure (headings, paragraphs, lists)
2. Convert tables to Markdown table format
3. Preserve any important formatting (bold, italic, code)
4. Extract text accurately, maintaining reading order
5. For multi-column layouts, merge into single-column reading order
6. Include figure/image captions as descriptive text
7. Do not add any commentary or explanations - just output the converted content

Output only the Markdown content, nothing else."""
