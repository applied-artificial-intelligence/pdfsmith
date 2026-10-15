"""Gemini PDF extraction with typed candidate status and owned client cleanup."""

import asyncio
import hashlib
import importlib.metadata
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("google-genai")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False


class GeminiBackend:
    name = "gemini"
    options_schema = {
        "model": Option("gemini-2.5-flash", str),
        "max_output_tokens": Option(8192, int, minimum=1),
        "request_timeout": Option(180.0, float, minimum=0.001),
    }

    def __init__(self, model: str = "gemini-2.5-flash", **options: Any) -> None:
        self._options = normalize_options(
            self.name, {"model": model, **options}, self.options_schema
        )
        if not self._options["model"].strip():
            raise ValueError("gemini.model must be nonempty")
        self._last_usage: dict[str, Any] | None = None

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        from google import genai
        from google.genai import types

        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "Set GOOGLE_API_KEY or GEMINI_API_KEY before Gemini parsing"
            )
        return genai.Client(
            api_key=key,
            enterprise=False,
            http_options=types.HttpOptions(
                timeout=max(1, math.ceil(self._options["request_timeout"] * 1000)),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
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
        if path.stat().st_size > 50_000_000:
            raise ValueError("Gemini PDF inputs support at most 50,000,000 bytes")
        if pdf_page_count(path) > 1000:
            raise ValueError("Gemini PDF inputs support at most 1000 pages")
        raw = path.read_bytes()
        client = self._create_client()
        content = None
        resources = {}
        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self._options["model"],
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(
                                data=raw, mime_type="application/pdf"
                            ),
                            types.Part.from_text(text=PDF_TO_MARKDOWN_PROMPT),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    max_output_tokens=self._options["max_output_tokens"],
                    candidate_count=1,
                    response_modalities=["TEXT"],
                ),
            )
            if response.response_id:
                resources["response_id"] = response.response_id
            self._last_usage = {
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "requested_model": self._options["model"],
                "response_model": response.model_version,
                "response_id": response.response_id,
                "tokens": response.usage_metadata.model_dump(
                    mode="json", exclude_none=True
                )
                if response.usage_metadata is not None
                else None,
            }
            feedback = response.prompt_feedback
            reason = feedback.block_reason if feedback else None
            if getattr(reason, "value", reason) not in {
                None,
                "BLOCK_REASON_UNSPECIFIED",
            }:
                raise RuntimeError(f"Gemini blocked the document request: {reason}")
            if not response.candidates or len(response.candidates) != 1:
                raise RuntimeError("Gemini omitted a single complete candidate")
            candidate = response.candidates[0]
            if (
                candidate.index not in {None, 0}
                or candidate.finish_reason != types.FinishReason.STOP
            ):
                raise RuntimeError(
                    f"Gemini extraction did not complete: {candidate.finish_reason}"
                )
            result = candidate.content
            if result is None or result.role not in {None, "model"} or not result.parts:
                raise RuntimeError("Gemini omitted candidate text content")
            parts = []
            for part in result.parts:
                if part.thought:
                    continue
                extras = part.model_dump(
                    exclude_none=True, exclude={"text", "thought", "thought_signature"}
                )
                if not isinstance(part.text, str) or extras:
                    raise RuntimeError("Gemini returned non-text extraction content")
                parts.append(part.text)
            if not parts:
                raise RuntimeError("Gemini omitted final text content")
            content = "".join(parts)
            return content
        except Exception as exc:
            import httpx
            from google.genai import errors as genai_errors

            if isinstance(exc, httpx.TransportError) or (
                isinstance(exc, genai_errors.APIError)
                and (exc.code >= 500 or exc.code == 408)
            ):
                raise BackendOperationError(
                    "Gemini request completion is unknown; request was not retried",
                    resource_ids=resources,
                    completion_unknown=True,
                ) from exc
            raise
        finally:
            primary = sys.exc_info()[1]
            errors = []
            try:
                client.close()
            except Exception as exc:
                errors.append(f"client.close: {type(exc).__name__}: {exc}")
            try:
                # Close the SDK async client on an owned loop.
                # Direct synchronous callers can already have a running loop.
                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(lambda: asyncio.run(client.aio.aclose())).result()
            except Exception as exc:
                errors.append(f"client.aio.aclose: {type(exc).__name__}: {exc}")
            if errors:
                uncertain = (
                    isinstance(primary, BackendOperationError)
                    and primary.completion_unknown
                )
                if isinstance(primary, BackendOperationError):
                    errors = [*primary.cleanup_errors, *errors]
                raise BackendOperationError(
                    "Gemini resource cleanup failed",
                    parse_completed=content is not None,
                    recovered_content=content,
                    resource_ids=resources,
                    completion_unknown=uncertain,
                    cleanup_errors=tuple(errors),
                ) from primary


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
