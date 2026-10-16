"""Google parsing through real REST/storage SDK transports without cloud access."""

import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend
from pdfsmith.errors import BackendOperationError

OPTIONS = {"project_id": "offline", "processor_id": "processor"}


@pytest.mark.parametrize(
    "case", ["complete", "document-error", "missing-pages", "close-error"]
)
def test_google_sync_rejects_document_errors_and_missing_pages(case, multipage_pdf):
    pytest.importorskip("google.cloud.documentai_v1")
    from tests.google_transport import google_clients

    client, _, wire = google_clients(case)
    with patch.object(GoogleDocumentAIBackend, "_create_client", return_value=client):
        if case == "complete":
            assert "FINAL PAGE SENTINEL" in parse(
                multipage_pdf, backend="google_document_ai", backend_options=OPTIONS
            )
        else:
            with pytest.raises(RuntimeError) as caught:
                parse(
                    multipage_pdf, backend="google_document_ai", backend_options=OPTIONS
                )
            if case == "close-error":
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
    assert wire.closed >= 1


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "individual-error",
        "document-error",
        "wrong-destination",
        "missing-shard",
        "duplicate-shard",
        "timeout",
        "delete-error",
        "close-error",
        "metadata-failed",
        "missing-status",
        "wrong-source",
        "terminal-error",
        "missing-response",
        "text-gap",
        "duplicate-page",
        "cancel-complete",
        "cancel-error",
        "wrong-operation",
        "ambiguous-submit",
    ],
)
def test_google_batch_checks_status_shards_and_owns_resource_cleanup(case, tmp_path):
    pytest.importorskip("google.cloud.documentai_v1")
    pytest.importorskip("google.cloud.storage")
    pypdf = pytest.importorskip("pypdf")
    from tests.google_transport import google_clients

    path = tmp_path / "two-pages.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=300, height=300)
    writer.write(path)
    client, objects, wire = google_clients(case)
    options = {
        **OPTIONS,
        "gcs_bucket": "offline-bucket",
        "mode": "batch",
        "poll_interval": 0.001,
        "max_wait": 0.02
        if case in {"timeout", "cancel-error", "cancel-complete"}
        else 5,
    }
    with (
        patch.object(GoogleDocumentAIBackend, "_create_client", return_value=client),
        patch.object(GoogleDocumentAIBackend, "_create_storage", return_value=objects),
    ):
        if case == "complete":
            assert (
                parse(path, backend="google_document_ai", backend_options=options)
                == "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
        else:
            with pytest.raises(RuntimeError) as caught:
                parse(path, backend="google_document_ai", backend_options=options)
            expected = {
                "individual-error": "document failed",
                "document-error": "document error",
                "wrong-destination": "unowned output",
                "missing-shard": "missing or duplicate",
                "duplicate-shard": "missing or duplicate",
                "metadata-failed": "metadata failed",
                "missing-status": "mismatched document",
                "wrong-source": "mismatched document",
                "terminal-error": "batch failed",
                "missing-response": "terminal batch response",
                "text-gap": "overlapping or missing shard text",
                "duplicate-page": "page coverage",
            }
            if case in expected:
                assert expected[case] in str(caught.value)
            if case in {"delete-error", "close-error"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            if case in {
                "timeout",
                "cancel-error",
                "cancel-complete",
                "wrong-operation",
                "ambiguous-submit",
            }:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.completion_unknown == (case != "cancel-complete")
                if case != "ambiguous-submit":
                    assert caught.value.resource_ids["operation"].endswith("owned-job")
                    assert any(call.get("cancel") for call in wire.calls)
                else:
                    assert (
                        len(
                            [
                                call
                                for call in wire.calls
                                if call["url"]
                                .split("?", 1)[0]
                                .endswith(":batchProcess")
                            ]
                        )
                        == 1
                    )
                if case != "cancel-complete":
                    assert not any(call["method"] == "DELETE" for call in wire.calls)
    assert wire.closed == 3
    if case not in {
        "timeout",
        "cancel-error",
        "wrong-operation",
        "ambiguous-submit",
        "delete-error",
    }:
        assert not wire.objects


def test_google_construction_is_offline_and_does_not_import_provider_sdk():
    code = """import socket,sys
from pdfsmith.backends.google_document_ai_backend import GoogleDocumentAIBackend
def denied(*a,**kw):raise RuntimeError('Constructor attempted network')
socket.socket.connect=denied;socket.getaddrinfo=denied
GoogleDocumentAIBackend()
assert 'google.cloud.documentai_v1' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_google_missing_input_precedes_credentials_and_client_creation(tmp_path):
    with (
        patch.object(GoogleDocumentAIBackend, "_create_client") as create,
        pytest.raises(FileNotFoundError),
    ):
        parse(tmp_path / "missing.pdf", backend="google_document_ai")
    create.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"unknown": True},
        {"request_timeout": False},
        {"processor_id": "x/other"},
        {"gcs_bucket": "gs://bucket"},
    ],
)
def test_google_invalid_options_fail_before_provider_work(options):
    with pytest.raises(ValueError):
        GoogleDocumentAIBackend(**options)


@pytest.mark.parametrize("case", ["complete", "blank", "submit-error", "large-upload"])
def test_google_auto_selects_sync_and_batch_by_actual_page_count(case, tmp_path):
    pytest.importorskip("google.cloud.documentai_v1")
    pytest.importorskip("google.cloud.storage")
    pypdf = pytest.importorskip("pypdf")
    import hashlib

    from google.api_core.exceptions import BadRequest

    from tests.google_transport import google_clients

    path = tmp_path / "document.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(16 if case != "blank" else 2):
        writer.add_blank_page(width=300, height=300)
    if case == "large-upload":
        writer.add_metadata({"/TransportPayload": "x" * 9_000_000})
    writer.write(path)
    client, storage, wire = google_clients(case)
    options = {**OPTIONS, "gcs_bucket": "offline-bucket", "poll_interval": 0.001}
    with (
        patch.object(GoogleDocumentAIBackend, "_create_client", return_value=client),
        patch.object(GoogleDocumentAIBackend, "_create_storage", return_value=storage),
    ):
        if case == "submit-error":
            with pytest.raises(BadRequest, match="Controlled submit error"):
                parse(path, backend="google_document_ai", backend_options=options)
            assert not wire.objects
        else:
            text = parse(path, backend="google_document_ai", backend_options=options)
            assert text == (
                "" if case == "blank" else "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
    if case != "blank":
        uploads = [call for call in wire.calls if "input_sha256" in call]
        assert len(uploads) == 1
        assert (
            uploads[0]["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        )
    assert not wire.objects
