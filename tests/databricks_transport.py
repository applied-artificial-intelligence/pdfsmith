"""Databricks SDK statement serialization over an offline requests adapter."""

import base64
import io
import json
import re
from unittest.mock import patch
from urllib.parse import urlparse


def databricks_client(case="complete", create=None):
    import requests
    from databricks.sdk import WorkspaceClient

    class Wire(requests.adapters.BaseAdapter):
        def __init__(self):
            self.calls = []
            self.closed = False
            self.cancelled = False
            self.pages = 2

        def close(self):
            self.closed = True
            if case == "close-error":
                raise RuntimeError("Controlled Databricks session close error")

        def parsed(self):
            value = {
                "document": {
                    "pages": [{"id": n} for n in range(self.pages)],
                    "elements": [
                        {"id": 0, "type": "text", "content": "FIRST PAGE SENTINEL"},
                        {"id": 1, "type": "text", "content": "FINAL PAGE SENTINEL"},
                    ],
                },
                "error_status": [],
                "metadata": {"id": "offline-document", "version": "2.0"},
            }
            if case == "blank":
                value["document"]["elements"] = []
            if case == "page-error":
                value["error_status"] = [
                    {"page_id": 1, "error_message": "Controlled failed page"}
                ]
            if case == "missing-pages":
                value["document"]["pages"] = []
            if case == "missing-text":
                value["document"]["elements"][1].pop("content")
            if case == "wrong-version":
                value["metadata"]["version"] = "3.0"
            if case == "wrong-order":
                value["document"]["elements"].reverse()
            return json.dumps(value)

        def statement(self, state="SUCCEEDED"):
            result = {"statement_id": "owned-statement", "status": {"state": state}}
            if case == "missing-identity":
                result.pop("statement_id")
            if state == "FAILED":
                result["status"]["error"] = {
                    "error_code": "BAD_REQUEST",
                    "message": "Controlled SQL failure",
                }
            if state == "SUCCEEDED":
                result["manifest"] = {
                    "format": "JSON_ARRAY",
                    "total_chunk_count": 1,
                    "total_row_count": 1,
                    "truncated": case == "truncated",
                    "schema": {
                        "column_count": 1,
                        "columns": [
                            {
                                "name": "result",
                                "position": 0,
                                "type_name": "STRING",
                                "type_text": "STRING",
                            }
                        ],
                    },
                    "chunks": [{"chunk_index": 0, "row_count": 1, "row_offset": 0}],
                }
                result["result"] = {
                    "chunk_index": 0,
                    "row_count": 1,
                    "row_offset": 0,
                    "data_array": [[self.parsed()]],
                }
                if case == "missing-result":
                    result.pop("result")
                if case == "empty-result":
                    result["result"]["data_array"] = []
                if case == "extra-result":
                    result["manifest"]["total_row_count"] = 2
                if case == "malformed-json":
                    result["result"]["data_array"] = [["not JSON"]]
            return result

        def send(self, request, **kwargs):
            from pypdf import PdfReader

            path = urlparse(request.url).path
            entry = {"method": request.method, "path": path}
            self.calls.append(entry)
            status = 200
            if path.endswith("/.well-known/databricks-config"):
                data = {}
            elif path == "/api/2.0/sql/statements" and request.method == "POST":
                body = json.loads(request.body)
                sql = body["statement"]
                entry["statement"] = sql
                match = re.search(r"unbase64\('([A-Za-z0-9+/=]+)'\)", sql)
                if match:
                    raw = base64.b64decode(match[1], validate=True)
                    assert raw.startswith(b"%PDF-")
                    self.pages = len(PdfReader(io.BytesIO(raw)).pages)
                    assert "'version', '2.0'" in sql
                    assert "'descriptionElementTypes', ''" in sql
                else:
                    entry["legacy_sql"] = True
                if case == "ambiguous-submit":
                    status = 500
                    data = {
                        "error_code": "INTERNAL_ERROR",
                        "message": "Controlled submission error",
                    }
                else:
                    data = self.statement(
                        "PENDING"
                        if case
                        in {"pending", "timeout", "cancel-complete", "cancel-error"}
                        else "FAILED"
                        if case == "failed"
                        else "SUCCEEDED"
                    )
            elif path.endswith("/cancel"):
                self.cancelled = True
                data = {}
                if case == "cancel-error":
                    status = 403
                    data = {
                        "error_code": "PERMISSION_DENIED",
                        "message": "Controlled cancellation error",
                    }
            elif "/result/chunks/" in path:
                data = (
                    self.statement()["result"]
                    if case != "missing-result"
                    else {
                        "chunk_index": 0,
                        "row_count": 1,
                        "row_offset": 0,
                        "data_array": [[self.parsed()]],
                    }
                )
            elif path.endswith("/owned-statement"):
                data = self.statement(
                    "CANCELED"
                    if self.cancelled and case == "cancel-complete"
                    else "RUNNING"
                    if case in {"timeout", "cancel-error", "cancel-complete"}
                    else "SUCCEEDED"
                )
            else:
                raise AssertionError(
                    f"Unexpected Databricks HTTP request: {request.method} {path}"
                )
            response = requests.Response()
            response.status_code = status
            response.url = request.url
            response.request = request
            response.headers["content-type"] = "application/json"
            response._content = json.dumps(data).encode()
            response.raw = io.BytesIO(response._content)
            return response

    wire = Wire()

    # New SDK config consults the workspace metadata endpoint at construction.
    # Keep that actual SDK request on the same controlled transport.
    def send(session, request, **kwargs):
        return wire.send(request, **kwargs)

    with patch.object(requests.Session, "send", send):
        client = (
            create()
            if create
            else WorkspaceClient(
                host="https://offline.databricks.invalid",
                token="offline-token",
                auth_type="pat",
            )
        )
    client.api_client._api_client._session.mount("https://", wire)
    return client, wire
