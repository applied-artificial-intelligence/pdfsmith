# Plan: PDFsmith library update and complete backend verification

This plan decomposes the reviewed spec.md after Stefan selected every registered
backend. GPT and Claude reports are retained under reviews/; dispositions resolve
shared design blockers. Implementation is authorized. Integration-specific SDK facts
and runtime regressions remain required before each affected milestone closes.
The original review packet and baseline remain immutable historical evidence.

## Execution evidence

Core/API/CLI work and all 11 local adapters have installed execution evidence.
All eight hosted adapters have actual SDK offline contract checks across Python
3.10-3.13; they remain open for live service verification. The detailed current
matrix is backend-inventory.json and commands/results are under milestones/.
A resolved review finding is not a live integration claim.

Issue 16 additionally tests all six documented installation choices in fresh
non-editable environments, reconciles README against the preserved October 9
capability branch, tests installed module/distribution/console/archive identity,
and reproduces the Python 3.10 locked ONNX Runtime wheel failure. CI uses the
locked supported resolution and contains no release/publish job. Ruff is pinned
to the existing hook version so source, local checks and CI agree.

live-run-protocol.txt defines proposed documents, routes, settings, bounded
submissions, cleanup evidence and the separate authorization information needed.
It does not authorize provider spending. Batch Google, other models/modes and
additional live failure experiments require their own named scope.

## Reconciled design, October 15, 2026

Both returned reviews recommended revision before implementation. Their shared
planning blockers are resolved by spec.md's Reviewed contract and the complete
finding dispositions in reviews/dispositions.txt. Provider-specific claims still
require their own producing-code tests; no live service has been validated.

Use constructor-bound schemas and lazy expensive initialization on every direct
and convenience path. The constructors are authoritative for options; registry
metadata describes dependencies/input/execution only and does not duplicate those
schemas. Convenience parsing creates fresh configurations; no-option get_backend
preserves locked reuse and freezes configuration. Preserve pdf_path= and accept
input_path= with a conflict error. Drop unreleased preset/ocr instead of retaining
invalid aliases or a Marker alias that activates paid LLM work.

Static discovery never imports wrappers/SDKs. Expose registered_backends() with
names, extras, dependencies, execution policy, required environment variable names
and tested formats; keep available_backends()'s released local ordering. No
include_services switch or claim that find_spec proves importability is needed.
The backend inventory records evidence as independent observations with precise
scope, not an assumed progression from registration to operational readiness.

Apply the exact typed configuration precedence, copying and alias rules in the
specification. Preserve released Docling layering while making YAML optional and
lazy; do not centralize an undeclared PyYAML import into the core API. All wrappers
begin PDF-only until their own image route is tested. PyMuPDF work is process-
isolated; PDFium uses shared runtime synchronization, including indirect paths.
Async convenience calls move blocking resolution/setup off the event loop.

Each provider issue defines terminal-success and blank-output predicates, required
fields/page coverage, request identity, cleanup/uncertain-submission behavior and
strict real-SDK transport fixtures. After successful extraction, cleanup failure
raises an operational exception retaining content and resource identifiers. The
CLI saves completed content as a separate private recovery JSON, reports the path
and keeps a nonzero exit and prior destination. Unknown
remote completion forbids destructive cleanup of active-job resources or blind
resubmission. SDK request serialization is not live SQL/service validation.

LlamaParse's installed legacy SDK inspection precedes any replacement. One modern
path, explicit pinned version/tier, disable_cache=true by default, rejected legacy
parsing_mode and provider-confirmed identity are specified. The exact accepted
published versions were selected from current official documentation and SDK
inspection in Issue 5: llama-cloud 2.18.x, 2026-06-15/2026-09-28/2026-09-29,
with per-tier pairing verified against the service versions endpoint in milestone
17 (Fast supports 2026-06-15). Runtime-version confirmation and
cache-hit status remain unknown; provider parameter echoes are separate.

Keep existing issue IDs for traceability. Execute Issue 1 (test safety plus early
version/core wheel), Issues 2-3, Issue 4, then Issue 15. Independent backend issues
5-14 follow stable shared contracts. First local milestones do not wait for paid
service authorization or another integration's unresolved runtime problem.

## Verification and evidence

Each issue first reproduces its user-visible error, then adds a regression that
fails with the producing defect and passes after repair. Tests named below are
planned additions to the indicated existing files or explicitly proposed new
files; they are not claimed to exist or pass today. New proposed files are
 tests/test_contracts.py, tests/verify_distribution.py and
 tests/test_provider_contracts.py. Exact selection names will be set with the tests.
Run focused pytest, Ruff and repository type checks before each scoped commit.
Install pre-commit before committing. Ordinary tests are network-denied and live
tests are excluded regardless of inherited environment flags. The fixture/test
runner environment is separate from each clean installed-wheel environment. Test environments may use python -m pytest
when proving the behavior of a specific installed wheel rather than the checkout.

The local verification matrix must cover all 11 local integrations on a public PDF
and controlled fixtures. Each SDK/service matrix covers all eight service names
and separates offline contracts from authorized live execution. Unsupported Python,
platform, system-tool or model combinations get a reproduced limitation, not a
silent skip counted as success. Test per-extra resolution before advertising a
bundle. A local milestone can close while another integration remains visibly open.

Each closed issue exports source/package/backend identities, exact commands and
fresh results, input/output hashes and limitations to this work unit. Raw parsing
outputs are capability evidence, not benchmark quality scores. No timing ranking
or resource-performance claim is planned.

## Preservation and dependencies

Initial identity/hashes are in baseline/inherited-state.json. Only explicitly
owned paths are staged. Preserve inherited API/module/provider/lockfile bytes in
the review snapshot before integrating them issue by issue. Authorship of these
uncommitted changes is unknown. Secret-bearing prompts, .env, MCP configuration and
credential values are excluded. Add appropriate ignores without removing files.

Public main remains fe66170231dd580d9f919662ed3b89947f091763. The independent
README branch cb5094e6b2690b50da748bcea4875adaa8c74dfc must be fetched and compared
before README editing; reuse its corrections without deleting its branch until
its work actually lands. Public branch pushes are permitted. Merge to main,
package release, service spend and deployment remain separately unauthorized.

### Milestone: `0.3.0.dev0 - Reviewed parser contracts and backend verification`

**Issue 1 - Preserve inherited work and establish failing compatibility evidence**

Review reconciliation is complete; this is the first engineering checkpoint.

Files: tests/conftest.py, tests/test_safety.py, tests/test_api.py, pyproject.toml, src/pdfsmith/__init__.py and work-unit evidence.

Resolve test safety before broad collection: deny outbound connections, isolate HOME
and inherited credentials, and exclude live tests independently of environment
flags. Reproduce the old RUN_COMMERCIAL_TESTS=0/false/1 behavior with synthetic
clients and an execution tripwire, then verify zero live-test execution. Move
0.3.0.dev0 single-source identity, wheel/module/CLI equality and core-only imports
here. Compare ASTs for every release/public module, not only api/registry. Preserve
the original baseline and report bytes. Reason-specific xfails must be strict.

Verify: Run the actual integration-test entry point with a synthetic SDK tripwire for absent/0/false/1 flags before and after the guard. Run safety/version tests and the clean core-wheel probe; expected old compatibility failures are strict and named.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: inherited-source

| Question | Answer | Kind |
|---|---|---|
| record | One allowlisted file revision with bytes and SHA-256; no credential content. | definitional |
| absent-record | A missing historical author remains unknown and does not license deletion. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Git revision plus relative path and byte hash identify a file; timestamps are not authorship. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| preserved-source | Inherited source and new changes remain distinguishable. | A new commit absorbs an unrelated modification or a snapshot omits inherited bytes. |

Closes: inherited-source.record, inherited-source.absent-record, inherited-source.ordering-spacing, inherited-source.entity-identity, inherited-source.known-at, inherited-source.institution, preserved-source

**Issue 2 - Repair registry discovery and deterministic backend selection**

Depends on Issue 1.

Files: src/pdfsmith/backends/registry.py, src/pdfsmith/api.py, src/pdfsmith/__init__.py and tests/test_api.py.

Use metadata/top-level find_spec only, without wrapper imports or environment
mutation. registered_backends() lists all entries; available_backends() preserves
legacy local ordering. Do not add include_services. Lock singleton creation; never
cache a failed initialization. Record static required variable names, not values.
Fix extra aliases and neutralize unsupported quality descriptions. A fresh-process
discovery test detects imported wrappers, torch/docling and environment changes.

Verify: Run tests/test_api.py and discovery subprocess tests; verify all 19 entries and zero backend imports/env mutations plus thread-safe singleton retry.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: registry-installation

| Question | Answer | Kind |
|---|---|---|
| record | One registered backend and its declared dependencies, not a successful parse. | definitional |
| absent-record | Missing SDK means dependency-unavailable; absent credentials are a distinct state. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | A backend name is stable; an install extra and SDK distribution name may differ. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| honest-discovery | Discovery and selection distinguish membership, dependencies and initialization. | Listing a backend initializes a client, omits a registered name or routes a paid default. |

Closes: registry-installation.record, registry-installation.absent-record, registry-installation.ordering-spacing, registry-installation.entity-identity, registry-installation.known-at, registry-installation.institution, honest-discovery

**Issue 3 - Unify API validation, option precedence and async behavior**

Depends on Issue 2.

Files: src/pdfsmith/api.py, src/pdfsmith/config.py, shared backend validation/execution helpers, tests/test_contracts.py, tests/test_async.py and tests/test_config.py.

Bind options in constructors, apply stored options in producing calls, and
make constructors validate-only. Keep pdf_path and inherited input_path alias;
reject both together. Remove unreleased preset/ocr and all generic quality aliases.
Use exact typed configuration/copying/alias precedence from spec.md. Core/config
import stays dependency-free; YAML import is lazy and its extra declared. API and
direct paths share schemas. Native-runtime execution follows spec.md's process/
serialization policy; generic concurrent executor access is not a safety policy.

Verify: Run tests/test_contracts.py, tests/test_async.py and tests/test_config.py. Reproduce keyword, option-source and heartbeat defects first; exercise the same direct constructors and API calls after repair.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: parse-request

| Question | Answer | Kind |
|---|---|---|
| record | One input path, selected backend and effective configuration for one call. | definitional |
| absent-record | Unspecified options mean declared defaults; a missing path is an error. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input identity is bytes; the backend name and effective options identify invocation behavior. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| validated-api | Sync/async share validated semantics and preserve released call forms. | A typo is ignored, setup blocks the loop or options leak into another operation. |

Closes: parse-request.record, parse-request.absent-record, parse-request.ordering-spacing, parse-request.entity-identity, parse-request.known-at, parse-request.institution, validated-api

**Issue 4 - Verify configurable pypdf and pdfplumber through installed packages**

Depends on Issue 3.

Files: pypdf_backend.py, pdfplumber_backend.py, tests/test_backends.py and tests/verify_distribution.py.

Constructors accept validated options and forward them to extract_text/tables
at parse time. Test actual two-column/layout effects through both API and direct
constructor calls. Cover API/async options and default CLI only here; CLI option
parity belongs to Issue 15. No tests of removed presets are required beyond their
explicit rejection. Use clean extra-only wheel targets without PyYAML/test helpers.

Verify: Run actual installed-wheel API/async/default CLI probes on the retained Premera PDF and controlled text/table/layout/blank/corrupt inputs. Require different output for a layout-affecting constructor option. Keep fixture generation outside wheel targets.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: baseline-document

| Question | Answer | Kind |
|---|---|---|
| record | One PDF rendition and its actual parser output, not extraction ground truth. | definitional |
| absent-record | Blank output is a recorded empty result; exception means no completed output. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Identify PDFs and returned UTF-8 bytes by hashes, not document names or output lengths. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| local-baselines | Both baseline extras parse documents and apply supported options. | Only imports or mocks run, or the output-affecting option never reaches extraction. |

Closes: baseline-document.record, baseline-document.absent-record, baseline-document.ordering-spacing, baseline-document.entity-identity, baseline-document.known-at, baseline-document.institution, local-baselines

**Issue 5 - Migrate and verify the LlamaParse SDK contract**

Depends on Issue 3.

Files: llamaparse_backend.py, its extra/lock and tests/providers/test_llamaparse.py.

Inspect the actual installed legacy SDK before deciding replacement: distribution,
re-export, fields/unknown-field handling, serialization/endpoints/defaults,
ignore_errors, index base, retries/polling and cache controls. Replacement is
conditional on missing supported controls. Require explicit tier plus a published
pinned version, reject legacy parsing_mode, disable_cache=true by default and
separate requested/provider-confirmed identities. Validate complete job/page
coverage, failed pages, duplicate/order/missing expansion and tier/version output
compatibility. Do not map premium or invent historical effective defaults.

Verify: Run only tests/providers/test_llamaparse.py in its isolated SDK environment; capture real serialized requests and typed failure/page responses. No live call.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: llamaparse-job

| Question | Answer | Kind |
|---|---|---|
| record | One upload/parse job with SDK version, effective tier, service version and outputs. | definitional |
| absent-record | Missing results, unfinished jobs and failed pages cannot imply completed content. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Job ID, input hash, request settings and pinned service version identify the operation. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| llamaparse-contract | LlamaParse sends the requested configuration and interprets terminal results. | The mode is stored but not sent, latest changes silently or partial output is called complete. |

Closes: llamaparse-job.record, llamaparse-job.absent-record, llamaparse-job.ordering-spacing, llamaparse-job.entity-identity, llamaparse-job.known-at, llamaparse-job.institution, llamaparse-contract

**Issue 6 - Verify the remaining lightweight local integrations**

Depends on Issue 3.

Files: pymupdf_backend.py, pymupdf4llm_backend.py, pdfminer_backend.py, pypdfium2_backend.py and local installed-package tests.

Use spawned-process isolation for fitz/pymupdf4llm and runtime-wide locking for
PDFium, covering init/extract/cleanup and mixed sync/async callers. Exercise actual
native work in subprocesses, including event-loop responsiveness. Close pypdf
streams and PDFium document/page/text handles. Check owner-password-only PDFs
against needs_pass rather than assuming is_encrypted means unreadable.

Verify: Run each named extra in isolation on the public PDF and controlled encrypted/corrupt files. Instrument mixed sync/async native boundaries, cleanup and real native heartbeat in subprocesses.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: lightweight-output

| Question | Answer | Kind |
|---|---|---|
| record | One selected local parser invocation over identified PDF bytes. | definitional |
| absent-record | Missing package is unavailable; empty output is distinct from corrupt-input failure. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Name, parser/SDK version, effective settings and input hash identify the invocation. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| lightweight-parsers | All remaining lightweight integrations execute with declared dependencies. | A backend requires an undeclared transitive package or leaks its native document on failure. |

Closes: lightweight-output.record, lightweight-output.absent-record, lightweight-output.ordering-spacing, lightweight-output.entity-identity, lightweight-output.known-at, lightweight-output.institution, lightweight-parsers

**Issue 7 - Verify Docling and Marker model-backed integration contracts**

Depends on Issue 3.

Files: docling_backend.py, marker_backend.py and model-backed installed tests.

Move model acquisition out of constructors. Inspect Docling conversion status
and failures before export; ensure finally cleanup even if export raises. The
verified Docling 2.139 pipeline owns handle cleanup in its finally block; avoid
double-unloading in the wrapper, and terminate worker-owned model memory. Apply
OCR-language/table-mode settings through actual pipeline options. Marker remote
LLM augmentation is unsupported and cannot be activated by defaults or files.
Marker 2.0.0/Surya 0.22.1 require a local CPU llama-server binary for OCR.
Use private per-conversion SDK discovery files and capture subprocess handles at
the pinned SDK spawn sites; stop and reap only those owned processes, including
conversion/rendering failures. Bind services to loopback and forbid external
service reuse or LLM augmentation. Ordinary tests allow only ports added by an
owned spawn and revoke them at cleanup. Local RPC bypasses ambient proxies.
Check local-inference finish/refusal status before Surya drops those fields, and
abort queued inference on failure. Cleanup failure retains completed text.
Model-backed conversions run process-isolated. Real typed partial-conversion
results must fail; model/system blockers leave verification open.

Verify: Run actual CPU model conversions in isolated extra environments on public/controlled PDFs, including typed partial-conversion rejection, option effects and finally cleanup. Do not count missing assets as a pass.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: model-conversion

| Question | Answer | Kind |
|---|---|---|
| record | One document conversion using identified model assets, configuration and runtime. | definitional |
| absent-record | Missing models or failed conversion is not empty-content success. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input/output hashes plus package/model asset identities identify the run. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| model-parsers | Docling and Marker options reach current real conversion APIs. | Only constructors work, Markdown retrieval targets an obsolete field or model assets are undeclared. |

Closes: model-conversion.record, model-conversion.absent-record, model-conversion.ordering-spacing, model-conversion.entity-identity, model-conversion.known-at, model-conversion.institution, model-parsers

**Issue 8 - Verify Kreuzberg, Extractous and Unstructured runtime integration**

Depends on Issue 3.

Files: kreuzberg_backend.py, extractous_backend.py, unstructured_backend.py and native installed tests.

Check the installed Extractous maximum-string-length default and result metadata
for truncation; use its full readinto stream with copied buffers, not its capped
string API or reusable bytearray references. All three wrappers use isolated
native workers, including direct sync and async entry points. Verify
Rust/Java/OCR runtime safety and actual configuration schemas. Unstructured 0.27.27
requires Python 3.11-3.13 and a preinstalled en_core_web_sm 3.8.0 model; missing
assets must not trigger implicit installation or empty-success output. Require
complete page breaks for Unstructured and ordered native pages for Kreuzberg.
Current Marker and Unstructured PDF extras have incompatible Pillow constraints;
keep their environments separate and declare uv conflicts, preserving core Python
3.10 support and an explicit unsupported-Python error for Unstructured. No image capability
is declared until the wrapper's real PNG/JPEG/TIFF route is tested.

Verify: Run real PDF/native/OCR extra-specific checks, controlled image routes where claimed, async heartbeat and sync-from-running-loop behavior. Check Extractous limit/truncation with reachable long content.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: native-conversion

| Question | Answer | Kind |
|---|---|---|
| record | One native/system-tool conversion with input type and configured extraction strategy. | definitional |
| absent-record | Unavailable system tools and failed OCR are errors, not evidence of a blank document. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input/output bytes, backend/runtime/tool versions and effective options identify the run. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| native-parsers | Native/OCR integrations execute their declared PDF/image and async contracts. | The installed version has a different config schema or async results are never awaited. |

Closes: native-conversion.record, native-conversion.absent-record, native-conversion.ordering-spacing, native-conversion.entity-identity, native-conversion.known-at, native-conversion.institution, native-parsers

**Issue 9 - Verify AWS Textract and Azure SDK request and cleanup contracts**

Depends on Issue 3.

Files: aws_textract_backend.py, azure_document_intelligence_backend.py and their isolated provider tests.

Constructors do not resolve credentials or create clients. Page rendering uses
process-isolated fitz helpers, not concurrent threads. Validate supported input and
MIME before client work. Close AWS native handles in finally when later pages
fail. Specify accepted terminal/blank response shapes and preserve primary errors
with cleanup diagnostics; live billing/permissions remain unverified.

Verify: Run real installed SDKs with offline transports for missing/invalid input, oversized/multipage bodies, late-page error, terminal responses and cleanup. Live verification remains separately gated.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: ocr-service-response

| Question | Answer | Kind |
|---|---|---|
| record | One SDK request/page sequence and its documented terminal response. | definitional |
| absent-record | Failed/absent pages do not produce an apparently completed full document. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input hash, page identity, service/SDK configuration and response status identify work. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| ocr-sdk-contracts | AWS/Azure requests and failures follow current documented contracts. | A size rule or SDK body is obsolete, or a late page error publishes early pages as success. |

Closes: ocr-service-response.record, ocr-service-response.absent-record, ocr-service-response.ordering-spacing, ocr-service-response.entity-identity, ocr-service-response.known-at, ocr-service-response.institution, ocr-sdk-contracts

**Issue 10 - Verify Google Document AI synchronous and batch result handling**

Depends on Issue 3.

Files: google_document_ai_backend.py, google extra and tests/providers/test_google.py.

Make page counting a declared dependency using pypdf rather than optional fitz.
Validate document-level status and output destination before shard coverage/order/
duplicate checks. Local timeout does not mean remote termination: attempt bounded
cancellation and retain active-job inputs/resources when completion is uncertain.
Report owned identifiers and cleanup failures explicitly. Use typed Google SDK
exceptions rather than substring classification where available.

Verify: Run offline real-SDK batch pipeline tests with status failures, shuffled/missing/duplicate shards, metadata coverage, timeout/cancellation and cleanup uncertainty. No live upload.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: google-batch-document

| Question | Answer | Kind |
|---|---|---|
| record | One processor job document with explicit terminal status and ordered shards. | definitional |
| absent-record | No output or a failed document remains a failure even if another shard exists. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Processor/version, input hash, job/document ID and shard metadata identify records. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| google-batch-contract | Google batch failures and shard ordering cannot masquerade as complete output. | Lexicographic sorting reorders pages or one failed document is ignored. |

Closes: google-batch-document.record, google-batch-document.absent-record, google-batch-document.ordering-spacing, google-batch-document.entity-identity, google-batch-document.known-at, google-batch-document.institution, google-batch-contract

**Issue 11 - Verify Databricks execution and document-response contracts**

Depends on Issue 3.

Files: databricks_backend.py and tests/providers/test_databricks.py.

Require explicit warehouse configuration; no constructor warehouse discovery.
Verify binary-input/options-map SQL and document.elements[*].content plus
error_status/schema metadata from current official docs. Bound inline payloads or
specify staging lifecycle. Poll pending statements, retrieve all chunks, require
result cardinality, cancel best-effort on timeout, reject malformed/missing results.
SDK transport checks do not prove workspace SQL acceptance.

Verify: Run real SDK transport checks of outgoing documented SQL/binary requests, PENDING-to-SUCCEEDED polling, timeout cancellation, chunk/cardinality and documented nested errors/results. SQL execution remains documentation-backed until authorized live work.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: databricks-statement

| Question | Answer | Kind |
|---|---|---|
| record | One submitted document-parsing statement and its polled terminal result. | definitional |
| absent-record | Pending or missing result is not an empty successful parsed document. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Warehouse, statement ID, input hash, SDK and SQL/function configuration identify work. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| databricks-contract | Databricks parses documented result types and accounts for async statement state. | The function signature is invalid or a still-running statement is labeled a failure or success. |

Closes: databricks-statement.record, databricks-statement.absent-record, databricks-statement.ordering-spacing, databricks-statement.entity-identity, databricks-statement.known-at, databricks-statement.institution, databricks-contract

**Issue 12 - Verify Anthropic document requests and completion handling**

Depends on Issue 3.

Files: anthropic_backend.py and tests/providers/test_anthropic.py.

Require documented terminal stop status and text/blank conditions; reject
refusal/truncation. Decouple model acceptance from pricing tables; reject unknown
kwargs. Preserve provider-reported usage, remove undated USD/page estimates.
Apply lazy credentials/client initialization and explicit per-call result isolation.

Verify: Run real Anthropic SDK transport fixtures including unknown config, terminal text/blank, refusal/truncation and usage responses; errors must originate in the producing wrapper.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: anthropic-message

| Question | Answer | Kind |
|---|---|---|
| record | One document request and completion with model, stop reason and usage. | definitional |
| absent-record | No text, refusal or truncated generation must not imply complete recovered content. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input hash, exact model/API/SDK configuration and message ID identify the operation. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| anthropic-contract | Anthropic output and option accounting reflect actual SDK responses. | A model is rejected only because old pricing lacks it or max-token truncation is ignored. |

Closes: anthropic-message.record, anthropic-message.absent-record, anthropic-message.ordering-spacing, anthropic-message.entity-identity, anthropic-message.known-at, anthropic-message.institution, anthropic-contract

**Issue 13 - Verify OpenAI document uploads, completion status and cleanup**

Depends on Issue 3.

Files: openai_backend.py and tests/providers/test_openai.py.

Current Chat Completions PDF input is not assumed obsolete. Verify actual model
and request limits, finish/refusal status, usage and owned upload lifecycle. Failure
after upload still deletes terminal-operation uploads; uncertain active work is
reported. Successful parse plus cleanup failure raises content-retaining operational
error. Decouple model acceptance from prices and remove undated USD estimates.

Verify: Run real OpenAI SDK upload/completion transports, post-upload generation error, truncation/refusal, cleanup error and content-retaining operational exception checks.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: openai-file-response

| Question | Answer | Kind |
|---|---|---|
| record | One owned upload and document response with terminal completion status. | definitional |
| absent-record | Missing content or incomplete generation cannot imply complete parsed content. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Owned file ID, input hash, exact model/API/SDK options and response ID identify work. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| openai-contract | OpenAI upload lifecycle and completion status survive failure paths. | Generation raises after upload and leaves an unreported file, or incomplete output is returned as full. |

Closes: openai-file-response.record, openai-file-response.absent-record, openai-file-response.ordering-spacing, openai-file-response.entity-identity, openai-file-response.known-at, openai-file-response.institution, openai-contract

**Issue 14 - Verify Gemini document requests and finish/usage semantics**

Depends on Issue 3.

Files: gemini_backend.py and tests/providers/test_gemini.py.

Inspect prompt/candidate block and finish reasons before flattening response.text.
Use current typed SDK responses and actual request parameters/limits, not generic
model tables. Preserve real usage, remove undated USD estimates and size-based
page-limit enforcement. Unknown kwargs fail before client work.

Verify: Run real google-genai SDK transports for MIME/config fields, blocked/truncated/empty typed candidates and usage without accepting unknown kwargs.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: gemini-candidate

| Question | Answer | Kind |
|---|---|---|
| record | One document-generation request with candidate finish status and usage. | definitional |
| absent-record | Blocked, truncated and absent candidates are distinct from complete content. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Input hash, exact model/configuration, SDK and response ID identify the invocation. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| gemini-contract | Gemini honors explicit configuration and interprets candidate status. | The wrapper reads only response.text while ignoring blocked/truncated finish reasons. |

Closes: gemini-candidate.record, gemini-candidate.absent-record, gemini-candidate.ordering-spacing, gemini-candidate.entity-identity, gemini-candidate.known-at, gemini-candidate.institution, gemini-contract

**Issue 15 - Bring CLI options and output preservation into the reviewed contract**

Depends on Issues 2-4.

Files: src/pdfsmith/cli.py and tests/test_cli.py.

Stage output in the destination directory before parsing; validate aliases via
resolved path and samefile, including hard links. Encode/write/close before atomic
replace, which defines commit. Test close/partial-write/replace and separately
post-commit diagnostic failure. stdout/file bytes equal returned UTF-8 exactly;
no extra newline or Written message on stdout. stdout/shell redirection are not
atomic. Backend options replace removed preset/OCR CLI plans.

Verify: Run tests/test_cli.py plus actual console subprocesses. Inject partial-write/encoding/close/replace and post-commit stderr errors; verify input/old output hashes and stdout/file parity.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: cli-operation

| Question | Answer | Kind |
|---|---|---|
| record | One CLI request with an input path, options, stdout/stderr and optional output file. | definitional |
| absent-record | A failed operation produces nonzero exit and cannot replace prior valid output. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Resolved file identity and hashes distinguish input/output, including aliases. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| atomic-cli | The CLI applies reviewed options and preserves previous files on failure. | A parse/write failure truncates output, stdout carries diagnostics or an output alias destroys input. |

Closes: cli-operation.record, cli-operation.absent-record, cli-operation.ordering-spacing, cli-operation.entity-identity, cli-operation.known-at, cli-operation.institution, atomic-cli

**Issue 16 - Reconcile package identity, installation coverage and final handoff**

Depends on the affected backend/CLI milestones; unresolved live authorization remains explicit.

Files: pyproject.toml, generated uv.lock, README reconciliation and tests/verify_distribution.py.

Early version/core-wheel work is already owned by Issue 1. Final package work
checks each extra and advertised bundle in empty non-editable wheel environments
on Python 3.10-3.13 or narrows reproduced support bounds. Test runner/fixture tools
cannot mask dependencies. Local assessment with a blocker is not verified closure.
Keep offline/live service evidence separate and correct stale tests instead of
using skips. Supply the editorial handoff separately from package verification.

Verify: Build once and install the wheel into empty Python 3.10-3.13 core/baseline and each-extra environments; run all applicable unpaid tests, Ruff and repository mypy. Reconcile bundles and support limits with actual outcomes.
Use uv-managed environments and pytest with the focused selection described above.
Record commands, exit results, source/wheel/dependency identities and input/output
hashes. Run Ruff and mypy before the scoped commit.

Done means the stated tests executed and passed with no unintended file changes;
provider rows remain live-unverified until authorized real execution.

### Premises

Input: package-evidence

| Question | Answer | Kind |
|---|---|---|
| record | One installed distribution/backend/configuration test outcome linked to source and artifacts. | definitional |
| absent-record | A skip, missing run or unavailable environment is not a passing integration result. | definitional |
| ordering-spacing | Honor document/page/service order where defined; do not treat filename or registry order as extraction quality. | empirical |
| entity-identity | Wheel hash, source revision, dependency snapshot and input/output hashes identify evidence. | definitional |
| known-at | Input and effective options are fixed before invocation; SDK/service status is known only when returned and validated. | definitional |
| institution | PDFsmith specification defines wrapper behavior; pinned parser/SDK contracts define provider fields and ordering. | definitional |

### Claims

| Id | Claim | How it could be false |
|---|---|---|
| installed-identity | Installable package identity and support claims match fresh executed evidence. | Module and wheel versions disagree, a declared extra omits a dependency or skipped providers are called verified. |

Closes: package-evidence.record, package-evidence.absent-record, package-evidence.ordering-spacing, package-evidence.entity-identity, package-evidence.known-at, package-evidence.institution, installed-identity

## Next actions

No further planning approval is required. Provider spending, public-main merge and
package release remain separate decisions once concrete requests are prepared.
