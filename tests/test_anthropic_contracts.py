"""Actual Anthropic SDK request and terminal-response contracts, all offline."""

import hashlib
import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.anthropic_backend import AnthropicBackend
from pdfsmith.errors import BackendOperationError


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "blank",
        "missing-usage",
        "max_tokens",
        "refusal",
        "tool_use",
        "pause_turn",
        "missing-stop",
        "missing-content",
        "wrong-role",
        "close-error",
        "server-error",
    ],
)
def test_anthropic_requires_terminal_text_and_retains_only_reported_usage(
    case, multipage_pdf
):
    pytest.importorskip("anthropic", minversion="1.15")
    pytest.importorskip("pypdf")
    from tests.anthropic_transport import anthropic_client

    client, wire = anthropic_client(case)
    backend = AnthropicBackend(model="future-pdf-model", max_tokens=1234)
    with patch.object(backend, "_create_client", return_value=client):
        if case in {"complete", "blank", "missing-usage"}:
            result = backend.parse(multipage_pdf)
            assert result == (
                "" if case == "blank" else "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
        else:
            with pytest.raises(Exception) as caught:
                backend.parse(multipage_pdf)
            if case == "close-error":
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            elif case != "server-error":
                assert isinstance(caught.value, RuntimeError)
                assert "Anthropic" in str(caught.value)
    assert wire.closed
    assert len(wire.calls) == 1
    assert (
        wire.calls[0]["input_sha256"]
        == hashlib.sha256(multipage_pdf.read_bytes()).hexdigest()
    )
    assert wire.calls[0]["model"] == "future-pdf-model"
    assert wire.calls[0]["max_tokens"] == 1234
    info = backend.get_cost_info()
    assert info["pricing"] is None and info["last_parsing_cost"] is None
    if case != "server-error":
        assert info["usage"]["tokens"] == (
            None
            if case == "missing-usage"
            else {"input_tokens": 13, "output_tokens": 7}
        )


def test_anthropic_constructor_does_not_import_sdk_or_resolve_credentials():
    code = """import socket,sys
from pdfsmith.backends.anthropic_backend import AnthropicBackend
def denied(*a,**kw):raise RuntimeError('Constructor attempted network')
socket.socket.connect=denied;socket.getaddrinfo=denied
AnthropicBackend()
assert 'anthropic' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_anthropic_missing_input_precedes_credentials_and_client_work(tmp_path):
    with (
        patch.object(AnthropicBackend, "_create_client") as create,
        pytest.raises(FileNotFoundError),
    ):
        parse(tmp_path / "missing.pdf", backend="anthropic")
    create.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"unknown": True},
        {"model": ""},
        {"max_tokens": False},
        {"request_timeout": 0},
        {"temperature": 0},
    ],
)
def test_anthropic_unsupported_options_fail_before_provider_work(options):
    with pytest.raises(ValueError):
        AnthropicBackend(**options)


def test_anthropic_usage_does_not_survive_a_failed_next_invocation(
    multipage_pdf, tmp_path
):
    pytest.importorskip("anthropic", minversion="1.15")
    from tests.anthropic_transport import anthropic_client

    client, _ = anthropic_client()
    backend = AnthropicBackend()
    with patch.object(backend, "_create_client", return_value=client):
        backend.parse(multipage_pdf)
    assert backend.get_cost_info()["usage"]["tokens"]["input_tokens"] == 13
    with pytest.raises(FileNotFoundError):
        backend.parse(tmp_path / "missing.pdf")
    assert backend.get_cost_info()["usage"] is None


@pytest.mark.parametrize("case", ["request-bytes", "page-count"])
def test_anthropic_rejects_actual_pdf_limits_before_client_work(case, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    path = tmp_path / "over-limit.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(101 if case == "page-count" else 1):
        writer.add_blank_page(width=300, height=300)
    if case == "request-bytes":
        writer.add_metadata({"/TransportPayload": "x" * 24_000_000})
    writer.write(path)
    with (
        patch.object(AnthropicBackend, "_create_client") as create,
        pytest.raises(ValueError, match="request limit|100 PDF pages"),
    ):
        AnthropicBackend().parse(path)
    create.assert_not_called()


def test_anthropic_real_client_factory_never_retries_ambiguous_submission(
    monkeypatch, multipage_pdf
):
    pytest.importorskip("anthropic", minversion="1.15")
    from tests.anthropic_transport import anthropic_client

    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-key")
    backend = AnthropicBackend()
    client, wire = anthropic_client("server-error", create=backend._create_client)
    with (
        patch.object(backend, "_create_client", return_value=client),
        pytest.raises(BackendOperationError) as caught,
    ):
        backend.parse(multipage_pdf)
    assert caught.value.completion_unknown
    assert len(wire.calls) == 1
    assert wire.closed
