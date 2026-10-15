"""Fresh interpreter isolation for native extraction, including direct calls."""

import contextlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def extract_in_process(backend: str, path: Path, options: dict[str, Any]) -> str:
    result = subprocess.run(
        [sys.executable, "-I", "-m", "pdfsmith.backends._process"],
        input=json.dumps(
            {"backend": backend, "path": str(path.absolute()), "options": options}
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"{backend} worker exited with status {result.returncode}")
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError(f"{backend} worker returned an invalid response") from exc
    if "operation_error" in response:
        from pdfsmith.errors import BackendOperationError

        error = response["operation_error"]
        cause = error.pop("cause")
        error["cleanup_errors"] = tuple(error["cleanup_errors"])
        exception = BackendOperationError(**error)
        if cause:
            raise exception from RuntimeError(cause)
        raise exception
    if "error" in response:
        error_types = {
            "ValueError": ValueError,
            "ImportError": ImportError,
            "ModuleNotFoundError": ImportError,
            "FileNotFoundError": FileNotFoundError,
        }
        error = response["error"]
        raise error_types.get(error["type"], RuntimeError)(error["message"])
    text = response.get("text")
    if not isinstance(text, str):
        raise RuntimeError(f"{backend} worker did not return text")
    return text


def _extract_mupdf(backend: str, path: str, options: dict[str, Any]) -> str:
    import pymupdf

    with pymupdf.open(path) as document:
        if document.is_encrypted:
            raise ValueError("Password-protected PDF is unsupported")
        if backend == "pymupdf":
            parts = [page.get_text(sort=options["sort"]).strip() for page in document]
            text = "\n\n".join(part for part in parts if part)
            text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
            while "\n\n\n" in text:
                text = text.replace("\n\n\n", "\n\n")
            return text.strip()
        if backend == "pymupdf4llm":
            import pymupdf4llm

            options = dict(options)
            layout = options.pop("use_layout")
            pymupdf4llm.use_layout(layout)
            pages = pymupdf4llm.to_markdown(
                document,
                page_chunks=True,
                show_progress=False,
                write_images=False,
                embed_images=False,
                **options,
            )
            if not isinstance(pages, list) or len(pages) != len(document):
                raise RuntimeError("PyMuPDF4LLM returned incomplete page coverage")
            parts = []
            for index, page in enumerate(pages, 1):
                metadata = page.get("metadata", {})
                if metadata.get("page", metadata.get("page_number")) != index:
                    raise RuntimeError("PyMuPDF4LLM returned invalid page order")
                if not isinstance(page.get("text"), str):
                    raise RuntimeError("PyMuPDF4LLM omitted page text")
                parts.append(page["text"].strip())
            return "\n\n".join(part for part in parts if part)
    raise ValueError(f"Unsupported process backend: {backend}")


def _extract(backend: str, path: str, options: dict[str, Any]) -> str:
    if backend in {"pymupdf", "pymupdf4llm"}:
        return _extract_mupdf(backend, path, options)
    if backend == "kreuzberg":
        from pdfsmith.backends.kreuzberg_backend import _extract as extract
    elif backend == "extractous":
        from pdfsmith.backends.extractous_backend import _extract as extract
    elif backend == "marker":
        from pdfsmith.backends.marker_backend import _extract as extract
    elif backend == "docling":
        from pdfsmith.backends.docling_backend import _extract as extract
    elif backend == "unstructured":
        from pdfsmith.backends.unstructured_backend import _extract as extract
    else:
        raise ValueError(f"Unsupported process backend: {backend}")
    return extract(Path(path), options)


def _test_network_guard() -> None:
    import os

    if os.environ.get("_PDFSMITH_TEST_OFFLINE") != "1":
        return
    import socket

    ports: set[int] = set()
    socket._pdfsmith_test_local_ports = ports  # type: ignore[attr-defined]
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def permitted(address: Any) -> bool:
        return (
            isinstance(address, tuple)
            and len(address) >= 2
            and address[0] == "127.0.0.1"
            and address[1] in ports
        )

    def guard(original: Any) -> Any:
        def guarded(*args: Any, **kwargs: Any) -> Any:
            if original in (original_connect, original_connect_ex):
                address = args[1]
            elif original == original_getaddrinfo:
                address = (args[0], args[1])
            else:
                address = args[0]
            if not permitted(address):
                raise RuntimeError(
                    "Outbound networking is disabled in PDFsmith test workers"
                )
            return original(*args, **kwargs)

        return guarded

    for name, original in (
        ("connect", original_connect),
        ("connect_ex", original_connect_ex),
    ):
        setattr(socket.socket, name, guard(original))
    socket.create_connection = guard(original_create_connection)
    socket.getaddrinfo = guard(original_getaddrinfo)


def main() -> None:
    _test_network_guard()
    if sys.argv[1:2] == ["--marker-server"]:
        import runpy

        module = sys.argv[2]
        if module not in {"surya.fast_layout.server", "surya.ocr_error.server"}:
            raise ValueError("Unsupported Marker server")
        sys.argv = sys.argv[2:]
        runpy.run_module(module, run_name="__main__")
        return
    request = json.load(sys.stdin)
    response: dict[str, Any]
    try:
        with contextlib.redirect_stdout(sys.stderr):
            text = _extract(request["backend"], request["path"], request["options"])
        response = {"text": text}
    except Exception as exc:
        from pdfsmith.errors import BackendOperationError

        if isinstance(exc, BackendOperationError):
            response = {
                "operation_error": {
                    "message": str(exc),
                    "parse_completed": exc.parse_completed,
                    "recovered_content": exc.recovered_content,
                    "resource_ids": exc.resource_ids,
                    "completion_unknown": exc.completion_unknown,
                    "cleanup_errors": exc.cleanup_errors,
                    "cause": str(exc.__cause__) if exc.__cause__ else None,
                }
            }
        else:
            response = {"error": {"type": type(exc).__name__, "message": str(exc)}}
    json.dump(response, sys.stdout)


if __name__ == "__main__":
    main()
