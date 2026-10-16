"""OpenAI PDF file inputs with terminal completion and owned upload cleanup."""

import hashlib
import importlib.metadata
import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("openai")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False


class OpenAIBackend:
    name = "openai"
    options_schema = {
        "model": Option("gpt-4o-mini", str),
        "max_completion_tokens": Option(8192, int, minimum=1),
        "request_timeout": Option(180.0, float, minimum=0.001),
    }

    def __init__(self, model: str = "gpt-4o-mini", **options: Any) -> None:
        self._options = normalize_options(
            self.name, {"model": model, **options}, self.options_schema
        )
        if not self._options["model"].strip():
            raise ValueError("openai.model must be nonempty")
        if (
            self._options["model"]
            in {
                "gpt-4o-mini",
                "gpt-4o-mini-2024-07-18",
            }
            and self._options["max_completion_tokens"] > 16384
        ):
            raise ValueError("gpt-4o-mini supports at most 16,384 output tokens")
        self._last_usage: dict[str, Any] | None = None

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        from openai import OpenAI

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Set OPENAI_API_KEY before OpenAI parsing")
        return OpenAI(
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
        if path.stat().st_size >= 50_000_000:
            raise ValueError("OpenAI PDF file inputs must be under 50,000,000 bytes")
        pdf_page_count(path)
        raw = path.read_bytes()
        client = self._create_client()
        content = None
        file_id = ""
        terminal = False
        uncertain = False
        resources = {}
        try:
            upload = client.files.create(
                file=(path.name, raw, "application/pdf"), purpose="user_data"
            )
            if not isinstance(upload.id, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,200}", upload.id
            ):
                uncertain = True
                raise BackendOperationError(
                    "OpenAI upload identity is unknown", completion_unknown=True
                )
            file_id = upload.id
            resources["file_id"] = file_id
            if upload.status == "error":
                terminal = True
                raise RuntimeError("OpenAI file processing failed")
            response = client.chat.completions.create(
                model=self._options["model"],
                max_completion_tokens=self._options["max_completion_tokens"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "file", "file": {"file_id": file_id}},
                            {"type": "text", "text": PDF_TO_MARKDOWN_PROMPT},
                        ],
                    }
                ],
            )
            terminal = True
            if isinstance(response.id, str) and response.id:
                resources["response_id"] = response.id
            self._last_usage = {
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "requested_model": self._options["model"],
                "response_model": response.model,
                "response_id": response.id,
                "tokens": response.usage.model_dump(mode="json", exclude_none=True)
                if response.usage is not None
                else None,
            }
            if not resources.get("response_id") or len(response.choices) != 1:
                raise RuntimeError("OpenAI omitted a single identified completion")
            choice = response.choices[0]
            if (
                choice.index != 0
                or choice.finish_reason != "stop"
                or choice.message.refusal
            ):
                raise RuntimeError(
                    f"OpenAI extraction did not complete: {choice.finish_reason}; "
                    f"refusal={bool(choice.message.refusal)}"
                )
            if choice.message.role != "assistant" or not isinstance(
                choice.message.content, str
            ):
                raise RuntimeError("OpenAI omitted assistant text content")
            content = choice.message.content
            return content
        except Exception as exc:
            import openai

            if isinstance(
                exc, openai.APIConnectionError | openai.APIResponseValidationError
            ) or (
                isinstance(exc, openai.APIStatusError)
                and (exc.status_code >= 500 or exc.status_code == 408)
            ):
                uncertain = True
                raise BackendOperationError(
                    "OpenAI request completion is unknown; "
                    "owned file was retained where known",
                    resource_ids=resources,
                    completion_unknown=True,
                ) from exc
            if isinstance(exc, openai.APIStatusError) and 400 <= exc.status_code < 500:
                terminal = True
            raise
        finally:
            primary = sys.exc_info()[1]
            cleanup_errors = []
            if file_id and terminal:
                try:
                    result = client.files.delete(file_id)
                    if result.id != file_id or result.deleted is not True:
                        raise RuntimeError("OpenAI did not confirm owned file deletion")
                except Exception as exc:
                    from openai import NotFoundError

                    if not isinstance(exc, NotFoundError):
                        cleanup_errors.append(
                            f"files.delete: {type(exc).__name__}: {exc}"
                        )
            try:
                client.close()
            except Exception as exc:
                cleanup_errors.append(f"client.close: {type(exc).__name__}: {exc}")
            if cleanup_errors:
                if isinstance(primary, BackendOperationError):
                    cleanup_errors = [*primary.cleanup_errors, *cleanup_errors]
                raise BackendOperationError(
                    "OpenAI resource cleanup failed",
                    parse_completed=content is not None,
                    recovered_content=content,
                    resource_ids=resources,
                    completion_unknown=uncertain,
                    cleanup_errors=tuple(cleanup_errors),
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
