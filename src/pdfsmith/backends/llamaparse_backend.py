"""LlamaCloud v2 parsing with explicit service identity and complete page checks."""

import importlib.util
import os
import time
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

AVAILABLE = importlib.util.find_spec("llama_cloud") is not None
PUBLISHED_VERSIONS = ("2026-06-15", "2026-09-28", "2026-09-29")
LANGUAGES = (
    "abq",
    "ady",
    "af",
    "ang",
    "ar",
    "as",
    "ava",
    "az",
    "be",
    "bg",
    "bgc",
    "bh",
    "bho",
    "bn",
    "bs",
    "ch_sim",
    "ch_tra",
    "che",
    "cs",
    "cy",
    "da",
    "dar",
    "de",
    "en",
    "es",
    "et",
    "fa",
    "fr",
    "ga",
    "gom",
    "hi",
    "hr",
    "hu",
    "id",
    "inh",
    "is",
    "it",
    "ja",
    "kbd",
    "kn",
    "ko",
    "ku",
    "la",
    "lbe",
    "lez",
    "lt",
    "lv",
    "mah",
    "mai",
    "mi",
    "mn",
    "mni",
    "mr",
    "ms",
    "mt",
    "ne",
    "new",
    "nl",
    "no",
    "oc",
    "pi",
    "pl",
    "pt",
    "ro",
    "rs_cyrillic",
    "rs_latin",
    "ru",
    "sa",
    "sck",
    "sk",
    "sl",
    "sq",
    "sv",
    "sw",
    "ta",
    "tab",
    "te",
    "th",
    "tjk",
    "tl",
    "tr",
    "ug",
    "uk",
    "ur",
    "uz",
    "vi",
)
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


class LlamaParseBackend:
    name = "llamaparse"
    options_schema = {
        "tier": Option(
            None, str, ("fast", "cost_effective", "agentic", "agentic_plus")
        ),
        "version": Option(None, str, PUBLISHED_VERSIONS),
        "disable_cache": Option(True, bool),
        "language": Option("en", str, LANGUAGES),
        "max_wait_seconds": Option(180.0, float, minimum=0.001),
        "poll_interval_seconds": Option(1.0, float, minimum=0),
        "request_timeout_seconds": Option(60.0, float, minimum=0.001),
    }

    def __init__(self, **options: Any) -> None:
        if "parsing_mode" in options:
            raise ValueError(
                "parsing_mode is retired; supply explicit tier and version"
            )
        if "tier" not in options or "version" not in options:
            raise ValueError("LlamaParse requires explicit tier and published version")
        self._options = normalize_options(self.name, options, self.options_schema)
        self._lock = RLock()
        self._last_result_identity: dict[str, Any] | None = None

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    @property
    def last_result_identity(self) -> dict[str, Any] | None:
        with self._lock:
            return deepcopy(self._last_result_identity)

    def _client(self) -> Any:
        key = os.environ.get("LLAMA_CLOUD_API_KEY")
        if not key:
            raise ValueError(
                "LLAMA_CLOUD_API_KEY must be set for LlamaParse submission"
            )
        try:
            from llama_cloud import LlamaCloud
        except ImportError as exc:
            raise ImportError(
                "Install or upgrade pdfsmith[llamaparse] for v2 support"
            ) from exc
        return LlamaCloud(
            api_key=key,
            max_retries=0,
            timeout=self._options["request_timeout_seconds"],
            _strict_response_validation=True,
        )

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        count = pdf_page_count(path)
        with self._lock:
            return self._parse(path, count)

    def _parse(self, path: Path, page_count: int) -> str:
        self._last_result_identity = {
            "requested_tier": self._options["tier"],
            "requested_version": self._options["version"],
            "disable_cache": self._options["disable_cache"],
            "confirmed_tier": None,
            "confirmed_version": None,
            "provider_echoed_version": None,
            "cache_hit": None,
        }
        client = self._client()
        resources: dict[str, str] = {}
        upload_attempted = False
        submission_attempted = False
        terminal = False
        content: str | None = None
        primary: Exception | None = None
        cleanup_errors = []
        try:
            upload_attempted = True
            with path.open("rb") as stream:
                upload = client.files.create(file=(path.name, stream), purpose="parse")
            resources["file_id"] = upload.id
            submission_attempted = True
            job = client.parsing.create(
                file_id=upload.id,
                tier=self._options["tier"],
                version=self._options["version"],
                disable_cache=self._options["disable_cache"],
                processing_options={
                    "ocr_parameters": {"languages": [self._options["language"]]}
                },
                processing_control={
                    "job_failure_conditions": {"allowed_page_failure_ratio": 0.0}
                },
            )
            resources["job_id"] = job.id
            terminal = job.status in TERMINAL_STATUSES
            deadline = time.monotonic() + self._options["max_wait_seconds"]
            while True:
                result = client.parsing.get(job.id, expand=["markdown"])
                if result.job.id != job.id:
                    raise RuntimeError("LlamaParse returned a different job identifier")
                terminal = result.job.status in TERMINAL_STATUSES
                if terminal:
                    break
                if result.job.status not in {"PENDING", "RUNNING"}:
                    raise RuntimeError("LlamaParse returned an unknown job status")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "LlamaParse job did not complete within max_wait_seconds"
                    )
                time.sleep(min(self._options["poll_interval_seconds"], remaining))
            if result.job.status != "COMPLETED":
                raise RuntimeError(
                    f"LlamaParse job ended with status {result.job.status}"
                )
            identity = self._last_result_identity
            identity["confirmed_tier"] = result.job.tier
            identity["provider_echoed_version"] = (result.raw_parameters or {}).get(
                "version"
            )
            if result.job.tier is not None and result.job.tier != self._options["tier"]:
                raise RuntimeError("LlamaParse confirmed a different tier")
            if identity["provider_echoed_version"] not in (
                None,
                self._options["version"],
            ):
                raise RuntimeError("LlamaParse echoed a different requested version")
            pages = result.markdown.pages if result.markdown is not None else None
            if pages is None or len(pages) != page_count:
                raise RuntimeError(
                    "LlamaParse omitted markdown or complete page coverage"
                )
            parts = []
            for index, page in enumerate(pages, 1):
                if page.page_number != index:
                    raise RuntimeError(
                        "LlamaParse returned missing, duplicate or reordered pages"
                    )
                if page.success is not True or not isinstance(
                    getattr(page, "markdown", None), str
                ):
                    raise RuntimeError(f"LlamaParse failed to parse page {index}")
                parts.append(page.markdown.strip())
            content = "\n\n".join(part for part in parts if part)
        except Exception as exc:
            primary = exc
        finally:
            if "job_id" in resources and not terminal:
                try:
                    cancelled = client.parsing.cancel(resources["job_id"])
                    if cancelled.id != resources["job_id"]:
                        raise RuntimeError(
                            "Cancellation returned a different job identifier"
                        )
                    terminal = cancelled.status in TERMINAL_STATUSES
                except Exception as exc:
                    cleanup_errors.append(
                        f"Job cancellation failed: {type(exc).__name__}"
                    )
            if "job_id" in resources and terminal:
                try:
                    client.parsing.delete(resources["job_id"])
                except Exception as exc:
                    cleanup_errors.append(f"Job cleanup failed: {type(exc).__name__}")
            if "file_id" in resources and (not submission_attempted or terminal):
                try:
                    client.files.delete(resources["file_id"])
                except Exception as exc:
                    cleanup_errors.append(f"File cleanup failed: {type(exc).__name__}")
            try:
                client.close()
            except Exception as exc:
                cleanup_errors.append(f"Client close failed: {type(exc).__name__}")
        completion_unknown = (submission_attempted and not terminal) or (
            upload_attempted and "file_id" not in resources
        )
        if primary is not None or cleanup_errors:
            error = BackendOperationError(
                f"LlamaParse failed: {primary}"
                if primary
                else "LlamaParse cleanup failed after parsing",
                parse_completed=content is not None,
                recovered_content=content,
                resource_ids=resources,
                completion_unknown=completion_unknown,
                cleanup_errors=tuple(cleanup_errors),
            )
            raise error from primary
        assert content is not None
        return content
