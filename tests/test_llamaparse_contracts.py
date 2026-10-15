"""Real LlamaCloud SDK serialization and failure handling on strict offline HTTP."""

import asyncio
import copy
import json

import pytest

from pdfsmith import BackendOperationError, parse, parse_async
from pdfsmith.backends.llamaparse_backend import LlamaParseBackend

OPTIONS = {"tier": "agentic", "version": "2026-09-29", "poll_interval_seconds": 0}


@pytest.fixture
def offline_llama(monkeypatch):
    httpx = pytest.importorskip("httpx")
    sdk = pytest.importorskip("llama_cloud")
    if not hasattr(sdk, "LlamaCloud"):
        pytest.skip("Modern llama-cloud SDK required; legacy is inspected separately")
    state = {
        "pages": [{"page_number": 1, "success": True, "markdown": "# Controlled page"}],
        "status": "COMPLETED",
        "cancel_status": "CANCELLED",
        "cancel_id": "job-controlled",
        "fail": set(),
        "requests": [],
        "clients": [],
        "raw_parameters": None,
        "tier": "agentic",
    }

    def transport(request):
        route = (request.method, request.url.path)
        state["requests"].append(route)
        if route in state["fail"]:
            return httpx.Response(503, json={"detail": "controlled transport failure"})
        if route == ("POST", "/api/v1/beta/files"):
            assert b'name="purpose"' in request.read()
            assert b"%PDF-" in request.read()
            return httpx.Response(
                200,
                json={
                    "id": "file-controlled",
                    "name": "document.pdf",
                    "project_id": "project-controlled",
                },
            )
        if route == ("POST", "/api/v2/parse"):
            state["submitted"] = json.loads(request.read())
            return httpx.Response(
                200,
                json={
                    "id": "job-controlled",
                    "project_id": "project-controlled",
                    "status": "PENDING",
                },
            )
        if route == ("GET", "/api/v2/parse/job-controlled"):
            assert request.url.params.get_list("expand") == ["markdown"]
            result = {
                "job": {
                    "id": "job-controlled",
                    "project_id": "project-controlled",
                    "status": state["status"],
                    "tier": state["tier"],
                },
                "raw_parameters": state["raw_parameters"],
            }
            if state["pages"] is not None:
                result["markdown"] = {"pages": state["pages"]}
            return httpx.Response(200, json=result)
        if route == ("POST", "/api/v2/parse/job-controlled/cancel"):
            return httpx.Response(
                200,
                json={
                    "id": state["cancel_id"],
                    "project_id": "project-controlled",
                    "status": state["cancel_status"],
                },
            )
        if route == ("DELETE", "/api/v2/parse/job-controlled"):
            return httpx.Response(
                200, json={"id": "job-controlled", "project_id": "project-controlled"}
            )
        if route == ("DELETE", "/api/v1/beta/files/file-controlled"):
            return httpx.Response(204)
        raise AssertionError(f"Unexpected endpoint {route}")

    def client(backend):
        http = httpx.Client(transport=httpx.MockTransport(transport))
        state["clients"].append(http)
        return sdk.LlamaCloud(
            api_key="synthetic-offline",
            max_retries=0,
            http_client=http,
            _strict_response_validation=True,
        )

    monkeypatch.setattr(LlamaParseBackend, "_client", client)
    return state


@pytest.mark.parametrize("language", ["en", "de"])
def test_explicit_identity_and_cache_controls_reach_real_sdk(
    sample_pdf, offline_llama, language
):
    backend = LlamaParseBackend(**OPTIONS, language=language)
    assert backend.parse(sample_pdf) == "# Controlled page"
    request = offline_llama["submitted"]
    assert request["tier"] == "agentic" and request["version"] == "2026-09-29"
    assert request["disable_cache"] is True
    assert (
        request["processing_control"]["job_failure_conditions"][
            "allowed_page_failure_ratio"
        ]
        == 0
    )
    assert request["processing_options"]["ocr_parameters"]["languages"] == [language]
    identity = backend.last_result_identity
    assert identity["requested_version"] == "2026-09-29"
    assert identity["confirmed_version"] is None and identity["cache_hit"] is None
    assert identity["confirmed_tier"] == "agentic"
    assert all(client.is_closed for client in offline_llama["clients"])
    assert offline_llama["requests"][-2:] == [
        ("DELETE", "/api/v2/parse/job-controlled"),
        ("DELETE", "/api/v1/beta/files/file-controlled"),
    ]


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED"])
def test_explicit_provider_failure_cannot_become_empty_success(
    sample_pdf, offline_llama, status
):
    offline_llama["status"] = status
    with pytest.raises(BackendOperationError, match=status) as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.parse_completed is False
    assert error.value.completion_unknown is False
    assert isinstance(error.value.__cause__, RuntimeError)


@pytest.mark.parametrize(
    "fault",
    ["failed_page", "missing_expansion", "missing_text", "wrong_tier", "wrong_version"],
)
def test_incomplete_or_different_provider_output_is_rejected(
    sample_pdf, offline_llama, fault
):
    if fault == "failed_page":
        offline_llama["pages"] = [
            {"page_number": 1, "success": False, "error": "controlled page failure"}
        ]
    elif fault == "missing_expansion":
        offline_llama["pages"] = None
    elif fault == "missing_text":
        del offline_llama["pages"][0]["markdown"]
    elif fault == "wrong_tier":
        offline_llama["tier"] = "cost_effective"
    else:
        offline_llama["raw_parameters"] = {"version": "2026-09-28"}
    with pytest.raises(BackendOperationError) as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.parse_completed is False


@pytest.mark.parametrize("numbers", [[1, 1, 3], [3, 2, 1], [1, 3]])
def test_page_coverage_and_order_survive_sdk_deserialization(
    multipage_pdf, offline_llama, numbers
):
    offline_llama["pages"] = [
        {"page_number": n, "success": True, "markdown": f"Page {n}"} for n in numbers
    ]
    with pytest.raises(BackendOperationError, match="page"):
        parse(multipage_pdf, backend="llamaparse", backend_options=OPTIONS)


def test_complete_blank_content_is_distinct_from_failure(empty_pdf, offline_llama):
    offline_llama["pages"][0]["markdown"] = ""
    assert parse(empty_pdf, backend="llamaparse", backend_options=OPTIONS) == ""


def test_cleanup_failure_keeps_completed_content_and_identifiers(
    sample_pdf, offline_llama
):
    offline_llama["fail"].add(("DELETE", "/api/v1/beta/files/file-controlled"))
    with pytest.raises(BackendOperationError, match="cleanup failed") as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.parse_completed is True
    assert error.value.recovered_content == "# Controlled page"
    assert error.value.resource_ids == {
        "job_id": "job-controlled",
        "file_id": "file-controlled",
    }
    assert len(error.value.cleanup_errors) == 1
    assert all(client.is_closed for client in offline_llama["clients"])


def test_parse_error_remains_primary_when_cleanup_also_fails(sample_pdf, offline_llama):
    offline_llama["status"] = "FAILED"
    offline_llama["fail"].add(("DELETE", "/api/v1/beta/files/file-controlled"))
    with pytest.raises(BackendOperationError, match="FAILED") as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.__cause__ is not None and "FAILED" in str(error.value.__cause__)
    assert error.value.cleanup_errors
    assert error.value.recovered_content is None


def test_ambiguous_submission_is_not_retried_and_retains_uploaded_file(
    sample_pdf, offline_llama
):
    route = ("POST", "/api/v2/parse")
    offline_llama["fail"].add(route)
    with pytest.raises(BackendOperationError) as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert offline_llama["requests"].count(route) == 1
    assert not any(method == "DELETE" for method, _ in offline_llama["requests"])
    assert error.value.completion_unknown is True
    assert error.value.resource_ids == {"file_id": "file-controlled"}


@pytest.mark.parametrize(
    "cancel_status, deleted", [("CANCELLED", True), ("RUNNING", False)]
)
def test_poll_failure_cancels_but_keeps_active_job_resources(
    sample_pdf, offline_llama, cancel_status, deleted
):
    offline_llama["fail"].add(("GET", "/api/v2/parse/job-controlled"))
    offline_llama["cancel_status"] = cancel_status
    with pytest.raises(BackendOperationError) as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert ("POST", "/api/v2/parse/job-controlled/cancel") in offline_llama["requests"]
    assert any(method == "DELETE" for method, _ in offline_llama["requests"]) is deleted
    assert error.value.completion_unknown is not deleted


def test_constructor_is_lazy_and_bad_input_fails_before_credentials(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    backend = LlamaParseBackend(**OPTIONS)
    with pytest.raises(FileNotFoundError):
        backend.parse(tmp_path / "missing.pdf")
    wrong = tmp_path / "image.pdf"
    wrong.write_bytes(b"not a PDF")
    with pytest.raises(ValueError, match="PDF header"):
        backend.parse(wrong)


def test_missing_credentials_fail_only_at_valid_parse(sample_pdf, monkeypatch):
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    with pytest.raises(ValueError, match="LLAMA_CLOUD_API_KEY"):
        LlamaParseBackend(**OPTIONS).parse(sample_pdf)


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"parsing_mode": "premium"},
        {"tier": "agentic", "version": "latest"},
        {"tier": "agentic", "version": "2026-01-08"},
        {**OPTIONS, "disable_cache": "maybe"},
    ],
)
def test_legacy_implicit_and_moving_configuration_are_rejected(options):
    with pytest.raises(ValueError):
        LlamaParseBackend(**options)


def test_sync_inside_loop_and_async_convenience_use_same_sdk_contract(
    sample_pdf, offline_llama
):
    async def run():
        assert LlamaParseBackend(**OPTIONS).parse(sample_pdf) == "# Controlled page"
        assert (
            await parse_async(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
            == "# Controlled page"
        )

    asyncio.run(run())


def test_effective_request_identity_is_defensively_copied(sample_pdf, offline_llama):
    backend = LlamaParseBackend(**OPTIONS)
    changed = backend.effective_options
    changed["tier"] = "fast"
    backend.parse(sample_pdf)
    identity = copy.deepcopy(backend.last_result_identity)
    identity["confirmed_tier"] = "wrong"
    assert backend.last_result_identity["confirmed_tier"] == "agentic"


def test_polling_timeout_retains_cause_and_confirms_cancellation(
    sample_pdf, offline_llama
):
    offline_llama["status"] = "RUNNING"
    with pytest.raises(BackendOperationError) as error:
        parse(
            sample_pdf,
            backend="llamaparse",
            backend_options={**OPTIONS, "max_wait_seconds": 0.001},
        )
    assert isinstance(error.value.__cause__, TimeoutError)
    assert error.value.completion_unknown is False
    assert ("POST", "/api/v2/parse/job-controlled/cancel") in offline_llama["requests"]


def test_client_close_failure_preserves_completed_content(
    sample_pdf, offline_llama, monkeypatch
):
    import httpx

    original = httpx.Client.close

    def close_then_fail(client):
        original(client)
        raise OSError("controlled client close failure")

    monkeypatch.setattr(httpx.Client, "close", close_then_fail)
    with pytest.raises(BackendOperationError, match="cleanup failed") as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.parse_completed is True
    assert error.value.recovered_content == "# Controlled page"
    assert error.value.cleanup_errors == ("Client close failed: OSError",)


def test_foreign_cancel_confirmation_does_not_authorize_resource_deletion(
    sample_pdf, offline_llama
):
    offline_llama["fail"].add(("GET", "/api/v2/parse/job-controlled"))
    offline_llama["cancel_id"] = "different-job"
    with pytest.raises(BackendOperationError) as error:
        parse(sample_pdf, backend="llamaparse", backend_options=OPTIONS)
    assert error.value.completion_unknown is True
    assert error.value.cleanup_errors
    assert not any(method == "DELETE" for method, _ in offline_llama["requests"])


def test_structurally_corrupt_pdf_fails_before_credentials(tmp_path, monkeypatch):
    from pypdf.errors import PdfReadError

    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a complete PDF\n")
    with pytest.raises(PdfReadError):
        LlamaParseBackend(**OPTIONS).parse(path)
