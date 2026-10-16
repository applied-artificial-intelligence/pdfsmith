"""Marker conversion in a fresh worker with owned local inference processes."""

import importlib.metadata
import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pdfsmith._inputs import validate_input
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

AVAILABLE = importlib.util.find_spec("marker") is not None


class MarkerBackend:
    name = "marker"
    options_schema = {
        "disable_ocr": Option(False, bool),
        "paginate_output": Option(False, bool),
        "use_llm": Option(False, bool, (False,)),
        "num_threads": Option(2, int, minimum=1),
        "model_cache_dir": Option(str(Path.home() / ".cache/pdfsmith/marker"), str),
        "llama_cpp_binary": Option("llama-server", str),
    }

    def __init__(self, **options: Any) -> None:
        self._options = normalize_options(self.name, options, self.options_schema)
        for key in ("model_cache_dir", "llama_cpp_binary"):
            if not self._options[key].strip():
                raise ValueError(f"marker.{key} requires a nonempty path")
        self._options["model_cache_dir"] = str(
            Path(self._options["model_cache_dir"]).expanduser().absolute()
        )

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        return extract_in_process(self.name, path, self._options)


class _OwnedProcesses:
    """Subprocess dependency for the two pinned Surya spawn modules only."""

    def __init__(self) -> None:
        self.children: list[subprocess.Popen] = []
        self.content: str | None = None
        self._test_ports: set[int] = set()

    def __getattr__(self, name: str) -> Any:
        return getattr(subprocess, name)

    def Popen(self, *args: Any, **kwargs: Any) -> subprocess.Popen:
        command = args[0] if args else kwargs.get("args")
        if isinstance(command, list) and len(command) > 2:
            if command[1:3] in (
                ["-m", "surya.fast_layout.server"],
                ["-m", "surya.ocr_error.server"],
            ):
                command = [
                    sys.executable,
                    "-I",
                    "-m",
                    "pdfsmith.backends._process",
                    "--marker-server",
                    *command[2:],
                ]
                if args:
                    args = (command, *args[1:])
                else:
                    kwargs["args"] = command
            if "--port" in command:
                port = int(command[command.index("--port") + 1])
                allowed = getattr(socket, "_pdfsmith_test_local_ports", None)
                if allowed is not None:
                    allowed.add(port)
                    self._test_ports.add(port)
        process = subprocess.Popen(*args, **kwargs)
        self.children.append(process)
        return process

    def __enter__(self) -> "_OwnedProcesses":
        return self

    def __exit__(self, kind: Any, primary: Any, traceback: Any) -> None:
        errors = []
        for process in reversed(self.children):
            try:
                if process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=10)
                    except (OSError, subprocess.TimeoutExpired):
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=10)
                else:
                    process.wait()
            except Exception as exc:
                errors.append(f"pid={process.pid}: {type(exc).__name__}: {exc}")
        allowed = getattr(socket, "_pdfsmith_test_local_ports", None)
        if allowed is not None:
            allowed.difference_update(self._test_ports)
        if errors:
            raise BackendOperationError(
                "Marker local server cleanup failed",
                parse_completed=self.content is not None,
                recovered_content=self.content,
                resource_ids={
                    f"server_{i}": str(p.pid) for i, p in enumerate(self.children)
                },
                cleanup_errors=tuple(errors),
            ) from primary


def _completion_guard(generate: Any) -> Any:
    failures: list[Exception] = []

    def guarded(item: Any, *, client: Any, **kwargs: Any) -> Any:
        if failures:
            raise RuntimeError(f"Marker inference failed: {failures[0]}") from failures[
                0
            ]

        def create(**request: Any) -> Any:
            try:
                completion = client.chat.completions.create(**request)
                choices = completion.choices
                if (
                    not isinstance(choices, list)
                    or len(choices) != 1
                    or choices[0].index != 0
                    or choices[0].finish_reason != "stop"
                    or choices[0].message.refusal
                    or not isinstance(choices[0].message.content, str)
                ):
                    raise RuntimeError("Incomplete or refused Marker generation")
                return completion
            except Exception as exc:
                failures.append(exc)
                raise

        proxy = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        result = generate(item, client=proxy, **kwargs)
        # Surya catches request exceptions and drops finish_reason. Raise outside
        # that catch before retry/fallback can accept an incomplete generation.
        if failures:
            raise RuntimeError(f"Marker inference failed: {failures[0]}") from failures[
                0
            ]
        if result.error:
            error = RuntimeError("Marker inference request failed")
            failures.append(error)
            raise error
        return result

    return guarded


def _extract(path: Path, options: dict[str, Any]) -> str:
    from pdfsmith._documents import pdf_page_count

    count = pdf_page_count(path)
    for package, expected in (("marker-pdf", "2.0.0"), ("surya-ocr", "0.22.1")):
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ImportError(
                f"Marker runtime requires {package}=={expected}; "
                "install pdfsmith[marker]"
            ) from exc
        if installed != expected:
            raise ImportError(f"Marker runtime requires {package}=={expected}")
    cache = Path(options["model_cache_dir"])
    cache.mkdir(parents=True, exist_ok=True)
    # Private sentinels prevent reuse or termination of another caller's servers.
    with tempfile.TemporaryDirectory(prefix="pdfsmith-marker-") as home:
        os.environ.setdefault("HF_HOME", str(cache / "huggingface"))
        os.environ.update(
            HOME=home,
            NO_PROXY="127.0.0.1,localhost,::1",
            no_proxy="127.0.0.1,localhost,::1",
            TORCH_DEVICE="cpu",
            MODEL_CACHE_DIR=str(cache / "models"),
            FONT_PATH=str(cache / "font/GoNotoCurrent-Regular.ttf"),
            OMP_NUM_THREADS=str(options["num_threads"]),
            MKL_NUM_THREADS=str(options["num_threads"]),
            OPENBLAS_NUM_THREADS=str(options["num_threads"]),
            SURYA_INFERENCE_BACKEND="llamacpp",
            SURYA_INFERENCE_URL="",
            SURYA_INFERENCE_HOST="127.0.0.1",
            SURYA_INFERENCE_KEEP_ALIVE="true",
            LLAMA_CPP_BINARY=options["llama_cpp_binary"],
            LLAMA_CPP_NGL="0",
            LLAMA_CPP_EXTRA_ARGS="",
            SURYA_INFERENCE_PARALLEL="1",
            FAST_DETECTOR_DEVICE="cpu",
            FAST_LAYOUT_NUM_THREADS=str(options["num_threads"]),
            FAST_LAYOUT_SERVER_URL="",
            FAST_LAYOUT_SERVER_HOST="127.0.0.1",
            OCR_ERROR_SERVER_URL="",
            OCR_ERROR_SERVER_HOST="127.0.0.1",
        )
        from surya.common.batch_service import client as batch_client
        from surya.inference.backends import llamacpp, openai_client
        from surya.settings import settings

        # Override SDK endpoint/port/autostart configuration before any client work.
        # Each service chooses a private free port and runs only on loopback.
        for prefix in ("SURYA_INFERENCE", "FAST_LAYOUT_SERVER", "OCR_ERROR_SERVER"):
            setattr(settings, f"{prefix}_PORT", None)
            setattr(settings, f"{prefix}_AUTOSTART", True)
        threads = options["num_threads"]
        settings.LLAMA_CPP_EXTRA_ARGS = f"--threads {threads} --threads-batch {threads}"
        settings.SURYA_INFERENCE_CTX_SIZE = None
        settings.SURYA_INFERENCE_CTX_PER_SLOT = 12288
        settings.SURYA_GGUF_LOCAL_MODEL_PATH = None
        settings.SURYA_GGUF_LOCAL_MMPROJ_PATH = None
        settings.FAST_LAYOUT_MODEL_CHECKPOINT = "hf://datalab-to/surya_layout2"
        settings.OCR_ERROR_MODEL_CHECKPOINT = "s3://ocr_error_detection/2025_02_18"
        settings.SURYA_MODEL_CHECKPOINT = "datalab-to/surya-ocr-2"
        settings.SURYA_GGUF_REPO = "datalab-to/surya-ocr-2-gguf"
        settings.SURYA_GGUF_MODEL_FILE = "surya-2.gguf"
        settings.SURYA_GGUF_MMPROJ_FILE = "surya-2-mmproj.gguf"

        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from surya.fast_layout import FastLayoutPredictor
        from surya.recognition import RecognitionPredictor

        class CheckedLayout(FastLayoutPredictor):
            def __call__(self, images: Any, **kwargs: Any) -> Any:
                results = super().__call__(images, **kwargs)
                if len(results) != len(images) or any(
                    result.error for result in results
                ):
                    raise RuntimeError("Marker layout inference failed or lost pages")
                return results

        class CheckedRecognition(RecognitionPredictor):
            def __call__(self, images: Any, **kwargs: Any) -> Any:
                results = super().__call__(images=images, **kwargs)
                if len(results) != len(images) or any(
                    block.error for page in results for block in page.blocks
                ):
                    raise RuntimeError("Marker OCR inference failed or lost pages")
                return results

        original_batch = batch_client.subprocess
        original_llama = llamacpp.subprocess
        original_generate = openai_client._generate_one
        with _OwnedProcesses() as owned:
            # Surya stop() does not stop its servers. Capture Popen handles at the
            # two SDK spawn sites, without changing the subprocess module itself.
            batch_client.subprocess = owned
            llamacpp.subprocess = owned
            openai_client._generate_one = _completion_guard(original_generate)
            try:
                models = create_model_dict(inference_backend="llamacpp")
                models["fast_layout_model"] = CheckedLayout(use_order=False)
                models["recognition_model"] = CheckedRecognition(
                    models["inference_manager"]
                )
                converter = PdfConverter(
                    artifact_dict=models,
                    config={
                        "mode": "fast",
                        "disable_ocr": options["disable_ocr"],
                        "paginate_output": options["paginate_output"],
                        "use_llm": False,
                        "extract_images": False,
                        "disable_tqdm": True,
                    },
                )
                result = converter(str(path))
                pages = result.metadata.get("page_stats", [])
                if converter.page_count != count or [
                    page.get("page_id") for page in pages
                ] != list(range(count)):
                    raise RuntimeError("Marker returned incomplete page coverage")
                if not isinstance(result.markdown, str):
                    raise RuntimeError("Marker did not return Markdown text")
                owned.content = result.markdown
            finally:
                batch_client.subprocess = original_batch
                llamacpp.subprocess = original_llama
                openai_client._generate_one = original_generate
        if owned.content is None:
            raise RuntimeError("Marker conversion did not complete")
        return owned.content
