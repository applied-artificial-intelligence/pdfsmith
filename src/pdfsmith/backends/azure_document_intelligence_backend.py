"""Bounded Azure document analysis with complete pages and owned result cleanup."""

import importlib.metadata
import io
import os
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("azure-ai-documentintelligence")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False


class AzureDocumentIntelligenceBackend:
    name = "azure_document_intelligence"
    options_schema = {
        "endpoint": Option(None, str, allow_none=True),
        "model_id": Option("prebuilt-read", str, ("prebuilt-read", "prebuilt-layout")),
        "output_format": Option("text", str, ("text", "markdown")),
        "max_wait": Option(180.0, float, minimum=0.001),
        "poll_interval": Option(1.0, float, minimum=0.001),
        "request_timeout": Option(60.0, float, minimum=0.001),
    }

    def __init__(
        self, endpoint: str | None = None, api_key: str | None = None, **options: Any
    ) -> None:
        if api_key is not None and not isinstance(api_key, str):
            raise ValueError("Azure api_key must be a string")
        self._api_key = api_key
        explicit = {
            **options,
            "endpoint": endpoint
            if endpoint is not None
            else os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        }
        self._options = normalize_options(self.name, explicit, self.options_schema)
        endpoint = self._options["endpoint"]
        if endpoint is not None:
            parsed = urlparse(endpoint)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Azure endpoint must be an HTTPS service URL")
            self._options["endpoint"] = endpoint.rstrip("/")
        if (
            self._options["output_format"] == "markdown"
            and self._options["model_id"] != "prebuilt-layout"
        ):
            raise ValueError("Azure Markdown output requires prebuilt-layout")

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        endpoint = self._options["endpoint"]
        key = self._api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not endpoint or not key:
            raise RuntimeError(
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
                "AZURE_DOCUMENT_INTELLIGENCE_KEY before Azure parsing"
            )
        return DocumentIntelligenceClient(
            endpoint,
            AzureKeyCredential(key),
            api_version="2024-11-30",
            retry_total=0,
            redirect_max=0,
        )

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        if path.stat().st_size > 500_000_000:
            raise ValueError(
                "Azure PDF exceeds the 500,000,000-byte standard-tier limit"
            )
        data = path.read_bytes()
        from pypdf import PdfReader

        document = PdfReader(io.BytesIO(data))
        if document.is_encrypted:
            raise ValueError("Encrypted PDFs are unsupported by Azure analysis")
        count = len(document.pages)
        if not 1 <= count <= 2000:
            raise ValueError("Azure standard-tier parsing requires 1-2000 pages")
        client = self._create_client()
        content = None
        resources: dict[str, str] = {}
        terminal = False
        submitted = False
        model = self._options["model_id"]
        location: list[str] = []
        cleanup_errors = []
        deadline = time.monotonic() + self._options["max_wait"]

        def capture(response: Any) -> None:
            value = response.http_response.headers.get("operation-location")
            if value:
                location.append(value)

        try:
            from azure.ai.documentintelligence.models import AnalyzeResult
            from azure.core.rest import HttpRequest

            submitted = True
            with io.BytesIO(data) as stream:
                # NoPolling prevents an SDK background thread outliving our deadline.
                poller = client.begin_analyze_document(
                    model_id=model,
                    body=stream,
                    content_type="application/octet-stream",
                    output_content_format=self._options["output_format"],
                    string_index_type="unicodeCodePoint",
                    polling=False,
                    raw_response_hook=capture,
                    connection_timeout=min(
                        10.0,
                        self._options["request_timeout"],
                        self._options["max_wait"],
                    ),
                    read_timeout=min(
                        self._options["request_timeout"], self._options["max_wait"]
                    ),
                )
            if len(location) != 1:
                raise RuntimeError("Azure omitted its operation location")
            url = urlparse(location[0])
            endpoint = urlparse(self._options["endpoint"])
            prefix = (
                endpoint.path.rstrip("/")
                + f"/documentintelligence/documentModels/{model}/analyzeResults/"
            )
            if (
                (url.scheme, url.hostname, url.port or 443)
                != (endpoint.scheme, endpoint.hostname, endpoint.port or 443)
                or url.username
                or url.password
                or not url.path.startswith(prefix)
            ):
                raise RuntimeError("Azure returned an unexpected operation destination")
            operation = poller.details.get("operation_id")
            if not isinstance(operation, str) or not operation:
                raise RuntimeError("Azure omitted operation identity")
            resources.update(operation_id=operation, model_id=model)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "Azure analysis deadline exceeded; remote completion is unknown"
                    )
                response = client.send_request(
                    HttpRequest("GET", location[0]),
                    connection_timeout=min(10.0, remaining),
                    read_timeout=min(self._options["request_timeout"], remaining),
                )
                try:
                    if response.status_code != 200:
                        from azure.core.exceptions import HttpResponseError

                        raise HttpResponseError(response=response)
                    payload = response.json()
                finally:
                    response.close()
                status = payload.get("status")
                if status in {"failed", "canceled"}:
                    terminal = True
                    raise RuntimeError(f"Azure analysis terminated with {status}")
                if status == "succeeded":
                    terminal = True
                    body = payload.get("analyzeResult")
                    if not isinstance(body, dict):
                        raise RuntimeError("Azure omitted its analysis result")
                    result = AnalyzeResult(body)
                    if result.model_id != model or result.api_version != "2024-11-30":
                        raise RuntimeError(
                            "Azure analysis identity did not match the request"
                        )
                    if not result.pages or [
                        p.page_number for p in result.pages
                    ] != list(range(1, count + 1)):
                        raise RuntimeError("Azure returned incomplete page coverage")
                    if (
                        self._options["output_format"] == "markdown"
                        and result.content_format != "markdown"
                    ):
                        raise RuntimeError("Azure did not confirm Markdown output")
                    if not isinstance(result.content, str):
                        raise RuntimeError("Azure omitted document content")
                    content = result.content
                    return content
                if status not in {"notStarted", "running"}:
                    raise RuntimeError("Azure returned an unknown analysis state")
                time.sleep(
                    min(
                        self._options["poll_interval"],
                        max(0, deadline - time.monotonic()),
                    )
                )
        except Exception as exc:
            from azure.core.exceptions import HttpResponseError

            rejected = (
                isinstance(exc, HttpResponseError)
                and exc.status_code in {400, 401, 403, 404, 415, 422, 429}
                and not resources
            )
            if submitted and not terminal and not rejected:
                raise BackendOperationError(
                    "Azure remote completion is unknown; result was retained",
                    resource_ids=resources,
                    completion_unknown=True,
                ) from exc
            raise
        finally:
            primary = sys.exc_info()[1]
            if terminal and resources:
                try:
                    client.delete_analyze_result(
                        model,
                        resources["operation_id"],
                        connection_timeout=min(10.0, self._options["request_timeout"]),
                        read_timeout=self._options["request_timeout"],
                    )
                except Exception as exc:
                    from azure.core.exceptions import ResourceNotFoundError

                    if not isinstance(exc, ResourceNotFoundError):
                        cleanup_errors.append(
                            f"delete_analyze_result: {type(exc).__name__}: {exc}"
                        )
            try:
                client.close()
            except Exception as exc:
                cleanup_errors.append(f"client.close: {type(exc).__name__}: {exc}")
            if cleanup_errors:
                if isinstance(primary, BackendOperationError):
                    cleanup_errors = [*primary.cleanup_errors, *cleanup_errors]
                raise BackendOperationError(
                    "Azure resource cleanup failed",
                    parse_completed=content is not None,
                    recovered_content=content,
                    resource_ids=resources,
                    completion_unknown=submitted and not terminal,
                    cleanup_errors=tuple(cleanup_errors),
                ) from primary
