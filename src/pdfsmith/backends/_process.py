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

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Outbound networking is disabled in PDFsmith test workers")

    for name in ("connect", "connect_ex"):
        setattr(socket.socket, name, denied)
    socket.create_connection = denied
    socket.getaddrinfo = denied


def main() -> None:
    _test_network_guard()
    request = json.load(sys.stdin)
    response: dict[str, Any]
    try:
        with contextlib.redirect_stdout(sys.stderr):
            text = _extract(request["backend"], request["path"], request["options"])
        response = {"text": text}
    except Exception as exc:
        response = {"error": {"type": type(exc).__name__, "message": str(exc)}}
    json.dump(response, sys.stdout)


if __name__ == "__main__":
    main()
