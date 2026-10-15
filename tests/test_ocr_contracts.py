"""Offline OCR request/completion contracts using installed SDK transports."""

import subprocess
import sys
from unittest.mock import patch

import pytest

from pdfsmith import parse
from pdfsmith.backends.registry import BACKEND_REGISTRY
from pdfsmith.errors import BackendOperationError


@pytest.fixture
def colored_pages(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "two-pages.pdf"
    document = canvas.Canvas(str(path), pagesize=(300, 300), invariant=1)
    for color, label in [
        ((1, 0, 0), "FIRST PAGE SENTINEL"),
        ((0, 0, 1), "FINAL PAGE SENTINEL"),
    ]:
        document.setFillColorRGB(*color)
        document.rect(0, 0, 300, 300, stroke=0, fill=1)
        document.setFillColorRGB(0, 0, 0)
        document.drawString(40, 150, label)
        document.showPage()
    document.save()
    return path


@pytest.mark.parametrize(
    "backend,sdk",
    [
        ("aws_textract", "boto3"),
        ("azure_document_intelligence", "azure.ai.documentintelligence"),
    ],
)
def test_ocr_constructor_needs_no_credentials_and_does_not_initialize_sdk(backend, sdk):
    code = (
        "import sys,socket\n"
        "def denied(*a,**kw):raise RuntimeError('No network during construction')\n"
        "socket.socket.connect=denied;socket.getaddrinfo=denied\n"
        "from pdfsmith.backends.registry import BACKEND_REGISTRY;"
        f"BACKEND_REGISTRY[{backend!r}].loader()();"
        f"assert {sdk!r} not in sys.modules, 'SDK initialized during construction'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("backend", ["aws_textract", "azure_document_intelligence"])
def test_ocr_missing_input_is_reported_before_credentials_or_client_work(
    backend, tmp_path
):
    with pytest.raises(FileNotFoundError):
        parse(tmp_path / "missing.pdf", backend=backend)


@pytest.mark.parametrize(
    "backend,options",
    [
        ("aws_textract", {"region": ""}),
        ("aws_textract", {"request_timeout": 0}),
        ("aws_textract", {"unknown": True}),
        ("azure_document_intelligence", {"max_wait": True}),
        ("azure_document_intelligence", {"output_format": "markdown"}),
        ("azure_document_intelligence", {"endpoint": "http://untrusted.invalid"}),
        ("azure_document_intelligence", {"unknown": True}),
    ],
)
def test_ocr_invalid_or_unsupported_options_fail_before_sdk_work(backend, options):
    with pytest.raises(ValueError):
        BACKEND_REGISTRY[backend].loader()(**options)


@pytest.mark.parametrize(
    "case", ["complete", "missing-pages", "missing-text", "late-error", "close-error"]
)
def test_textract_uses_correct_page_images_and_never_publishes_failed_pages(
    case, colored_pages
):
    pytest.importorskip("boto3")
    pytest.importorskip("pymupdf")
    from pdfsmith.backends.aws_textract_backend import AWSTextractBackend
    from tests.ocr_transport import aws_client

    client, transport = aws_client(case)
    with patch.object(AWSTextractBackend, "_create_client", return_value=client):
        if case == "complete":
            result = parse(colored_pages, backend="aws_textract")
            assert result == "FIRST PAGE SENTINEL\n\nFINAL PAGE SENTINEL"
            assert [call["color"] for call in transport.calls] == [
                (255, 0, 0),
                (0, 0, 255),
            ]
        elif case == "close-error":
            with pytest.raises(BackendOperationError) as caught:
                parse(colored_pages, backend="aws_textract")
            assert caught.value.parse_completed
            assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            assert caught.value.resource_ids["page_2_request"]
        else:
            with pytest.raises(ValueError if case == "late-error" else RuntimeError):
                parse(colored_pages, backend="aws_textract")
    assert transport.closed


def test_textract_rejects_oversized_page_geometry_before_client_creation(tmp_path):
    pytest.importorskip("pypdf")
    pytest.importorskip("pymupdf")
    from reportlab.pdfgen import canvas

    from pdfsmith.backends.aws_textract_backend import AWSTextractBackend

    path = tmp_path / "oversized.pdf"
    document = canvas.Canvas(str(path), pagesize=(10000, 10000), invariant=1)
    document.drawString(100, 100, "Oversized rendered page")
    document.save()
    with (
        patch.object(AWSTextractBackend, "_create_client") as create,
        pytest.raises(ValueError, match="pixel"),
    ):
        parse(path, backend="aws_textract")
    create.assert_not_called()


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "running",
        "missing-pages",
        "missing-text",
        "timeout",
        "failed",
        "delete-error",
        "close-error",
        "wrong-location",
    ],
)
def test_azure_requires_complete_pages_and_retains_unknown_operations(
    case, colored_pages
):
    pytest.importorskip("azure.ai.documentintelligence")
    from pdfsmith.backends.azure_document_intelligence_backend import (
        AzureDocumentIntelligenceBackend,
    )
    from tests.ocr_transport import azure_client

    client, transport = azure_client(case)
    options = {
        "endpoint": "https://offline.azure.invalid",
        "poll_interval": 0.001,
        "max_wait": 0.02 if case == "timeout" else 5,
    }
    with patch.object(
        AzureDocumentIntelligenceBackend, "_create_client", return_value=client
    ):
        if case in {"complete", "running"}:
            assert (
                parse(
                    colored_pages,
                    backend="azure_document_intelligence",
                    backend_options=options,
                )
                == "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            )
        else:
            with pytest.raises(RuntimeError) as caught:
                parse(
                    colored_pages,
                    backend="azure_document_intelligence",
                    backend_options=options,
                )
            if case in {"delete-error", "close-error"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.parse_completed
                assert "FINAL PAGE SENTINEL" in caught.value.recovered_content
            if case in {"timeout", "wrong-location"}:
                assert isinstance(caught.value, BackendOperationError)
                assert caught.value.completion_unknown
                assert not any(call["method"] == "DELETE" for call in transport.calls)
    assert transport.closed


def test_textract_keeps_late_page_error_when_client_cleanup_also_fails(colored_pages):
    pytest.importorskip("boto3")
    pytest.importorskip("pymupdf")
    from pdfsmith.backends.aws_textract_backend import AWSTextractBackend
    from tests.ocr_transport import aws_client

    client, transport = aws_client("late-and-close-error")
    with (
        patch.object(AWSTextractBackend, "_create_client", return_value=client),
        pytest.raises(BackendOperationError) as caught,
    ):
        parse(colored_pages, backend="aws_textract")
    assert not caught.value.parse_completed
    assert isinstance(caught.value.__cause__, ValueError)
    assert "second-page" in str(caught.value.__cause__)
    assert transport.closed


@pytest.mark.parametrize("case", ["failed-and-delete-error", "timeout-and-close-error"])
def test_azure_keeps_primary_failure_and_unknown_state_during_cleanup(
    case, colored_pages
):
    pytest.importorskip("azure.ai.documentintelligence")
    from pdfsmith.backends.azure_document_intelligence_backend import (
        AzureDocumentIntelligenceBackend,
    )
    from tests.ocr_transport import azure_client

    client, transport = azure_client(case)
    options = {
        "endpoint": "https://offline.azure.invalid",
        "max_wait": 0.02,
        "poll_interval": 0.001,
    }
    with (
        patch.object(
            AzureDocumentIntelligenceBackend, "_create_client", return_value=client
        ),
        pytest.raises(BackendOperationError) as caught,
    ):
        parse(
            colored_pages,
            backend="azure_document_intelligence",
            backend_options=options,
        )
    assert not caught.value.parse_completed
    assert caught.value.__cause__ is not None
    assert transport.closed
    if case.startswith("timeout"):
        assert caught.value.completion_unknown
        assert not any(call["method"] == "DELETE" for call in transport.calls)
    else:
        assert "failed" in str(caught.value.__cause__)


@pytest.mark.parametrize("backend", ["aws_textract", "azure_document_intelligence"])
def test_ocr_blank_success_requires_complete_page_metadata(backend, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    if backend == "aws_textract":
        pytest.importorskip("boto3")
        pytest.importorskip("pymupdf")
        from tests.ocr_transport import aws_client as factory
    else:
        pytest.importorskip("azure.ai.documentintelligence")
        from tests.ocr_transport import azure_client as factory
    path = tmp_path / "blank.pdf"
    document = pypdf.PdfWriter()
    document.add_blank_page(width=300, height=300)
    document.add_blank_page(width=300, height=300)
    document.write(path)
    client, transport = factory("blank")
    cls = BACKEND_REGISTRY[backend].loader()
    options = (
        {"endpoint": "https://offline.azure.invalid"}
        if backend.startswith("azure")
        else {}
    )
    with patch.object(cls, "_create_client", return_value=client):
        assert parse(path, backend=backend, backend_options=options) == ""
    assert transport.closed


def test_azure_markdown_request_and_confirmed_result_are_consistent(colored_pages):
    pytest.importorskip("azure.ai.documentintelligence")
    from tests.ocr_transport import azure_client

    client, transport = azure_client()
    cls = BACKEND_REGISTRY["azure_document_intelligence"].loader()
    with patch.object(cls, "_create_client", return_value=client):
        result = parse(
            colored_pages,
            backend=cls.name,
            backend_options={
                "endpoint": "https://offline.azure.invalid",
                "model_id": "prebuilt-layout",
                "output_format": "markdown",
            },
        )
    assert result.startswith("# FIRST PAGE SENTINEL")
    assert "outputContentFormat=markdown" in transport.calls[0]["url"]
