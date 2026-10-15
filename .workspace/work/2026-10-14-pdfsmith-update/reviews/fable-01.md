I'll read the packet first.**Decision: revise before implementation.** The spec's intent is right and the baseline diagnostics are real, but three design points (option binding, the preset/`ocr` layer, and the evidence/discovery model) are contradictory or undefined in a way that every later issue inherits. They are one-paragraph decisions, not rework. Issue 1 (preservation + failing-evidence tests) can start now; the pypdf/pdfplumber milestone (Issue 4) can start once D1–D3 below are decided; nothing else should start before the plan text is corrected.

---

## Findings, by severity

### Blocking all implementation

**B1. Option binding is contradictory across Issues 2–4 and the PDF-Bench path.**
Evidence: Issue 4 says "forward them to producing calls rather than constructors that cannot accept them"; Issue 2 says "Retain no-option `get_backend()` reuse while isolating configured instances"; review-context says PDF-Bench does `BACKEND_REGISTRY[name].loader()` then `cls(**kwargs)` then `backend.parse(path)`. Working `api.py` `get_backend()` does `backend_class(**backend_options)` for every call; released `registry.py` `get_instance()` caches one zero-arg instance.
Failure scenario: if options become `parse()`-call arguments, PDF-Bench's constructor kwargs are rejected or ignored; if they become constructor kwargs, "forward to producing calls" is misread and `layout=True` lands on `PDFPlumberBackend.__init__` again (the TypeError already reproduced in `baseline/working.json` `layout_preset`).
Required change: state one rule: constructors accept the per-backend validated option schema and store it; `parse()` applies stored options to the producing calls; `get_backend(name)` with no options returns the cached instance, with options returns a fresh one; `parse()` never caches configured instances. Obtain PDF-Bench's actual kwargs per backend (missing evidence) before fixing schemas.
Test: `cls = BACKEND_REGISTRY["pdfplumber"].loader(); cls(layout=True).parse(fixture)` must differ from `cls().parse(fixture)` on a two-column fixture; `get_backend("pypdf") is get_backend("pypdf")` and `get_backend("pypdf", backend_options={}) is not get_backend("pypdf", backend_options={"x":...})`.
Affects: Issues 2, 3, 4, 6, 7, 8, 15. Blocks all.

**B2. The cross-backend `preset`/`ocr` layer is unreleased, wrong for 5 of 6 targets, and can trigger paid work.**
Evidence: `api.py` `PRESETS["best"]["marker"] = {"force_ocr": True, "use_llm": True}`; `_build_backend_options` for `unstructured` with `ocr=True` sets `merged["ocr_languages"] = True` (a bool, not a language string); presets send `boxes_flow`/`detect_vertical` to `PDFMinerBackend.__init__(self)`, `strategy`+`infer_table_structure` to a constructor accepting only `strategy`, `force_ocr`+`ocr_languages` to `KreuzbergBackend(force_ocr)`. Invalid preset `typo` and `ocr=True` for pypdf are silently dropped (`PRESETS.get(preset, {})`; `ocr_mappings` miss) — reproduced in `working.json` `invalid_preset`/`unsupported_ocr`. 0.2.0 has no `preset`/`ocr` at all (`public.json`: `TypeError: unexpected keyword 'preset'`).
Failure scenario: once Issue 7 forwards Marker options correctly, `parse(path, preset="best")` on a machine with marker installed enables `use_llm=True`, which in Marker means an external LLM service call — exactly the "accidental provider work" spec 7/10 forbid, reached through a local-looking option.
Required change: decide D2. Either delete `preset`/`ocr` (never released; keep bytes in the snapshot) or replace them with a per-backend alias table that contains only keys present in that backend's schema, with `use_llm` excluded. Spec 9 "unsupported common options fail explicitly" must be stated as: unknown preset → `ValueError`; preset/`ocr` on a backend without a mapping → `ValueError`, not no-op.
Test: `parse(fixture, backend="pypdf", preset="typo")` raises; `parse(fixture, backend="pypdf", ocr=True)` raises; mutation test asserting no backend schema contains `use_llm` reachable from any preset.
Affects: Issues 3, 7, 8, 15. Blocks Issue 3 and everything after.

**B3. Evidence tiers and the "configured" state are not defined, and discovery is specified against itself.**
Evidence: spec Terms row "Available" lists four states; `backend-inventory.json` uses only two `current_evidence` strings; Issue 2 wants "installed SDK-only environments" and "configured/readiness", while spec 8 says listing "cannot … obtain credentials". The inventory lacks the spec-3 columns (input types, options, sync/async, config, system tools).
Required change: define an enum used in every evidence record: `registered → importable (find_spec, no module execution) → constructible (import + constructor, no network) → offline-contract (real SDK, fake transport) → local-e2e → live-e2e`. Define "configured" as a static list of required env-var *names* per backend, never read during discovery. Add the missing inventory columns before Issue 2.
Affects: Issues 2, 16 (claim format for every row). Blocks Issue 2 and the evidence export in all later issues.

### High — blocks the named integration/milestone

**H1. Image routing claims support that no service wrapper implements.**
Evidence: `api.py` `IMAGE_CAPABLE_BACKENDS` lists all 8 services. `anthropic_backend.py` sends `"media_type": "application/pdf"` with `pdf_path.read_bytes()`; `gemini_backend.py` `mime_type="application/pdf"`; `openai_backend.py` uploads any file as `type: "file"`; `azure…` `content_type="application/pdf"`; `aws_textract_backend.py` `fitz.open(stream=pdf_bytes, filetype="pdf")`; `google…` `mime_type="application/pdf"`; `databricks` base64 of whatever bytes. `IMAGE_PREFERENCE` (docling/kreuzberg/extractous) is also unverified: `docling_backend.py` configures `format_options` only for `InputFormat.PDF`, so image conversion uses Docling's defaults, not the configured `do_ocr`/device.
Failure scenario: `parse("scan.png", backend="anthropic")` passes local validation and sends a mislabeled request to a paid endpoint.
Required change: image capability becomes a per-wrapper flag set only where a tested image path exists; reject at validation, before any client/network work. Initially no service claims images.
Test: for each backend, parse a controlled PNG with a transport that fails the test on any outbound request when the wrapper does not declare image support.
Affects: Issue 3 (routing) + Issues 7, 8, 9–14. Blocks each integration's "image" row.

**H2. Partial/failed/truncated output still returns as a string in every inspected service and two local wrappers; the plan misses four of them.**
Evidence (per file): `llamaparse_backend.py` returns `""` when `documents` is empty; the historic `llama_parse` client has defaulted to swallowing job errors and returning an empty list (verify `ignore_errors` on the installed version) — Issue 5 names partial jobs but not this default. `databricks_backend.py` reads `result["elements"]` at top level, returns `""` on an empty `data_array`, returns the raw string on `JSONDecodeError`, and never inspects an error-status field; Issue 11 names "malformed response" but not the result-shape or per-page error fields (verify the official output schema). `gemini_backend.py` `response.text or ""` ignores finish reason and prompt block. `openai_backend.py` ignores `finish_reason`/refusal and sends `max_completion_tokens=100000` regardless of model. `anthropic_backend.py` ignores `stop_reason`. `docling_backend.py` never reads `result.status` (partial-success does not raise under default `convert`) — Issue 7 does not mention it. `extractous_backend.py` uses a default `Extractor()`; verify whether the installed version applies a default maximum string length (silent truncation) — Issue 8 does not mention it. `google_document_ai_backend.py` reads output without `operation.metadata` per-document status and sorts shard names lexicographically (Issue 10 covers both).
Required change: add the four missing checks to Issues 5, 7, 8, 11; every service wrapper must raise on non-terminal/failed/blocked/truncated status; a valid-empty result is returned only when the provider reports completion.
Test: fake transport returning the provider's documented failure/`length`/`SAFETY`/partial shapes must raise; Docling: construct a `ConversionResult` with partial status via the real model class and assert raise.
Affects: Issues 5, 7, 8, 10, 11, 12, 13, 14. Blocks each integration.

**H3. Discovery executes backend modules and has process-global side effects; non-ImportError failures escape.**
Evidence: `registry.py` `is_available()` calls `self.loader()`, which imports the backend module; `docling_backend.py` runs `os.environ.setdefault("OMP_NUM_THREADS", …)` etc. at import; `marker_backend.py` imports `marker.converters.pdf` (torch) at discovery; `is_available()` catches only `ImportError`, so a native-load `OSError` from pypdfium2/extractous aborts `available_backends()` and the CLI `backends` command. `_available` is cached forever.
Required change: dependency detection via `importlib.util.find_spec` on declared import names (as `pypdf_backend.py` already does), no module execution; module import happens at `get_backend`; broad exceptions at that point are reported as "dependency present but broken". Remove import-time env mutation from docling (apply thread limits inside `_get_converter` or document as opt-in).
Test: run `available_backends()` in a subprocess with `OMP_NUM_THREADS` unset and docling installed; assert env unchanged and `sys.modules` contains no `docling`/`torch`; inject a loader raising `OSError` and assert discovery still returns.
Affects: Issue 2. Blocks Issue 2's "done" criterion.

**H4. Environment/file configuration is a silent option source and is partly dead.**
Evidence: `docling_backend.py` docstring documents `DOCLING_OCR=true`; `KNOWN_OPTIONS=["do_ocr", …]` makes `_load_env_config` look up `DOCLING_DO_OCR`. `tests/test_config.py` passes `known_options=["ocr"]`, so the suite tests the loader with a key the backend never uses. Env values stay strings (`DOCLING_DO_OCR=false` → `self._do_ocr="false"`, truthy); `get_bool`/`get_int` exist but are unused. `_find_config_file` reads `./.pdfsmith/<backend>.yaml` relative to the process CWD. `config.py` imports `yaml` unconditionally while `pyproject.toml` has `dependencies = []` and `dev` declares only `types-PyYAML`; the baseline envs were given PyYAML via `baseline/requirements.txt`, which hides it. `config.py` is byte-identical in the 0.2.0 wheel. Three different `num_threads` defaults exist (`"2"` env default, `4` in `BACKEND_DEFAULTS`, `2` in `.get("num_threads", 2)`).
Required change: Issue 3 must specify: one documented env name per option generated from the schema, typed coercion through the schema, CWD config either removed or opt-in via an explicit path/env, and `pyyaml` declared (core or lazily imported only for file config). Issue 7 regression must go through `DoclingBackend` not `load_backend_config`.
Test: `DOCLING_OCR=true` (documented name) → `DoclingBackend()._do_ocr is True`; `DOCLING_DO_OCR=false` → `False` (bool); core-only wheel venv: `python -c "import pdfsmith.config"` must not raise.
Affects: Issues 3, 7, 16. Blocks Issue 3.

**H5. Remote and heavy work happens at construction and on the event loop; sync wrappers break inside a running loop.**
Evidence: `databricks_backend.py` `__init__` calls `self._get_warehouse_id()` → `warehouses.list()` (network) when `DATABRICKS_WAREHOUSE_ID` is unset; `marker_backend.py` `__init__` calls `create_model_dict()` (model download); working `parse_async` calls `get_backend()` (import + constructor) synchronously before `run_in_executor`; `kreuzberg_backend.py` `parse()` uses `asyncio.run`, which raises inside a running loop — PDF-Bench's direct `backend.parse(path)` from a notebook fails; `parse_async` still uses `asyncio.get_event_loop()`.
Required change: Issue 3: constructors do only local validation and client object creation; first network/model work occurs in `parse`/`parse_async`; both import and constructor run in the executor; Issue 11: warehouse must be explicit (no discovery); Issue 8: sync path must work with or without a running loop (run the native coroutine in a dedicated thread/loop) — the plan says "according to the documented contract", which leaves it open; decide it.
Test: loop heartbeat task during `parse_async(backend="databricks")` with a transport that sleeps; assert heartbeat ticks. `asyncio.run(…)` wrapper calling `KreuzbergBackend().parse()` must not raise.
Affects: Issues 3, 7, 8, 11. Blocks those.

**H6. LlamaParse: cache identity and the SDK replacement are under-specified.**
Evidence: Issue 5 promises "observable cache policy" but never ties cache behavior to request identity; `llamaparse_backend.py` never forwards `parsing_mode`, hard-codes `result_type="markdown"`, `language` at top level, and the extra is `llama-parse>=0.6` (unbounded).
Risk: a repeat run with a changed tier/version served from a service-side cache keyed by file hash would silently invalidate a PDF-Bench comparison; "latest" service version drifts between runs.
Required change before any code: record on the installed SDK (a) distribution and module version, (b) what `llama_parse.LlamaParse` resolves to (own implementation vs. shim), (c) whether tier/version/processing/output options and cache-bypass flags are reachable through it, (d) its error-swallowing default, (e) page-index base. Replace the SDK path only if (c) fails. Then: pin an explicit service version (never "latest"), expose cache-bypass as a first-class option and record it in the evidence record, reject legacy `parsing_mode` names with a message listing current tier names rather than mapping them (mapping implies cost equivalence the packet already says cannot be assumed). Output/completion: treat per-page error entries and non-success job status as failures (H2).
Test: transport capture asserts tier, version, cache flag and language are present in the request body exactly; mutation dropping any one fails; a job status of failed/partial with the SDK's default settings must raise, not return `""`.
Affects: Issue 5 only.

### Medium

**M1. Databricks request path is unverified on three counts** (`databricks_backend.py`): the `ai_parse_document('<base64>', 'base64')` call form, the size of a SQL statement embedding a multi-MB base64 literal, and `wait_timeout="30s"` with the pending state treated as "Unknown error" while the statement keeps running and is never cancelled. Required: official-doc check of the function signature and documented input pattern (volume/`READ_FILES` vs. literal), `get_statement` polling with a bound, `cancel_execution` on give-up, and honest reporting that cancellation is best-effort. Test: transport returning PENDING then SUCCEEDED; PENDING past the bound must issue a cancel request. Issue 11.

**M2. Cleanup and partial billing in OCR services.** `aws_textract_backend.py`: pages are billed one by one and `pdf_doc.close()` is skipped on exception (no `finally`); `google_document_ai_backend.py`: `operation.result(timeout=600)` raises without cancelling; `_cleanup_gcs` downgrades failure to a log line, which does not satisfy spec 14 "reported honestly"; `_get_page_count` returns `None` when PyMuPDF (undeclared in the `google` extra) is absent, so a 100-page/<20 MB file goes to the sync API and surfaces as "Invalid PDF". Required: `finally` for native handles; decide D6 for post-success cleanup failures; declare pymupdf in `google`, or make page counting a hard requirement. Issues 9, 10.

**M3. CLI contract gaps beyond Issue 15's list.** `cli.py`: `print(f"Written to {args.output}")` goes to stdout; stdout output gets a trailing newline that `-o` output lacks (two different "outputs" for one parse); `write_text` truncates before any failure; `--version` prints the module string (0.3.0) while the distribution says 0.2.0. Required: define byte identity between stdout and `-o` (one trailing newline, UTF-8 via `sys.stdout.buffer`), diagnostics to stderr, staged temp in the target directory + `os.replace`, alias check via resolved path/`samefile` (output may not yet exist — compare resolved parent+name too), and document that stdout cannot be atomic and that an interrupted provider job may keep running. Issues 15, 16.

**M4. Local handle hygiene and API currency.** `pypdfium2_backend.py` closes nothing (document/page/textpage) and relies on `get_text_range`, whose status on the installed 5.x should be checked; `pypdf_backend.py` never closes `PdfReader`; `pymupdf_backend.py` tests `is_encrypted` — verify against `needs_pass` semantics on an owner-password-only fixture. Issue 6. Test: open-handle count before/after a corrupt-input failure.

**M5. Issue 1 expected failures must be `xfail(strict=True)`**, otherwise a repair that lands as a side effect of another issue XPASSes silently and the marker is never removed. Issue 1.

**M6. Cost accounting.** `get_cost_info()` in the three frontier backends multiplies response tokens by hard-coded March-2026 price tables and estimates pages by `size // 75000`. Keep provider-reported token counts; drop USD figures or label them as a dated table that is not a bill. Issues 12–14.

**M7. Extras.** `all` omits `marker-pdf` and all services; `commercial` omits the frontier three; `pymupdf4llm` hint says `pdfsmith[light]`, which does not install it; `api.py` hints `pdfsmith[aws_textract]`/`[azure_document_intelligence]`/`[google_document_ai]`, none of which exist; `unstructured` extra's `pikepdf` claim is unverified; classifiers advertise 3.10–3.13 with evidence only on 3.12.11. Issue 16 covers bundle resolution; add the hint table to Issue 2 and at least one 3.10 and 3.13 core+baseline run or narrow the bounds.

### Low

- `registry.py` `BackendInfo` carries mutable `_instance`/`_available` as dataclass fields (participates in `__eq__`), and `get_instance` is not thread-safe.
- `api.py` duplicates backend resolution in `parse`, `parse_async` and `get_backend`, with a `backend_name or "docling"` fallback; Issue 3 "resolve once" fixes this — make it explicit that `parse()` must call the same resolver `get_backend()` exposes, so the "selected name" surface and the actual choice cannot diverge.
- `google…_raise_api_error` classifies by substring of the exception message.

---

## Unresolved author decisions

| # | Decision | Alternatives → consequences |
|---|---|---|
| D1 | Option binding (B1) | Constructor-bound + cached no-option instance: PDF-Bench path works, singleton test passes, schemas live on constructors. Call-bound: breaks PDF-Bench's `cls(**kwargs)` unless a shim is added — more code. |
| D2 | Keep `preset`/`ocr` (B2) | Drop: smallest surface, no cross-backend quality tiers (consistent with "no quality ranking"), nothing released breaks. Keep as per-backend alias tables: more schema work, must exclude `use_llm`, must define "unsupported → error". |
| D3 | First parameter name | Restore `pdf_path` (positional-or-keyword, as released): keyword baseline passes, `input_path` was never public. Accept both names: awkward signature forever. |
| D4 | Image support declarations (H1) | Services declare none until a tested path exists; local three only after a PNG run. Alternative "declare and verify later" leaves H1 open. |
| D5 | Running-loop contract for sync wrappers (H5) | Dedicated thread/loop per call: works everywhere, slight overhead. "Documented limitation": PDF-Bench-from-notebook breaks. |
| D6 | Cleanup failure after a successful parse (M2) | `warnings.warn` + structured attribute (`last_cleanup_errors`): content preserved, caller can inspect. Raise: honest but discards paid output. Log only: fails spec 14. |
| D7 | LlamaParse SDK path and legacy `parsing_mode` (H6) | Decide after the installed-SDK check; reject legacy names vs map — mapping asserts cost/quality equivalence the packet disclaims. |
| D8 | Version source | Hatch dynamic from module vs static pyproject with a test asserting equality. Either; pick one. |
| D9 | Default preference order | Keep legacy order (docling first when installed): preserves compatibility; default on a docling machine loads models. Light-first: changes released default behavior. Plan says keep — confirm. |

---

## Missing evidence and unsupported claims

Missing evidence (needed before the related issue closes):
- PDF-Bench's actual adapter code and the kwargs it passes per backend (only described in prose). Needed for D1/B1.
- The 0.2.0 wheel differs from public main in 16 of 25 module bytes (`api.py`, `registry.py`, `cli.py`, every backend except aws/azure/databricks/docling/google/config); `summary.json` asserts AST equality only for api/registry. The released CLI and backend constructor contracts are therefore inferred from public main. Add a wheel-vs-main AST/diff statement for all modules in Issue 1.
- Zero tests of any kind exist for the inherited `anthropic_backend.py`, `openai_backend.py`, `gemini_backend.py`; `test_commercial_backends.py` patches SDK classes, not transports; `tests/integration/*` is skip-only.
- Installed-SDK facts: llama-parse version/import graph, kreuzberg `ExtractionConfig` signature on the resolved major, extractous return type and default length limit, azure `begin_analyze_document` body/content-type form, Databricks `ai_parse_document` input/output schema, google-genai custom-transport support, pypdfium2 text API.
- Baseline environments installed `baseline/requirements.txt` (PyYAML, reportlab, pytest, cryptography) on top of the package, so no evidence yet exists for spec 17's "declared extras only" or for Python 3.10/3.11/3.13.
- README correction branch `cb5094e…` content is not in the packet; Issue 16 reconciliation cannot be reviewed.

Unsupported claims inside the packet (candidates for repair, not facts): every docstring limit and price (AWS "3,000 pages synchronous", Azure 500 MB, Anthropic 32 MB/100 pages, Gemini 50 MB/1000 pages, OpenAI `max_completion_tokens=100000`, Gemini `max_output_tokens=65536` for all models), all model-ID lists, "best quality"/"highest quality" descriptions in the registry, `IMAGE_CAPABLE_BACKENDS`, the `pikepdf` requirement note, and the `test_consistency_across_providers` premise that providers should agree.

Optional future work (not prerequisites): LiteParse, structured/bbox outputs, timing, any corpus or quality comparison (PDF-Bench's), running the three suites on 3.13.

---

## Simplifications (Q8) that keep all-backend scope, honest evidence and preservation

1. **Collapse the Premises/Claims boilerplate.** The `ordering-spacing`, `known-at`, `institution`, `entity-identity` rows are identical in all 16 issues; keep one shared section and one claim per issue. The plan shrinks by roughly half with no loss.
2. **Merge Issues 2+3** (one touch of `api.py`/`registry.py`, one resolver) and **merge 12–14** into one "LLM document backends" issue with a shared real-SDK transport harness and three rows; 9+10 keep separate rows but share the OCR harness. ~11 issues instead of 16.
3. **Adopt D2 = drop** `preset`/`ocr`. Keep `backend` + `backend_options` with per-backend schemas. Removes `_build_backend_options`, the preset tables, the `ocr_mappings` table, the CLI preset flags, and B2.
4. **Discovery = `find_spec`, readiness = import at `get_backend`.** Then `registered_backends()` (all 19, with `kind`, `extra`, `requires_env` names, `dependency_present`) plus unchanged `available_backends()` is sufficient; drop the `include_services` keyword idea.
5. **One evidence record schema** (tier enum from B3, package/backend versions, input/output hashes, command) emitted by a generalized `baseline_probe.py` per backend, instead of three new test files. Put provider contracts under `tests/providers/test_<name>.py` so each extra runs in isolation with `-k` unnecessary.
6. **Move the website-editorial handoff out of Issue 16** into a non-engineering deliverable; Issue 16 then has one job: wheel identity and per-extra installed checks.
7. **LlamaParse: no dual v1/v2 path.** Decide after the installed-SDK check; migrate in place under the same name.

---

## Question-by-question mapping

1. All 19 named, but tiers conflated (B3); 17 rows have source-only evidence, stated honestly.
2. No coherent plan yet (B1, D1, D3); fixable in one paragraph.
3. Not precise enough (B2, H3, H4, H5).
4. Covers tier/version/legacy mode but not cache identity, SDK-shim check order, or error-swallowing default (H6).
5. Masquerade paths remain in eight wrappers; plan misses four (H2). Real-SDK + fake transport is adequate offline evidence for serialization, polling and cleanup ordering only; it cannot verify server limits, model IDs, tier semantics or cache behavior, and hand-written "official response shapes" are themselves unverified fixtures — record the doc URL/date per fixture and keep the live tier separate.
6. Achievable for `-o` (temp + replace + alias check); stdout cannot be atomic; remote cancellation is best-effort only (M1, M3).
7. Failing tests are reachable if routed through `parse()`/real backends rather than `load_backend_config` (H4, M5); installed-wheel checks must use empty venvs with one extra each and assert imported third-party modules ⊆ the extra's dependency closure, and that `importlib.metadata.version`, `__version__` and `pdfsmith --version` agree.
8. Yes, unnecessarily complex; simplifications above.
