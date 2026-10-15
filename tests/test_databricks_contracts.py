"""Real Databricks SDK wire contracts without workspace execution."""

import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.databricks_backend import DatabricksBackend
from pdfsmith.errors import BackendOperationError

OPTIONS = {
    "host": "https://offline.databricks.invalid",
    "warehouse_id": "warehouse",
    "poll_interval": 0.001,
}


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "pending",
        "blank",
        "page-error",
        "missing-pages",
        "missing-text",
        "wrong-version",
        "wrong-order",
        "failed",
        "truncated",
        "missing-result",
        "empty-result",
        "extra-result",
        "malformed-json",
        "timeout",
        "cancel-complete",
        "cancel-error",
        "close-error",
        "ambiguous-submit",
        "missing-identity",
    ],
)
def test_databricks_reads_document_schema_and_never_publishes_failed_results(
    case, multipage_pdf
):
    pytest.importorskip("databricks.sdk")
    pytest.importorskip("pypdf")
    from tests.databricks_transport import databricks_client

    client, wire = databricks_client(case)
    options = {
        **OPTIONS,
        "max_wait": 0.02
        if case in {"timeout", "cancel-complete", "cancel-error"}
        else 5,
    }
    expected = {
        "page-error": "failed or unknown pages",
        "missing-pages": "page coverage",
        "missing-text": "element content",
        "wrong-version": "schema version",
        "wrong-order": "unordered document elements",
        "failed": "Controlled SQL failure",
        "truncated": "one-row result metadata",
        "empty-result": "incomplete result chunk",
        "extra-result": "one-row result metadata",
        "malformed-json": "malformed document JSON",
    }
    with patch.object(DatabricksBackend, "_create_client", return_value=client):
        if case in {"complete", "pending", "blank", "missing-result"}:
            text = parse(multipage_pdf, backend="databricks", backend_options=options)
            assert text == (
                "" if case == "blank" else "FIRST PAGE SENTINEL\n\nFINAL PAGE SENTINEL"
            )
            if case == "missing-result":
                assert any("/result/chunks/0" in call["path"] for call in wire.calls)
        else:
            with pytest.raises(RuntimeError) as caught:
                parse(multipage_pdf, backend="databricks", backend_options=options)
            if case in expected:
                assert expected[case] in str(caught.value)
            if case == "close-error":
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            if case in {
                "timeout",
                "cancel-complete",
                "cancel-error",
                "ambiguous-submit",
                "missing-identity",
            }:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.completion_unknown == (case != "cancel-complete")
                if case not in {"ambiguous-submit", "missing-identity"}:
                    assert (
                        caught.value.resource_ids["statement_id"] == "owned-statement"
                    )
                    assert wire.cancelled
    assert wire.closed
    posts = [call for call in wire.calls if call["path"] == "/api/2.0/sql/statements"]
    assert len(posts) == 1
    assert not posts[0].get("legacy_sql")


def test_databricks_constructor_needs_no_sdk_credentials_or_warehouse_discovery():
    code = """import sys,socket
from pdfsmith.backends.databricks_backend import DatabricksBackend
def denied(*a,**kw):raise RuntimeError('Constructor attempted network')
socket.socket.connect=denied;socket.getaddrinfo=denied
DatabricksBackend()
assert 'databricks.sdk' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_databricks_missing_input_precedes_credentials_and_sdk_work(tmp_path):
    with (
        patch.object(DatabricksBackend, "_create_client") as create,
        pytest.raises(FileNotFoundError),
    ):
        parse(tmp_path / "missing.pdf", backend="databricks")
    create.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"host": "http://workspace.invalid"},
        {"warehouse_id": "x/other"},
        {"unknown": True},
        {"max_wait": True},
    ],
)
def test_databricks_invalid_options_fail_before_client_work(options):
    with pytest.raises(ValueError):
        DatabricksBackend(**options)


def test_databricks_real_client_factory_accepts_its_configuration(
    monkeypatch, multipage_pdf
):
    pytest.importorskip("databricks.sdk")
    from tests.databricks_transport import databricks_client

    monkeypatch.setenv("DATABRICKS_TOKEN", "offline-token")
    backend = DatabricksBackend(**OPTIONS)
    client, wire = databricks_client(create=backend._create_client)
    with patch.object(backend, "_create_client", return_value=client):
        assert "FINAL PAGE SENTINEL" in backend.parse(multipage_pdf)
    assert wire.closed
