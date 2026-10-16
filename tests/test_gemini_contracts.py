"""Real GenAI request/candidate/usage/cleanup contracts without provider calls."""

import asyncio
import hashlib
import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.gemini_backend import GeminiBackend
from pdfsmith.errors import BackendOperationError


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "blank",
        "thoughts",
        "missing-usage",
        "zero-usage",
        "MAX_TOKENS",
        "SAFETY",
        "RECITATION",
        "blocked",
        "missing-candidates",
        "missing-content",
        "missing-finish",
        "non-text",
        "thoughts-only",
        "server-error",
        "close-error",
        "async-close-error",
    ],
)
def test_gemini_checks_candidates_and_closes_both_owned_sdk_clients(
    case, multipage_pdf
):
    pytest.importorskip("google.genai", minversion="2.31")
    pytest.importorskip("pypdf")
    from tests.gemini_transport import gemini_client

    client, wire = gemini_client(case)
    backend = GeminiBackend(model="future-pdf-model", max_output_tokens=1234)
    with patch.object(backend, "_create_client", return_value=client):
        if case in {"complete", "blank", "thoughts", "missing-usage", "zero-usage"}:
            result = backend.parse(multipage_pdf)
            assert result == (
                "" if case == "blank" else "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
        else:
            with pytest.raises(RuntimeError) as caught:
                backend.parse(multipage_pdf)
            if case in {"close-error", "async-close-error"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            elif case == "server-error":
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.completion_unknown
            else:
                assert "Gemini" in str(caught.value)
    assert wire.closed and wire.async_closed
    assert len(wire.calls) == 1
    request = wire.calls[0]
    assert (
        request["input_sha256"]
        == hashlib.sha256(multipage_pdf.read_bytes()).hexdigest()
    )
    assert request["path"].endswith("models/future-pdf-model:generateContent")
    assert request["generation_config"]["maxOutputTokens"] == 1234
    assert request["generation_config"]["candidateCount"] == 1
    assert request["generation_config"]["responseModalities"] == ["TEXT"]
    usage = backend.get_cost_info()
    assert usage["last_parsing_cost"] is None
    if case == "missing-usage":
        assert usage["usage"]["tokens"] is None
    if case == "zero-usage":
        assert usage["usage"]["tokens"]["prompt_token_count"] == 0


def test_gemini_constructor_does_not_import_sdk_or_resolve_credentials():
    code = """import socket,sys
from pdfsmith.backends.gemini_backend import GeminiBackend
def denied(*a,**kw):raise RuntimeError('Constructor attempted network')
socket.socket.connect=denied;socket.getaddrinfo=denied
GeminiBackend()
assert 'google.genai' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_gemini_missing_input_precedes_credentials_and_client_work(tmp_path):
    with (
        patch.object(GeminiBackend, "_create_client") as create,
        pytest.raises(FileNotFoundError),
    ):
        parse(tmp_path / "missing.pdf", backend="gemini")
    create.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"unknown": True},
        {"model": ""},
        {"max_output_tokens": False},
        {"request_timeout": 0},
    ],
)
def test_gemini_invalid_options_fail_before_provider_work(options):
    with pytest.raises(ValueError):
        GeminiBackend(**options)


def test_gemini_real_client_factory_does_not_retry_ambiguous_generation(
    monkeypatch, multipage_pdf
):
    pytest.importorskip("google.genai", minversion="2.31")
    from tests.gemini_transport import gemini_client

    monkeypatch.setenv("GOOGLE_API_KEY", "offline-key")
    backend = GeminiBackend()
    client, wire = gemini_client("server-error", create=backend._create_client)
    with (
        patch.object(backend, "_create_client", return_value=client),
        pytest.raises(BackendOperationError),
    ):
        backend.parse(multipage_pdf)
    assert len(wire.calls) == 1
    assert wire.closed and wire.async_closed


def test_gemini_direct_sync_call_in_active_loop_closes_its_async_client(multipage_pdf):
    pytest.importorskip("google.genai", minversion="2.31")
    from tests.gemini_transport import gemini_client

    client, wire = gemini_client()
    backend = GeminiBackend()

    async def run():
        with patch.object(backend, "_create_client", return_value=client):
            assert "FINAL PAGE SENTINEL" in backend.parse(multipage_pdf)

    asyncio.run(run())
    assert wire.closed and wire.async_closed


def test_gemini_usage_does_not_survive_a_failed_next_invocation(
    multipage_pdf, tmp_path
):
    pytest.importorskip("google.genai", minversion="2.31")
    from tests.gemini_transport import gemini_client

    client, _ = gemini_client()
    backend = GeminiBackend()
    with patch.object(backend, "_create_client", return_value=client):
        backend.parse(multipage_pdf)
    assert backend.get_cost_info()["usage"]["tokens"]["prompt_token_count"] == 13
    with pytest.raises(FileNotFoundError):
        backend.parse(tmp_path / "missing.pdf")
    assert backend.get_cost_info()["usage"] is None


def test_gemini_over_limit_page_count_fails_before_client_work(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    path = tmp_path / "too-many-pages.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(1001):
        writer.add_blank_page(width=300, height=300)
    writer.write(path)
    with (
        patch.object(GeminiBackend, "_create_client") as create,
        pytest.raises(ValueError, match="1000 pages"),
    ):
        GeminiBackend().parse(path)
    create.assert_not_called()
