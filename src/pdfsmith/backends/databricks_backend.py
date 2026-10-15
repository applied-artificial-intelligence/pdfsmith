"""Databricks SQL document parsing with explicit warehouse and complete results."""

import base64
import importlib.metadata
import json
import os
import re
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.backends._cleanup import close_client
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("databricks-sdk")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False

MAX_INPUT_BYTES = 10_000_000


class DatabricksBackend:
    name = "databricks"
    options_schema = {
        "host": Option(None, str, allow_none=True),
        "warehouse_id": Option(None, str, allow_none=True),
        "max_wait": Option(180.0, float, minimum=0.001),
        "poll_interval": Option(1.0, float, minimum=0.001),
        "request_timeout": Option(60.0, float, minimum=0.001),
    }

    def __init__(self, **options: Any) -> None:
        explicit = {
            key: os.environ[env]
            for key, env in {
                "host": "DATABRICKS_HOST",
                "warehouse_id": "DATABRICKS_WAREHOUSE_ID",
            }.items()
            if env in os.environ
        }
        self._options = normalize_options(
            self.name, {**explicit, **options}, self.options_schema
        )
        host = self._options["host"]
        if host is not None:
            parsed = urlparse(host)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Databricks host must be an HTTPS workspace origin")
            self._options["host"] = host.rstrip("/")
        warehouse = self._options["warehouse_id"]
        if warehouse is not None and not re.fullmatch(r"[A-Za-z0-9-]+", warehouse):
            raise ValueError("Databricks warehouse_id must be a resource ID")

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.config import Config

        token = os.getenv("DATABRICKS_TOKEN")
        client_id = os.getenv("DATABRICKS_CLIENT_ID")
        secret = os.getenv("DATABRICKS_CLIENT_SECRET")
        if not token and not (client_id and secret):
            raise RuntimeError(
                "Databricks requires DATABRICKS_TOKEN or OAuth M2M client credentials"
            )
        return WorkspaceClient(
            config=Config(
                host=self._options["host"],
                token=token,
                client_id=client_id if not token else None,
                client_secret=secret if not token else None,
                auth_type="pat" if token else "oauth-m2m",
                http_timeout_seconds=self._options["request_timeout"],
                disable_async_token_refresh=True,
            )
        )

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(
                "Databricks inline parsing supports PDFs up to 10,000,000 bytes"
            )
        count = pdf_page_count(path)
        if count > 500:
            raise ValueError(
                "Databricks full-document parsing supports at most 500 pages"
            )
        if not self._options["host"] or not self._options["warehouse_id"]:
            raise RuntimeError(
                "Databricks requires explicit host and warehouse_id configuration"
            )
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        sql = (
            f"SELECT to_json(ai_parse_document(unbase64('{data}'), "
            "map('version', '2.0', 'descriptionElementTypes', ''))) AS result"
        )
        client = self._create_client()
        http = client.api_client._api_client
        from databricks.sdk.clock import RealClock
        from databricks.sdk.service.sql import Disposition, Format

        class SingleAttemptClock(RealClock):
            def sleep(self, seconds: float) -> None:
                # This SDK has no no-retry switch; stop before any replay or backoff.
                raise RuntimeError(
                    "Databricks SDK retry suppressed"
                ) from sys.exc_info()[1]

        http._clock = SingleAttemptClock()
        service = client.statement_execution
        content = None
        statement_id = ""
        terminal = False
        submitted = False
        resources = {"warehouse_id": self._options["warehouse_id"]}
        deadline = time.monotonic() + self._options["max_wait"]

        def budget() -> None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Databricks statement deadline exceeded")
            http._http_timeout_seconds = min(
                self._options["request_timeout"], remaining
            )

        try:
            budget()
            submitted = True
            statement = service.execute_statement(
                statement=sql,
                warehouse_id=self._options["warehouse_id"],
                wait_timeout="0s",
                disposition=Disposition.INLINE,
                format=Format.JSON_ARRAY,
                byte_limit=25 * 1024 * 1024,
                row_limit=2,
            )
            identity = statement.statement_id
            if not isinstance(identity, str) or not re.fullmatch(
                r"[A-Za-z0-9-]{1,128}", identity
            ):
                raise RuntimeError("Databricks omitted a valid statement identity")
            statement_id = identity
            resources["statement_id"] = statement_id
            while True:
                if statement.statement_id != statement_id:
                    raise RuntimeError("Databricks changed the statement identity")
                state = (
                    statement.status.state.value
                    if statement.status and statement.status.state
                    else None
                )
                if state in {"FAILED", "CANCELED", "CLOSED"}:
                    terminal = True
                    error = statement.status.error
                    raise RuntimeError(
                        f"Databricks statement {state}: "
                        f"{error.message if error else 'no result'}"
                    )
                if state == "SUCCEEDED":
                    terminal = True
                    content = self._read_result(service, statement, count, budget)
                    return content
                if state not in {"PENDING", "RUNNING"}:
                    raise RuntimeError("Databricks returned an unknown statement state")
                budget()
                time.sleep(
                    min(
                        self._options["poll_interval"],
                        max(0, deadline - time.monotonic()),
                    )
                )
                budget()
                statement = service.get_statement(statement_id)
        except Exception as exc:
            from databricks.sdk import errors

            rejected = not statement_id and isinstance(
                exc,
                errors.BadRequest
                | errors.Unauthenticated
                | errors.PermissionDenied
                | errors.NotFound,
            )
            if rejected:
                terminal = True
            if submitted and not terminal and not rejected:
                cleanup_errors = []
                if statement_id:
                    try:
                        http._http_timeout_seconds = min(
                            10.0, self._options["request_timeout"]
                        )
                        service.cancel_execution(statement_id)
                        status = service.get_statement(statement_id)
                        terminal = (
                            status.statement_id == statement_id
                            and status.status is not None
                            and status.status.state is not None
                            and status.status.state.value
                            in {"FAILED", "CANCELED", "CLOSED", "SUCCEEDED"}
                        )
                    except Exception as cancel_error:
                        cleanup_errors.append(
                            f"cancellation: {type(cancel_error).__name__}: "
                            f"{cancel_error}"
                        )
                raise BackendOperationError(
                    "Databricks statement failed; remote state is reported separately",
                    resource_ids=resources,
                    completion_unknown=not terminal,
                    cleanup_errors=tuple(cleanup_errors),
                ) from exc
            raise
        finally:
            close_client(
                http._session,
                self.name,
                content=content,
                resource_ids=resources,
                primary=sys.exc_info()[1],
                completion_unknown=submitted and not terminal,
            )

    @staticmethod
    def _read_result(service: Any, statement: Any, count: int, budget: Any) -> str:
        manifest = statement.manifest
        if (
            manifest is None
            or manifest.truncated
            or manifest.total_row_count != 1
            or manifest.format is None
            or manifest.format.value != "JSON_ARRAY"
            or manifest.schema is None
            or manifest.schema.column_count != 1
            or not manifest.schema.columns
            or len(manifest.schema.columns) != 1
            or manifest.schema.columns[0].name != "result"
        ):
            raise RuntimeError("Databricks omitted complete one-row result metadata")
        chunks = manifest.chunks
        if not chunks or manifest.total_chunk_count != len(chunks):
            raise RuntimeError("Databricks omitted complete chunk metadata")
        if [c.chunk_index for c in chunks] != list(range(len(chunks))):
            raise RuntimeError("Databricks returned missing or duplicate result chunks")
        rows: list[Any] = []
        offset = 0
        for info in chunks:
            if (
                info.row_offset != offset
                or info.row_count is None
                or info.row_count < 0
            ):
                raise RuntimeError("Databricks returned invalid chunk row coverage")
            chunk = statement.result if info.chunk_index == 0 else None
            if chunk is None:
                budget()
                chunk = service.get_statement_result_chunk_n(
                    statement.statement_id, info.chunk_index
                )
            data = chunk.data_array or []
            if (
                chunk.external_links
                or chunk.chunk_index != info.chunk_index
                or chunk.row_offset != offset
                or chunk.row_count != info.row_count
                or len(data) != info.row_count
            ):
                raise RuntimeError("Databricks returned an incomplete result chunk")
            if chunk.next_chunk_index is not None and (
                chunk.next_chunk_index != info.chunk_index + 1
                or chunk.next_chunk_index >= len(chunks)
            ):
                raise RuntimeError("Databricks returned an invalid next chunk")
            rows.extend(data)
            offset += info.row_count
        if (
            offset != 1
            or len(rows) != 1
            or len(rows[0]) != 1
            or not isinstance(rows[0][0], str)
        ):
            raise RuntimeError("Databricks did not return exactly one JSON document")
        try:
            result = json.loads(rows[0][0])
        except ValueError as exc:
            raise RuntimeError("Databricks returned malformed document JSON") from exc
        if not isinstance(result, dict) or result.get("error_status") != []:
            raise RuntimeError("Databricks document reports failed or unknown pages")
        metadata = result.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("version") != "2.0":
            raise RuntimeError("Databricks did not confirm schema version 2.0")
        document = result.get("document")
        if not isinstance(document, dict):
            raise RuntimeError("Databricks omitted the parsed document")
        pages = document.get("pages")
        if not isinstance(pages, list) or [p.get("id") for p in pages] != list(
            range(count)
        ):
            raise RuntimeError("Databricks returned incomplete page coverage")
        elements = document.get("elements")
        if not isinstance(elements, list) or [e.get("id") for e in elements] != list(
            range(len(elements))
        ):
            raise RuntimeError(
                "Databricks returned missing or unordered document elements"
            )
        parts = []
        for element in elements:
            value = element.get("content")
            if value is None and element.get("type") in {"figure", "signature"}:
                continue
            if not isinstance(value, str):
                raise RuntimeError("Databricks omitted element content")
            if value.strip():
                parts.append(value.strip())
        return "\n\n".join(parts)
