"""Actual OpenAI SDK upload, completion and cleanup contracts without API calls."""

import hashlib
import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.openai_backend import OpenAIBackend
from pdfsmith.errors import BackendOperationError


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "blank",
        "missing-usage",
        "length",
        "content_filter",
        "tool_calls",
        "refusal",
        "missing-content",
        "missing-choices",
        "extra-choice",
        "generation-error",
        "ambiguous-generation",
        "upload-error",
        "delete-error",
        "delete-unconfirmed",
        "close-error",
        "generation-and-delete-error",
    ],
)
def test_openai_checks_completion_and_cleans_only_terminal_owned_uploads(
    case, multipage_pdf
):
    pytest.importorskip("openai", minversion="3.31")
    pytest.importorskip("pypdf")
    from tests.openai_transport import openai_client

    client, wire = openai_client(case)
    backend = OpenAIBackend(model="future-pdf-model", max_completion_tokens=1234)
    with patch.object(backend, "_create_client", return_value=client):
        if case in {"complete", "blank", "missing-usage"}:
            result = backend.parse(multipage_pdf)
            assert result == (
                "" if case == "blank" else "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
        else:
            with pytest.raises(Exception) as caught:
                backend.parse(multipage_pdf)
            expected = {
                "length": "did not complete",
                "content_filter": "did not complete",
                "tool_calls": "did not complete",
                "refusal": "did not complete",
                "missing-content": "assistant text",
                "missing-choices": "single identified",
                "extra-choice": "single identified",
                "generation-error": "Controlled generation error",
            }
            if case in expected:
                assert expected[case] in str(caught.value)
            if case in {"delete-error", "delete-unconfirmed", "close-error"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            if case in {"ambiguous-generation", "upload-error"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.completion_unknown
            if case == "generation-and-delete-error":
                assert isinstance(caught.value, BackendOperationError)
                assert not caught.value.parse_completed
                assert "Controlled generation error" in str(caught.value.__cause__)
    assert wire.closed
    assert (
        wire.calls[0]["input_sha256"]
        == hashlib.sha256(multipage_pdf.read_bytes()).hexdigest()
    )
    assert (
        len(
            [
                c
                for c in wire.calls
                if c["method"] == "POST" and c["path"] == "/v1/files"
            ]
        )
        == 1
    )
    if case in {"ambiguous-generation", "upload-error"}:
        assert not any(c["method"] == "DELETE" for c in wire.calls)
    else:
        assert wire.calls[-1] == {"method": "DELETE", "path": "/v1/files/file-owned"}
    if case != "upload-error":
        assert wire.calls[1]["model"] == "future-pdf-model"
        assert wire.calls[1]["max_completion_tokens"] == 1234
    if case == "missing-usage":
        assert backend.get_cost_info()["usage"]["tokens"] is None
    assert backend.get_cost_info()["last_parsing_cost"] is None


def test_openai_constructor_does_not_load_sdk_or_credentials():
    code = """import socket,sys
from pdfsmith.backends.openai_backend import OpenAIBackend
def denied(*a,**kw):raise RuntimeError('Constructor attempted network')
socket.socket.connect=denied;socket.getaddrinfo=denied
OpenAIBackend()
assert 'openai' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_openai_missing_input_precedes_credentials_and_client_work(tmp_path):
    with (
        patch.object(OpenAIBackend, "_create_client") as create,
        pytest.raises(FileNotFoundError),
    ):
        parse(tmp_path / "missing.pdf", backend="openai")
    create.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"unknown": True},
        {"model": ""},
        {"max_completion_tokens": False},
        {"request_timeout": 0},
    ],
)
def test_openai_invalid_options_fail_before_upload(options):
    with pytest.raises(ValueError):
        OpenAIBackend(**options)


def test_openai_source_client_factory_does_not_repeat_ambiguous_upload(
    monkeypatch, multipage_pdf
):
    pytest.importorskip("openai", minversion="3.31")
    from tests.openai_transport import openai_client

    monkeypatch.setenv("OPENAI_API_KEY", "offline-key")
    backend = OpenAIBackend()
    client, wire = openai_client("upload-error", create=backend._create_client)
    with (
        patch.object(backend, "_create_client", return_value=client),
        pytest.raises(BackendOperationError),
    ):
        backend.parse(multipage_pdf)
    assert len(wire.calls) == 1
    assert wire.closed


def test_openai_usage_snapshot_clears_before_a_failed_next_call(
    multipage_pdf, tmp_path
):
    pytest.importorskip("openai", minversion="3.31")
    from tests.openai_transport import openai_client

    client, _ = openai_client()
    backend = OpenAIBackend()
    with patch.object(backend, "_create_client", return_value=client):
        backend.parse(multipage_pdf)
    assert backend.get_cost_info()["usage"]["tokens"]["prompt_tokens"] == 13
    with pytest.raises(FileNotFoundError):
        backend.parse(tmp_path / "missing.pdf")
    assert backend.get_cost_info()["usage"] is None


@pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-4o-mini-2024-07-18"])
def test_openai_rejects_model_output_limit_before_upload(model, sample_pdf):
    pytest.importorskip("openai", minversion="3.31")
    pytest.importorskip("pypdf")
    from tests.openai_transport import openai_client

    client, wire = openai_client("complete")
    with (
        patch.object(OpenAIBackend, "_create_client", return_value=client),
        pytest.raises(ValueError, match="16,384"),
    ):
        parse(
            sample_pdf,
            backend="openai",
            backend_options={"model": model, "max_completion_tokens": 32768},
        )
    assert (
        not wire.calls
    ), "Invalid output limit reached the paid upload/generation path"
    client.close()


def test_openai_accepts_its_documented_output_limit(sample_pdf):
    pytest.importorskip("openai", minversion="3.31")
    pytest.importorskip("pypdf")
    from tests.openai_transport import openai_client

    client, wire = openai_client("complete")
    with patch.object(OpenAIBackend, "_create_client", return_value=client):
        result = parse(
            sample_pdf,
            backend="openai",
            backend_options={"max_completion_tokens": 16384},
        )
    assert "FINAL PAGE SENTINEL" in result
    assert wire.calls[1]["max_completion_tokens"] == 16384
