"""Public parsing and static backend discovery."""

import asyncio
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends.registry import BACKEND_REGISTRY, BackendInfo

BackendName = str
DEFAULT_PREFERENCE = [
    "docling",
    "marker",
    "pymupdf4llm",
    "kreuzberg",
    "unstructured",
    "pdfplumber",
    "pymupdf",
    "pypdf",
    "pdfminer",
    "pypdfium2",
    "extractous",
]
IMAGE_CAPABLE_BACKENDS: set[str] = set()


def registered_backends() -> list[BackendInfo]:
    """Return all registered metadata without initializing integrations."""
    return list(BACKEND_REGISTRY.values())


def available_backends() -> list[BackendInfo]:
    """Return dependency-present local backends in the released preference order."""
    return [
        BACKEND_REGISTRY[name]
        for name in DEFAULT_PREFERENCE
        if name in BACKEND_REGISTRY
        and BACKEND_REGISTRY[name].supports_python()
        and BACKEND_REGISTRY[name].is_available()
    ]


def _resolve_backend(
    name: str | None = None, *, for_image: bool = False
) -> BackendInfo:
    if name is not None:
        if name not in BACKEND_REGISTRY:
            raise ValueError(
                f"Unknown backend: {name}. Registered: {list(BACKEND_REGISTRY)}"
            )
        info = BACKEND_REGISTRY[name]
        info.require_python()
        if for_image and all(fmt == "pdf" for fmt in info.input_formats):
            raise ValueError(f"Backend '{name}' does not support image inputs")
        if not info.is_available():
            raise ImportError(
                f"Backend '{name}' dependencies are unavailable. "
                f"Install with: pip install pdfsmith[{info.extra}]"
            )
        return info
    for info in available_backends():
        if not for_image or any(fmt != "pdf" for fmt in info.input_formats):
            return info
    raise RuntimeError(
        "No PDF parsing backends are installed for this input. "
        "Install with: pip install pdfsmith[light]"
    )


def get_backend(
    name: str | None = None,
    *,
    backend_options: dict[str, Any] | None = None,
    for_image: bool = False,
) -> Any:
    """Reuse a default instance; explicit options, including {}, create a fresh one."""
    if backend_options is not None and not isinstance(backend_options, dict):
        raise TypeError("backend_options must be a dictionary")
    info = _resolve_backend(name, for_image=for_image)
    try:
        return info.get_instance(backend_options)
    except (ImportError, OSError) as exc:
        raise ImportError(
            f"Backend '{info.name}' dependencies are present but failed to load: {exc}"
        ) from exc


def _prepare(
    pdf_path: str | Path | None,
    input_path: str | Path | None,
    backend: str | None,
    backend_options: dict[str, Any] | None,
) -> tuple[Path, Any]:
    if pdf_path is not None and input_path is not None:
        raise TypeError("Specify pdf_path or input_path, not both")
    selected_path = pdf_path if pdf_path is not None else input_path
    if selected_path is None:
        raise TypeError("A pdf_path is required")
    path = Path(selected_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input must be a regular file: {path}")
    suffix = path.suffix.lower().lstrip(".")
    if backend is not None:
        info = BACKEND_REGISTRY.get(backend)
        if info is not None and suffix not in info.input_formats:
            raise ValueError(f"Backend '{backend}' does not support '{suffix}' inputs")
    formats = (
        BACKEND_REGISTRY[backend].input_formats
        if backend is not None and backend in BACKEND_REGISTRY
        else ("pdf",)
    )
    path = validate_input(path, formats)
    options = {} if backend_options is None else deepcopy(backend_options)
    return path, get_backend(backend, backend_options=options)


def _content(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("Backend must return text, including an explicit empty string")
    return value


def parse(
    pdf_path: str | Path | None = None,
    *,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
    input_path: str | Path | None = None,
) -> str:
    """Parse one document with constructor-bound options and a fresh instance."""
    path, instance = _prepare(pdf_path, input_path, backend, backend_options)
    return _content(instance.parse(path))


def _run_async(
    pdf_path: str | Path | None,
    input_path: str | Path | None,
    backend: str | None,
    backend_options: dict[str, Any] | None,
) -> str:
    path, instance = _prepare(pdf_path, input_path, backend, backend_options)
    if callable(getattr(instance, "parse_async", None)):
        return _content(asyncio.run(instance.parse_async(path)))
    return _content(instance.parse(path))


async def parse_async(
    pdf_path: str | Path | None = None,
    *,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
    input_path: str | Path | None = None,
) -> str:
    """Run resolution, initialization and extraction outside the calling loop."""
    return await asyncio.to_thread(
        _run_async, pdf_path, input_path, backend, deepcopy(backend_options)
    )
