# PDFsmith

PDFsmith provides one Python string API and CLI for PDF extraction through local
libraries and hosted services. Install the extra for the backend you select. The
core package has no mandatory runtime dependencies.

This branch contains the unpublished `0.3.0.dev0` update. The contracts below
refer to this source revision, not the package currently published on PyPI.
Eleven local adapters have actual installed-package parsing evidence. The eight
hosted adapters have offline checks against their real SDKs; they still require
separately authorized live service verification. Execution evidence does not
establish extraction accuracy or comparative quality.

## Installation

From a checkout of this branch, using [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12
uv pip install ".[pypdf,pdfplumber]"
uv run --no-project pdfsmith backends --all
```

Use a non-editable installation of the selected source or wheel when recording
reproducible results. Python 3.10-3.13 was exercised on Linux. Unstructured requires
Python 3.11-3.13. The test evidence does not establish support on other platforms.
An installed extra can still need native software, model assets or credentials.

| Bundle | Contents |
| --- | --- |
| `light` | pypdf, pdfplumber, PyMuPDF |
| `recommended` | pypdf, pdfplumber, PyMuPDF4LLM, Kreuzberg |
| `commercial` | AWS, Azure, Google Document AI, Databricks, LlamaParse |
| `frontier` | Anthropic, OpenAI, Gemini |
| `all` | Local backends except Marker; Unstructured only on supported Python versions |

`recommended` is a historical bundle name, not a measured recommendation.
`all` excludes hosted services and Marker. Marker 2.0's upstream dependencies
conflict with Unstructured and with the current Anthropic/OpenAI SDK extras.
Install `marker` in an environment separate from `unstructured`, `all`,
`anthropic`, `openai` and `frontier`. Exact dependency constraints are in
[pyproject.toml](pyproject.toml); [uv.lock](uv.lock) records the development resolution.

## Python API

```python
from pdfsmith import get_backend, parse, parse_async, registered_backends

text = parse("document.pdf", backend="pypdf",
             backend_options={"extraction_mode": "layout"})
other = parse(pdf_path="document.pdf", backend="pdfplumber")
# Inside an async function:
# text = await parse_async("document.pdf", backend="pypdf")

instance = get_backend("pdfplumber", backend_options={"layout": True})
print(instance.effective_options)

for info in registered_backends():
    print(info.name, info.extra, info.supports_python(), info.is_available())
```

`parse()` and `parse_async()` accept `str` or `Path` input and return `str`.
`input_path=` is an alias for `pdf_path=`; supplying both raises `TypeError`.
All adapters currently accept PDF files only. Missing files, directories,
unsupported extensions and mismatched signatures fail before expensive setup.
Structural corruption can require a parser to detect it.

Each convenience parse call creates a fresh backend. `get_backend(name)` reuses
one locked instance with its configuration frozen at first construction.
Supplying `backend_options`, including `{}`, creates a fresh instance instead.
The same schemas apply to direct
`BACKEND_REGISTRY[name].loader()(**options).parse(path)` calls.

Options are validated before SDK initialization. Unknown keys, invalid types,
nonfinite numbers and unsupported values raise `ValueError`. Boolean strings
accept `true/false`, `1/0`, `yes/no` and `on/off`. `effective_options` returns a
copy of normalized configuration without credentials. The unreleased `preset`
and generic `ocr` parameters are not supported; use the selected adapter's keys.

`parse_async()` moves resolution, setup and extraction off the calling event loop,
using a backend coroutine where present. Cancellation of the caller does not
promise to stop a worker or cancel remote processing. Native MuPDF, model, Rust
and Java extraction runs in fresh child processes; PDFium access is serialized.

Omitting `backend` selects the first dependency-present local backend in
[`DEFAULT_PREFERENCE`](src/pdfsmith/api.py). Selection is fixed, does not evaluate
the document, and never selects a hosted backend. It does not retry another
parser after a selected backend fails.

`available_backends()` reports that local preference set with distribution
metadata present on a supported Python version. `registered_backends()` includes
all 19 names. Neither function imports SDKs, loads models, checks credentials or
proves readiness. `required_env` lists configuration names, not their values.

## Local backends and options

All rows below have actual public-PDF and controlled-input execution evidence.
Output can be plain text or backend-produced Markdown. PDFplumber's wrapper
extracts text; it does not run a separate table-to-Markdown conversion.

| Backend and extra | Constructor options and defaults | Additional requirements |
| --- | --- | --- |
| `pypdf` | `extraction_mode="plain"` (`plain`, `layout`) | None beyond the extra |
| `pdfplumber` | `layout=False`, `x_tolerance=3.0`, `y_tolerance=3.0` | None beyond the extra |
| `pymupdf` | `sort=False` | MuPDF wheel/native support |
| `pymupdf4llm` | `use_layout=False`, `table_strategy="lines_strict"`, `force_text=True`, `ignore_images=False`, `use_ocr=False` | Tesseract assets when OCR is enabled |
| `pdfminer` | `char_margin=2.0`, `line_margin=0.5`, `word_margin=0.1`, `detect_vertical=False`, `all_texts=False` | None beyond the extra |
| `pypdfium2` | None | PDFium wheel/native support |
| `kreuzberg` | `force_ocr=False`, `output_format="plain"` (`plain`, `markdown`) | Tesseract for OCR; cache and LLM augmentation disabled by wrapper |
| `extractous` | None | Supported native/JVM runtime; extraction returns the complete text stream |
| `unstructured` | `strategy="fast"` (`fast`, `hi_res`, `ocr_only`), `include_page_breaks=False` | Python 3.11-3.13, preinstalled loadable `en_core_web_sm==3.8.0`; Poppler/Tesseract and YOLOX assets for applicable modes |
| `docling` | `do_ocr=False`, `do_table_structure=True`, `num_threads=4`, `device="auto"`, `ocr_languages=["en"]`, `table_mode="accurate"`, `artifacts_path=None` | Layout/table models; local Tesseract and language packs for OCR |
| `marker` | `disable_ocr=False`, `paginate_output=False`, `use_llm=False`, `num_threads=2`, `model_cache_dir="~/.cache/pdfsmith/marker"`, `llama_cpp_binary="llama-server"` | Marker 2.0/Surya 0.22.1, llama.cpp server binary and local model assets; separate dependency environment |

With PyMuPDF4LLM, `use_ocr` requires `use_layout=True`; `table_strategy` and
`ignore_images` require `use_layout=False`. The authoritative choice sets and
bounds are the `options_schema` definitions in
[src/pdfsmith/backends](src/pdfsmith/backends). Docling accepts `auto/cpu/cuda/mps`
for device and `fast/accurate` for table mode; CPU was exercised. Marker owns and
closes its local inference servers. Its `use_llm` option accepts only `False`;
local model inference still runs. Unstructured rejects a missing or damaged
spaCy installation before entering the SDK's model repair path.

Model-based libraries may download assets during first use. Preprovision assets
and configure their local paths before running in a restricted environment. The
[local execution evidence](.workspace/work/2026-10-14-pdfsmith-update/milestones)
records tested binaries, model hashes, fixtures and commands. Successful runs do
not imply every model, language, device or OCR mode was exercised.

Only Docling retains automatic option loading, in descending precedence:
explicit options, `PDFSMITH_DOCLING_*`, legacy `DOCLING_*`, project
`.pdfsmith/docling.yaml`, user `~/.config/pdfsmith/docling.yaml`, defaults.
Top-level keys merge; nested values replace. `OCR`, `THREADS` and
`TABLE_STRUCTURE` environment aliases remain supported. YAML requires the
`config` extra when PyYAML is otherwise absent. Other adapters use explicit
constructor options plus their documented provider credential/configuration sources.

## Hosted backends

These adapters have installed real-SDK offline contract evidence on Python
3.10-3.13. Live authentication, permissions and document processing remain
unverified. Selecting one explicitly can send document content to its provider
and incur charges. Installation and discovery do not submit documents.

| Backend | Extra | Configuration and options |
| --- | --- | --- |
| `aws_textract` | `aws` | Standard AWS credential chain; `region="us-east-1"`, `profile=None`, `request_timeout=60.0`. Wrapper renders every PDF page at 150 DPI and calls synchronous text detection per page. |
| `azure_document_intelligence` | `azure` | `AZURE_DOCUMENT_INTELLIGENCE_KEY`; endpoint option or `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`. `model_id="prebuilt-read"` (`prebuilt-read`, `prebuilt-layout`), `output_format="text"` (`text`, `markdown`), `max_wait=180.0`, `poll_interval=1.0`, `request_timeout=60.0`. |
| `google_document_ai` | `google` | Application Default Credentials; `project_id`/`GOOGLE_CLOUD_PROJECT`, `processor_id`/`GOOGLE_DOCUMENT_AI_PROCESSOR_ID`. `location="us"`, `processor_version=None`, `gcs_bucket=None`, `mode="auto"` (`auto`, `sync`, `batch`), `max_wait=600.0`, `poll_interval=1.0`, `request_timeout=60.0`. Batch requires an owned GCS bucket. |
| `databricks` | `databricks` | `host`/`DATABRICKS_HOST`, `warehouse_id`/`DATABRICKS_WAREHOUSE_ID`, PAT or OAuth M2M credentials. `max_wait=180.0`, `poll_interval=1.0`, `request_timeout=60.0`. Uses SQL `ai_parse_document` version 2.0 on binary PDF input. |
| `llamaparse` | `llamaparse` | `LLAMA_CLOUD_API_KEY`; explicit `tier` and pinned `version` required. `disable_cache=True`, `language="en"`, `max_wait_seconds=180.0`, `poll_interval_seconds=1.0`, `request_timeout_seconds=60.0`. |
| `anthropic` | `anthropic` | `ANTHROPIC_API_KEY`; `model="claude-haiku-4-5-20251001"`, `max_tokens=8192`, `request_timeout=180.0`. Inline PDF request. |
| `openai` | `openai` | `OPENAI_API_KEY`; `model="gpt-4o-mini"`, `max_completion_tokens=8192`, `request_timeout=180.0`. File upload and Chat Completions PDF input. |
| `gemini` | `gemini` | `GOOGLE_API_KEY` or `GEMINI_API_KEY`; `model="gemini-2.5-flash"`, `max_output_tokens=8192`, `request_timeout=180.0`. Inline PDF, Gemini Developer API. |

Timeouts are seconds and bound individual requests or job polling as named;
there is no universal wall-clock deadline for credential discovery, multi-page
work and cleanup. Databricks SDK metadata/authentication discovery precedes its
statement deadline. Models and account capabilities can change; an accepted
model string does not establish provider availability.

LlamaParse supports the verified tier/version pairs `fast/2026-06-15`,
`cost_effective/2026-09-28`, `agentic/2026-09-28`, `agentic/2026-09-29` and
`agentic_plus/2026-09-28`. Moving `latest`
aliases and legacy `parsing_mode` are rejected. Requested settings are recorded;
resolved runtime version and cache-hit status remain unknown unless the service
confirms them. The [ParseBench announcement](https://www.llamaindex.ai/blog/parsebench)
is external evaluation work and does not validate this wrapper.

Google selects sync for at most 15 pages and 40 MB; larger inputs use batch with
limits of 500 pages and 1 GB. A processor may impose lower limits. Anthropic's
wrapper permits up to 100 pages and a 32 MB serialized request. OpenAI requires
PDFs smaller than 50 MB. Gemini permits up to 50 MB and 1,000 pages. Databricks
permits up to 10 MB and 500 pages. These are wrapper bounds, not promises that
an account, model or processor will accept every input within them.

Anthropic, OpenAI and Gemini retain `get_cost_info()`, reporting only actual
usage from the last response, with input identity when available. Missing usage and monetary
fields are `None`; PDFsmith does not estimate a bill from file size or old prices.

## Failures and cleanup

A valid blank PDF can return `""`. Provider-declared failure, refusal, output-token
truncation, incomplete page coverage and missing required result fields raise.
The wrapper cannot detect every semantic omission in otherwise complete output.

`FileNotFoundError` identifies missing input, `ValueError` identifies invalid
selection/configuration/input, and `ImportError` identifies missing or broken
prerequisites. Parser and SDK errors can propagate.
[`BackendOperationError`](src/pdfsmith/errors.py) carries operational state:

- `completion_unknown` and `resource_ids` describe ambiguous submissions or jobs
  whose terminal status could not be confirmed. Inspect those resources before
  retrying; the wrapper retains resources still potentially in use.
- `parse_completed`, `recovered_content` and `cleanup_errors` preserve useful text
  when extraction succeeded but cleanup failed.
- `__cause__` retains the primary failure when cleanup also fails.

Submission retries are disabled. Known active jobs receive bounded polling and
best-effort cancellation where the service offers it. Azure's result API has no
cancellation operation; unknown results retain their identifiers. Local handles
are closed, and only known safe owned remote resources are deleted.

## CLI

```bash
pdfsmith parse document.pdf -b pypdf --backend-options '{"extraction_mode":"layout"}'
pdfsmith parse document.pdf -b pdfplumber -o output.txt
pdfsmith backends
pdfsmith backends --all
```

The CLI uses the same API and schemas. stdout contains exactly the returned
UTF-8 bytes, with no extra newline. Diagnostics use stderr. File output stages
in the destination directory and replaces the destination after successful
parsing, encoding and close. Input aliases, including hard links, are rejected.
Failures before replacement preserve the previous destination. stdout and shell
redirection have no atomic file guarantee.

If completed text accompanies a cleanup error, the CLI exits nonzero, preserves
the requested destination and saves a private `pdfsmith-recovery-*.json` beside
that destination, or in the system temporary directory for stdout mode. stderr
reports its path and resource identifiers. Treat recovery files as document data.

## Evidence and development checks

The [specification](.workspace/work/2026-10-14-pdfsmith-update/spec.md),
[review dispositions](.workspace/work/2026-10-14-pdfsmith-update/reviews/dispositions.txt)
and [milestone evidence](.workspace/work/2026-10-14-pdfsmith-update/milestones)
identify reproduced failures, source and wheel hashes, dependency snapshots,
commands, inputs, outputs and verification limits. Public input includes an
[eight-page Premera PDF](https://www.premera.com/documents/045632_2025.pdf);
controlled fixtures cover text, blank, corrupt and scanned inputs as applicable.

```bash
uv sync --locked --extra dev --extra light --extra commercial --extra frontier
uv run --no-sync ruff check src tests
uv run --no-sync ruff format --check src tests
uv run --no-sync mypy src --ignore-missing-imports
uv run --no-sync pytest -q
```

Ordinary pytest strips provider credentials, isolates HOME and denies Python
outbound DNS/TCP. Environment flags cannot opt into live provider tests. Offline
SDK tests use synthetic credentials and controlled transports. Native/model
integration evidence uses separate isolated environments and preprovisioned assets.

[PDF-Bench](https://github.com/applied-artificial-intelligence/pdf-bench) owns
corpus/reference construction and comparative experiments. This library supplies
the parsing interface; it does not certify benchmark results or parser rankings.
Public-main merge, package release, provider spending and website deployment are
separate actions.

## License and contributions

MIT. Report defects through [GitHub issues](https://github.com/applied-artificial-intelligence/pdfsmith/issues)
with the backend, package versions, options and a reproducible input that you can
share. Keep credentials and private documents out of reports.
