# Plan: PDFsmith library update and complete backend verification

This plan decomposes spec.md after Stefan selected every registered backend for
verification. It is a proposal for external GPT and Claude review, not evidence
that implementation or service validation occurred. All source changes depend on
returned reports and reconciliation of consequential findings. Baseline diagnostics
are already authorized and are recorded separately under baseline/.

## Design for review

Preserve the released string API and backend identifiers. Repair the inherited
extension rather than replacing the parser architecture. Keep registry metadata
separate from initialized instances: discovery must not create clients/models.
Expose a full registered inventory and distinguish dependency detection from
configured/readiness and fresh document-level verification. Proposed public
addition: registered_backends() -> list[BackendInfo]. Keep the existing no-argument
available_backends() order for compatibility; add an explicit include_services
keyword if needed to inspect installed service dependencies without initializing
them. Reviewers should challenge whether this addition is sufficient or redundant.

Resolve one backend per operation, then validate effective options against its
explicit supported contract before constructing it. Unknown keys and unsupported
preset/OCR requests fail rather than disappear. Do not infer support from **kwargs.
Retain no-option get_backend() reuse; configured parse calls must not share mutable
option dictionaries or result accounting. Run blocking setup/extraction off the
async event loop; use a native async path only where its setup and errors obey the
same contract. Document cancellation of executor work without claiming it kills a
thread or rolls back a provider job.

Use a single development-version source for an unpublished 0.3.0.dev0 build; the
existing public wheel remains 0.2.0. The reviewed implementation may use Hatch's
version-from-module support. The inherited 0.3.0 string is evidence of a proposal,
not authority to release. No release is part of this plan.

For local options, forward only documented settings to the producing extraction
calls, with per-backend schemas and behavior tests. Preserve default output unless
a reproduced defect requires a reviewed correction. Retain preset names only as
configuration aliases, without a quality guarantee. Keep images backend-specific;
reject formats not actually supported by that wrapper. Do not promise structured
JSON, bounding boxes or semantic completeness through a str return value.

For services, test the real installed SDK with offline transports and official
response shapes, not a second implementation of the wrapper. Validate paths and
options before uploads, inspect failure/truncation/partial statuses, use bounded
polling, and clean up owned temporary resources on failure. Offline SDK success is
not a live integration pass. Service E2E remains an explicit pending gate until
Stefan approves a concrete provider/configuration/input/spend protocol.

LlamaParse is an early independent service milestone. Assess migrating the existing
llamaparse backend to the current llama-cloud Parse v2 SDK, with explicit tier and
service version, nested processing/output controls and observable cache policy.
Keep its identifier, and provide an explicit legacy parsing_mode compatibility
mapping or rejection. A premium-to-agentic_plus mapping cannot be assumed equivalent.
The current wrapper does not forward parsing_mode at all. ParseBench informs the
need for preserved table/format content and transparent configuration; comparisons
and benchmark reuse belong to PDF-Bench. Adding LiteParse is outside this registry
update unless Stefan expands scope.

## Verification and evidence

Each issue first reproduces its user-visible error, then adds a regression that
fails with the producing defect and passes after repair. Tests named below are
planned additions to the indicated existing files or explicitly proposed new
files; they are not claimed to exist or pass today. New proposed files are
 tests/test_contracts.py, tests/test_installed_package.py and
 tests/test_provider_contracts.py. Exact selection names will be set with the tests.
Run focused pytest, Ruff and repository type checks before each scoped commit.
Install pre-commit before committing. Test environments may use python -m pytest
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

Files: work-unit evidence, .gitignore, tests/test_api.py and the proposed
 tests/test_contracts.py. Retain an allowlisted, hashed source snapshot and classify
inherited work by chronology and unknown authorship. Ignore credential/runtime
artifacts without deleting them. Add real public-API regressions for the observed
pdf_path keyword break, no-option instance reuse, ignored options and constructor
preset mismatch. Keep these expected failures visible until their owning repairs.
Do not commit inherited provider changes in this checkpoint.

Verify: replay baseline_probe.py against separate installed public/release/working
snapshots. Run uv run --extra dev --extra pypdf --extra pdfplumber pytest
 tests/test_api.py tests/test_contracts.py -q. This checkpoint records the exact
expected failures rather than claiming the suite is green. Mark tests requiring a
later fix as explicit expected failures with the reproduced reason, then remove
that marker in the owning repair; never use an unexplained blanket xfail.
Done when the initial bytes and actual defect triggers are recoverable without
secret files, and inherited work is distinct from owned changes.

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

Depends on Issue 1. Files: api.py, __init__.py, backends/registry.py and
 tests/test_api.py plus tests/test_contracts.py. Add full inventory with verified
extra names and separate local/service/input metadata. Preserve legacy order and
local-only default selection. Dependency checks cannot create clients/models,
read credentials or invoke providers. Explicit selection cannot substitute another
backend. Repair no-option instance reuse while isolating configured instances.

Verify: uv run --extra dev --extra pypdf --extra pdfplumber pytest
 tests/test_api.py tests/test_contracts.py -q. Test core-only and missing-dependency
subprocesses plus installed SDK-only environments; make any constructor or outbound
request during discovery fail the test. Show the inherited singleton regression
failing before the repair and passing after it. Done when all 19 names are
addressable and discovery never asserts successful service execution.

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

Depends on Issue 2. Files: api.py, config.py, tests/test_async.py and
 tests/test_contracts.py. Restore released keyword compatibility. Resolve once,
validate types/keys/input support, merge documented sources and dispatch identically
for sync/async. Explicit backend options override common OCR settings and presets;
those explicit layers override backend environment/file/default configuration.
Reject invalid/unsupported requests before constructor/provider activity. Preserve
native extraction exceptions and distinguish valid empty strings. Offload blocking
imports/setup as well as parsing; define executor cancellation limits.

Verify: uv run --extra dev --extra pypdf --extra pdfplumber pytest
 tests/test_api.py tests/test_async.py tests/test_config.py tests/test_contracts.py -q.
Use genuine unknown preset/OCR requests and conflicting configuration sources;
assert no client initialization or input/output mutation on rejection. Run a loop
heartbeat during deliberately blocked constructor and extraction calls. Concurrent
calls with conflicting options must not contaminate each other. Done when the
keyword and silent-option regressions pass on both entry points.

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

Depends on Issue 3. Files: pypdf_backend.py, pdfplumber_backend.py,
 tests/test_backends.py and tests/test_installed_package.py. Implement a bounded,
explicit option set based on current official extract_text/extract_tables APIs.
Cover pypdf extraction mode and pdfplumber layout/text/table settings where useful;
forward them to producing calls rather than constructors that cannot accept them.
Preserve plain defaults and document table/text duplication if retained.

Verify: isolated extras with uv, then python -m pytest on the proposed installed
package tests for these two backends. Parse the identified public Premera document
and deterministic controlled layout/table/blank/corrupt/missing inputs through API,
async API and CLI. A deliberately chosen layout fixture must change output under
layout settings, and the inherited preset error must fail before repair. Done when
both independent baseline backends have fresh hashed real-output evidence.

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

Depends on Issue 3; can proceed independently of the remaining local integrations.
Files: llamaparse_backend.py, pyproject.toml/lockfile as needed, and
 tests/test_provider_contracts.py. Pin the supported modern SDK/API contract from
current official documentation. Proposed path is llama-cloud Parse v2, retaining
the llamaparse name and explicit treatment of legacy parsing_mode/language. Expose
effective tier/version/cache controls, correct Markdown retrieval, bounded polling,
partial/failed results and resource cleanup. Remove historical price/quality
assertions unless evidence and ownership justify a separate claim. No live call.

Verify: install only the declared extra and run uv run --extra dev --extra
llamaparse pytest tests/test_provider_contracts.py -k llamaparse -q. Use the actual
installed SDK with an offline transport to inspect uploads, nested request fields,
version/tier changes, status polling and Markdown extraction. Test missing API key,
invalid settings, partial job, timeout and cleanup failure. A mutation that drops
tier/version must fail. Prepare a hashed one-document live protocol for Stefan's
separate authorization. Done offline means SDK-contract verified, live-unverified.

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

Depends on Issue 3. Files: pymupdf_backend.py, pymupdf4llm_backend.py,
 pdfminer_backend.py, pypdfium2_backend.py, metadata and backend/installed tests.
Check current official APIs and install extras separately. Repair installation
hints, supported extraction options and native handle/stream cleanup on exceptions.
Keep backend identifiers and direct constructor calls stable. Report PDF/image
input support from actual wrappers, not underlying-library possibilities.

Verify: run the proposed installed-package test selection for each of pymupdf,
pymupdf4llm, pdfminer and pypdfium2 in its isolated extra environment. Parse public
and controlled PDFs, repeat/concurrently execute where supported, provoke corrupt
and encrypted/missing input, and demonstrate release of native documents/pages/text
handles after producing-code errors. Done when each row has independent output
hashes and a precise dependency/platform contract.

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

Depends on Issue 3. Files: docling_backend.py, marker_backend.py, config.py,
metadata and backend/installed tests. Verify current official conversion/rendering
APIs, required configuration dependencies, model assets and system/runtime bounds.
Repair dropped OCR-language/table settings and the actual Marker result conversion
where current APIs require it. No-option operation must not enable paid model use.
Separate first-use model acquisition from subsequent parsing evidence. Inspect
resources before downloads; report measured incompatibility instead of skipping it.

Verify: isolated docling and marker extras, documented CPU fixtures/public PDF,
blank/corrupt controls, effective OCR/table configurations, repeated parsing and
cleanup. Actual model-backed E2E is required for a working-local claim. Offline
class stubs alone do not satisfy it. Run focused backend and installed-package
pytest selections plus Ruff/type checks. Done when each local integration really
runs or remains explicitly open with a reproduced upstream/runtime blocker.

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

Depends on Issue 3. Files: kreuzberg_backend.py, extractous_backend.py,
unstructured_backend.py, metadata and backend/installed tests. Check current APIs,
Rust/Java/native/system requirements, OCR language/configuration and image support.
Repair async dispatch and unsupported strategy/option acceptance. Do not infer
that images work because the registry lists the backend as image-capable.

Verify: each extra in isolation, actual public/controlled PDF runs, a controlled
image only for claimed image support, empty/corrupt controls and option-effect
fixtures. Test sync use inside/outside a running loop according to the documented
contract, and async calls with a responsive loop. State native/OCR tool versions.
Run focused backend/installed-package tests. Done when all three local rows have
real evidence or an explicit still-open reproduced failure.

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

Depends on Issue 3. Files: aws_textract_backend.py,
 azure_document_intelligence_backend.py, extras and tests/test_provider_contracts.py.
Verify official current input/size/page rules and SDK signatures. Validate all
local inputs before client/provider work, handle page conversion and extraction,
resource cleanup, terminal failures and configured input types. Offline fixtures
must be encoded with real installed SDK types or transports. No live call.

Verify: isolated aws and azure extras and offline transport tests for valid,
missing, corrupt, oversized, multipage, partial-result and provider-error paths.
Reproduce cleanup behavior when a later page fails. Document exactly what returned
text can represent and cannot represent. Run the provider pytest selections.
Done offline when contracts pass and concrete live protocols remain visibly gated.

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

Depends on Issue 3. Files: google_document_ai_backend.py, extras and provider
tests. Reconcile inherited batch work rather than replacing it blindly. Verify
processor-dependent limits, credentials and SDK/GCS dependencies, regional endpoint,
per-document status, shard/page order, bounded polling and cleanup. Inspect batch
metadata before treating outputs as complete. Do not sort shards as plain filename
strings if document shard metadata defines order. No GCS upload or live call.

Verify: actual SDK message round-trips and offline fake transport/storage matching
SDK objects. Include partial failure, missing output, shuffled/multi-digit shards,
poll timeout and upload/download/cleanup failure. A mutation that ignores failure
metadata or shard order must fail. Run google provider tests in the isolated extra.
Done offline when real SDK contracts pass, inherited changes are accounted for and
live upload/processor validation remains a separate recorded gate.

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

Depends on Issue 3. Files: databricks_backend.py, extras and provider tests.
Check the current official ai_parse_document input/output contract and supported
SDK statement polling. Review SQL/binary upload approach against documented APIs;
replace unsupported encoding/signature assumptions. Use explicit warehouse
configuration for predictable operation and avoid discovery starting remote work.
Differentiate pending/error/missing-result/partial document responses. No live SQL.

Verify: isolated databricks extra and actual SDK transport/typed response tests,
including queued/running/succeeded/failed/canceled states, timeout, no result,
malformed response and meaningful parsed elements. Test the submitted SQL/request,
not just a mocked wrapper return value. Done offline when current contracts are
checked and a concrete authorized live workspace protocol is ready.

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

Depends on Issue 3. Files: anthropic_backend.py, metadata and provider tests.
Reconcile inherited model mappings with current official document API and model
support. Decouple usable model identity from stale price dictionaries. Make any
retained constructor kwargs explicit, verify file/page limits and supported input
types, inspect stop reasons/truncation/refusal and avoid misleading cost accounting.
No live inference or model-selection quality claim.

Verify: actual installed SDK with offline transport and realistic typed messages,
usage/stop/error responses, invalid/missing configuration, truncated output and
concurrent option/accounting isolation. Provoke failures through the producing
wrapper and SDK request. Run anthropic provider tests. Done offline with exact
supported request contract and live-unverified status.

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

Depends on Issue 3. Files: openai_backend.py, metadata and provider tests.
Check current official file-input and response API support before selecting the
supported API path. Preserve useful caller model configuration, validate supported
options and completion state, and delete only uploads owned by this operation on
success and failure. Cleanup errors must not conceal the original parse error.
Do not equate an empty response or output-token limit with a full parse. No live call.

Verify: actual SDK with offline HTTP transport, successful and failed upload,
provider rejection after upload, truncation/refusal/empty responses and deletion
failure. A mutation that removes cleanup on generation failure must fail. Run
openai provider tests in the isolated extra. Done offline with fresh SDK request
and cleanup evidence plus a separate live-run protocol.

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

Depends on Issue 3. Files: gemini_backend.py, metadata and provider tests.
Check current official google-genai document handling, model IDs and output limits.
Remove silent option acceptance and stale-price coupling, inspect candidate finish
reasons/safety blocks, verify usage accounting from documented response fields and
clean up owned resources. Preserve environment-key compatibility. No live call.

Verify: installed google-genai SDK with offline transport; inspect MIME/bytes and
model/config request fields and actual typed blocked/truncated/empty/error/usage
responses. Test concurrent differently configured calls. Run gemini provider tests.
Done offline with exact SDK contract and visibly pending live-service verification.

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

Depends on Issues 2-4; other backend capabilities can become available later
without redesigning the CLI. Files: cli.py and tests/test_cli.py. Add explicit
configuration arguments matching the reviewed Python option schema, with no
credential-bearing command suggestions. Label inventory states honestly. Keep
stdout reserved for parse output and stderr for diagnostics. Stage complete file
output and replace atomically after parse/serialization success. Reject output
paths that would overwrite the input, including aliases, before extraction.

Verify: uv run --extra dev --extra pypdf --extra pdfplumber pytest tests/test_cli.py
 tests/test_installed_package.py -q. Run actual console subprocesses, invalid JSON,
unknown options, missing/corrupt/blank input, input/output aliasing and deliberately
failed serialization/write/replace. Prior valid output must remain byte-identical.
Done when installed CLI has the same effective configuration and failure semantics
as Python without output corruption.

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

Depends on Issues 1-15 for affected backend claims; independently completed
local milestones can export before every live gate is cleared. Files: package
metadata/version, lockfile, README after reconciliation of the existing correction
branch, required support documentation and tests/test_installed_package.py.
Generate the lockfile using uv, never manually. Build the unpublished wheel,
install it outside the checkout and test declared extras/Python bounds separately.
Use a single development version and record public/released/working identities.

Verify: uv build, installed wheel core-only/each-extra subprocess checks, and all
unpaid tests plus Ruff and repository type checks under declared environments.
Every local working claim needs actual output/input hashes. Every service row
separates SDK-contract verification from a live run. Re-run baseline diagnostics
against the new wheel and show each repaired regression's failing/passing evidence.
Publish no release or public-main merge. Supply one website-editorial-handoff.txt
and concise progress.txt, with exact support/exclusions and live-run protocols.
Done engineering means reviewed offline work and local verification are complete;
full live-service verification remains open until separately authorized runs pass.

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

Stefan submits the external review packet to GPT and Claude and returns both reports.
Provider spending, public-main merge and package release remain separate decisions.
