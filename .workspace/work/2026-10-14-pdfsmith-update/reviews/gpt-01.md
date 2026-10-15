# Decision: revise before implementation

The scope and staged approach are sound. **The shared lifecycle, configuration, execution-safety and failure contracts need several decisions before Issues 2–3 begin.** Most provider-specific defects already have appropriate issue owners and should block only those integrations. The first pypdf/pdfplumber milestone can finish independently of service verification.

I reviewed the complete packet, verified all **55 embedded file hashes**, and executed its configuration and option-building helpers in a temporary, credential-free environment. Those probes reproduced several configuration defects described below. I also checked targeted current primary documentation. I did **not** replay the recorded installed-package baselines, install or execute service SDKs, contact parsing services, or modify repository source.

## Scope and evidence accounting

**All 19 registered names are accounted for:** 11 local integrations and eight service integrations. The inventory does not claim that the remaining 17 integrations have document-level validation. Its two recorded local passes cover default behavior, not the proposed option contracts. external-review-packet

| Plan issue | Integrations | Evidence currently supplied |
|---|---|---|
| 4 | `pypdf`, `pdfplumber` | Recorded isolated installed-package document runs; configuration defects reproduced in the packet |
| 6 | `pymupdf`, `pymupdf4llm`, `pdfminer`, `pypdfium2` | Source inspection; integration runs pending |
| 7 | `docling`, `marker` | Source inspection; model-backed runs pending |
| 8 | `unstructured`, `kreuzberg`, `extractous` | Source inspection; native/runtime runs pending |
| 5 | `llamaparse` | Source inspection and documentation assessment; installed-SDK and live checks pending |
| 9 | `aws_textract`, `azure_document_intelligence` | Source inspection; offline SDK and live checks pending |
| 10 | `google_document_ai` | Inherited batch implementation inspected; offline SDK and live checks pending |
| 11 | `databricks` | Source inspection; request/result repair and verification pending |
| 12 | `anthropic` | Source inspection; offline SDK and live checks pending |
| 13 | `openai` | Source inspection; offline SDK and live checks pending |
| 14 | `gemini` | Source inspection; offline SDK and live checks pending |

Keep registration, dependency detection, configuration, offline SDK-contract evidence and document-level execution as separate fields. In particular, **“configuration not checked” is a legitimate discovery result**; discovering backends must not trigger credential resolution merely to fill that column.

## Findings ordered by severity

Paths below refer to `working-source/` unless otherwise indicated.

### F1 — High: the unpaid-test boundary is not fail-closed

**Affected issues:** 1, 5, 9–14, 16. **Blocks:** broad/provider test execution until guarded; not targeted local-baseline implementation.

**Evidence and failure scenario.** `tests/integration/test_commercial_integration.py` enables its live tests whenever `RUN_COMMERCIAL_TESTS` contains any nonempty string. Consequently, `RUN_COMMERCIAL_TESTS=0` enables them. The tests then construct actual clients and parse documents when credential variables exist. Registered pytest markers do not themselves prevent execution. The proposed final “all unpaid tests” command therefore needs an executable exclusion policy, not an interpretation of which tests are unpaid. external-review-packet external-review-packet external-review-packet

**Required change.** Put a shared safety harness in Issue 1, before provider test environments are used. Default test execution must exclude live tests and deny unexpected network access, including credential discovery, token refresh and metadata-service access. Supply synthetic credentials and controlled home/configuration locations to offline SDK tests. A separate explicit live command must select the authorized provider, input and configuration; an inherited environment flag must not constitute authorization.

**Exposing test.** Run ordinary test collection/execution with the flag absent, `"0"`, `"false"` and `"1"`, synthetic credential variables present, and an outbound-network tripwire. Every ordinary run must execute zero live requests. Offline transports must also reject unexpected additional requests.

### F2 — High: validation ownership is unresolved across the API, constructors and discovery

**Affected issues:** 2–3 and backend issues 5–14. **Blocks:** shared lifecycle implementation until ownership is specified; Issue 1 and isolated compatibility diagnostics remain independent.

**Evidence and failure scenario.** The packet correctly identifies PDF-Bench’s direct `loader() → constructor(**kwargs) → parse(path)` path. API-only validation cannot protect it. Databricks constructs its SDK client and potentially lists warehouses in `__init__`; Marker creates model assets in `__init__`. These actions precede any document-path validation on the direct path. Separately, `BackendInfo.is_available()` invokes the loader, and importing the Docling wrapper mutates process-wide thread environment variables. A test that forbids constructors during discovery would miss that import-time mutation. external-review-packet external-review-packet external-review-packet external-review-packet external-review-packet

**Required change.** Specify one lifecycle:

- Discovery reads static metadata and dependency information without importing backend implementations.
- Constructors normalize and validate configuration, without creating models, resolving credentials or contacting providers.
- `parse()` validates its input before lazy expensive initialization.
- Public API and direct-constructor calls use the same option normalization and validation helpers.

Distinguish cheap path/configuration checks from structural PDF inspection. The specification should not imply that arbitrary PDF corruption can be detected without inspecting the document.

**Exposing test.** Invoke the actual direct loader/constructor path with invalid options, then parse a missing file and a directory. Assert zero client/model initialization and requests. In a separate discovery subprocess, compare environment variables and loaded backend modules before and after listing all 19 entries.

### F3 — High: configuration precedence is described, but not yet an implementable contract

**Affected issues:** 3–5, 7–8, 12–15. **Blocks:** shared configuration implementation; each backend’s detailed option schema can be completed in its owning issue.

**Evidence and failure scenario.** Several independent defects are present:

* Docling advertises `DOCLING_OCR`, while its actual `KNOWN_OPTIONS` contains `do_ocr`; the loader searches for `DOCLING_DO_OCR`. I reproduced the advertised variable being ignored.
* Environment values remain strings. Docling reads `_config` directly rather than using `BackendConfig.get_bool()`.
* `_find_config_file()` chooses the local file instead of merging local and user configuration. I reproduced a local file containing only `do_ocr` suppressing the user’s unrelated `num_threads`.
* `get_backend_defaults()` makes a shallow copy. I reproduced mutation of one returned `ocr_languages` list appearing in another returned defaults dictionary. external-review-packet external-review-packet external-review-packet external-review-packet

**Required change.** Write the exact precedence order, including both environment prefixes and both file locations. A reasonable choice is:

`backend_options > common OCR > preset > PDFSMITH-prefixed environment > legacy environment > project YAML > user YAML > defaults`.

Define per-key merge behavior, nested mappings, aliases, omitted values versus explicit `None`, strict booleans/numbers, unknown keys in files and environment, and conflicting OCR/language settings. Normalize once and retain an immutable effective configuration; constructors must not reread configuration after API validation. Provide a read-only, non-secret effective-options surface for direct consumers.

Preserve `pdf_path=` on both sync and async APIs. Retaining inherited `input_path=` as an alias is inexpensive; supplying both should raise a documented error.

**Exposing test.** Put distinct values in every source, exercise canonical and legacy aliases, mutate nested caller dictionaries after construction, and verify the actual producing parser/SDK arguments through both API and direct construction. Invalid values must fail before expensive initialization—not merely be coerced differently by different SDKs.

### F4 — High: generic executor dispatch conflicts with native-runtime safety

**Affected issues:** 3, 6–7, 9–10, 12–14 wherever native PDF helpers are used. **Blocks:** shared async execution-policy selection and affected native milestones; not all local parsing work.

**Evidence and failure scenario.** The current async API initializes on the event-loop thread, then sends extraction to the default executor. The proposal fixes blocking initialization but does not specify backend thread-safety or cross-backend synchronization. PyMuPDF explicitly warns against multithreaded use. PDFium forbids simultaneous calls across threads even for different documents, including indirect wrappers. Fresh backend instances therefore do not solve the problem. external-review-packet [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html?utm_source=chatgpt.com)

The exposure also exists outside the named local backends: AWS rendering and several service page-count helpers call PyMuPDF. Two otherwise independent provider operations can therefore overlap in the same native library. external-review-packet external-review-packet

**Required change.** Declare execution policy per native runtime: thread-compatible, serialized, or process-isolated. Use process isolation for PyMuPDF-backed work unless a supported alternative is established. For PDFium, a shared synchronization boundary must cover all PDFsmith paths using that runtime; an instance lock is insufficient. Include direct synchronous calls, initialization and cleanup.

Separately define singleton initialization locking, failed-initialization retry behavior, configuration lifetime and result-accounting semantics. Preserve no-option `get_backend()` reuse without sharing mutable per-call results.

**Exposing test.** Overlap sync and async calls through different affected backends and instrument the native boundary to detect prohibited overlap. Run actual native tests in subprocesses. Keep the heartbeat test, but add real extraction coverage: a blocked Python constructor alone cannot establish responsiveness during native code execution.

### F5 — High: repairing option forwarding can activate hidden provider work; image routing remains overstated

**Affected issues:** 2–3, 7, 15 and each integration advertising images. **Blocks:** shared default/preset policy and affected image claims; not explicit baseline PDF parsing.

**Evidence and failure scenario.** `PRESETS["best"]["marker"]` contains `use_llm=True`. Today Marker’s zero-argument constructor rejects that preset. A straightforward constructor repair would activate the flag. Marker’s current documentation describes external LLM services, including a default Gemini service, under this option. Thus a generic preset could cross the promised local/unpaid boundary after the proposed repair. This is a prospective regression, not evidence that the current code already made a paid call. external-review-packet external-review-packet [GitHub](https://github.com/datalab-to/marker?utm_source=chatgpt.com)

The inherited image-capability set includes every service, but Azure, Anthropic and Gemini hard-code PDF request representations. AWS explicitly opens input as PDF. Registry membership therefore overstates wrapper support. external-review-packet external-review-packet external-review-packet external-review-packet

**Required change.** No generic preset, automatic selection or implicit configuration should enable an external inference service. Remove that Marker preset flag; any retained remote augmentation requires explicit provider-bearing configuration. Separate first-use model downloads from provider execution.

Represent input support as per-backend supported formats and actual request routing, not one image boolean. Unsupported formats must fail before upload. Define extension/content mismatch handling and the omitted `.tif` case.

**Exposing test.** Exercise every preset for automatically selectable local backends with outbound access denied. For image claims, pass real controlled PNG/JPEG/TIFF inputs through the wrapper and inspect the SDK request MIME/type/bytes. Negative image tests must assert zero requests and no substitution of a paid backend.

### F6 — High: LlamaParse v2 is a justified direction, but its migration contract is incomplete

**Affected issue:** 5, with option-schema dependencies in 3. **Blocks:** LlamaParse migration only.

**Evidence and failure scenario.** `LlamaParseBackend.__init__` validates and stores `parsing_mode`, then omits it from the SDK constructor. Existing tests explicitly expect the SDK call without that setting and only check the stored attribute for custom modes. They preserve the defect. external-review-packet external-review-packet(1)

Current official documentation supports migrating to `llama-cloud` Parse v2: it requires tier/version, nests language and processing settings, changes page indexing and consolidates cache controls. That supports the migration direction; it does not establish what the owner’s currently installed legacy SDK can already express. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/migration-v1-to-v2/)

**Required change before replacing the SDK path.** Inspect the actual installed distributions behind `llama_parse.LlamaParse`: versions, module origin/re-exports, constructor/model fields, handling of unknown fields, request serialization, endpoint, effective mode/tier defaults, version controls, cache flags, polling, retries and error handling. Determine whether `load_data()` suppresses errors or loses page/job status. The packet supplies package metadata observations, not this installed-SDK evidence. external-review-packet

Then resolve five contract details:

**Defaults and compatibility.** Specify the no-option tier and service version. The old nominal `cost_effective` default does not establish the old effective service behavior. Define legacy mappings and conflict handling. Rejecting `premium` with a migration message is safer than assuming equivalence to `agentic_plus`.

**Effective identity.** Keep requested tier/version separate from provider-confirmed identity. Moving version aliases and cost-optimizer routing must remain visible; a requested tier may not describe every page’s processing. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/tiers/)

**Cache.** Define the default and expose the actual v2 `disable_cache` control. Do not invent equivalence between legacy invalidate-only behavior and disabling cache. Cache-hit status remains unknown unless returned or otherwise established. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/configuring-parse/)

**Completion and output.** Check terminal job state, page success, expected page coverage, ordering and requested output presence before flattening. A completed blank page differs from an absent Markdown expansion. Current responses explicitly contain failed-page variants. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/response-format/)

**Tier/version compatibility.** Current documentation says older pinned `fast` versions are text-only, while newer ones support Markdown. Neither “fast always supports Markdown” nor “fast never supports Markdown” is a valid blanket rule. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/response-format/)

**Exposing tests.** Use the real selected SDK with offline transport to verify differing tier/version/cache requests, legacy conflicts, a successful job containing a failed page, missing expansion, reordered/duplicate pages and supported versus unsupported tier/version combinations. Prefer the SDK’s existing polling helper after inspecting its limits; the Python SDK already provides one. [Developer Documentation](https://developers.llamaindex.ai/llamaparse/parse/getting_started/)

### F7 — High: Databricks has concrete request and result-schema defects beyond missing polling

**Affected issue:** 11. **Blocks:** Databricks only.

**Evidence and failure scenario.** The wrapper submits:

```sql
SELECT ai_parse_document('<base64>', 'base64') as result
```

It then expects top-level `elements[*].text`, returns `""` for missing statement results, and returns malformed JSON unchanged. Current Databricks documentation specifies binary content, an options map, and a result containing `document.elements[*].content`, `error_status` and schema metadata. A valid documented result can therefore become empty “success” in this wrapper. external-review-packet [Databricks Documentation](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document)

**Required change.** Select and document a supported binary-input mechanism and explicit output schema. Validate statement completion separately from document-level errors. Retrieve all required result chunks, require the expected result cardinality, and reject malformed or structurally unexpected responses. Choose a bounded inline-input approach or explicit staging; do not introduce staging resources without lifecycle requirements.

**Exposing test.** Send the producing wrapper through the real SDK transport and verify the submitted request. Return a typed successful statement containing the documented nested document schema, then variants with page errors, missing results, truncated/chunked results and malformed JSON.

A transport test can verify SDK serialization and wrapper handling. **It cannot prove that the SQL engine accepts the statement or that a workspace supports the function.** Record SQL/function compatibility as documentation-backed until an authorized live execution occurs.

### F8 — High: the completion rule needs explicit predicates, including local partial conversions

**Affected issues:** 5, 7, 9–14. **Blocks:** affected integration closure, not baseline contract repair.

**Evidence and failure scenario.** Several producing paths discard completion information:

- Anthropic extracts text without inspecting stop status; OpenAI reads the first choice’s content; Gemini uses `response.text or ""`.
- Google treats operation completion as sufficient and concatenates lexicographically sorted JSON objects without checking per-document metadata.
- Docling exports `result.document` without checking conversion status.
- Existing Databricks tests explicitly accept absent result data as `""`. external-review-packet external-review-packet external-review-packet external-review-packet external-review-packet external-review-packet(1)

**Required change.** Each integration’s contract must identify accepted terminal statuses, refusal/truncation indicators, required result fields and the representation of a successful blank document. Unknown or incomplete status must not become successful text.

For Google, validate the submitted document’s status and declared output destination, then shard identity, count and order. For Docling and other converters, inspect available conversion/error metadata before export. Inspect Extractous metadata before deciding it carries no relevant failure information.

**Exposing test.** Return usable text alongside an explicit failure, truncation or failed-page indicator; the wrapper must raise. Pair that with an actual successful blank representation that returns `""`. For Google, test a missing middle shard, duplicates and multi-digit shard names through `_parse_batch`, not only the concatenation helper.

The plan appropriately excludes detecting silent semantic omissions. A terminal success status establishes protocol completion, not complete transcription of everything in the document. external-review-packet

### F9 — High: cleanup and cancellation lack a terminal-state policy

**Affected issues:** 3, 5–7, 9–14. **Blocks:** affected resource-lifecycle milestones and their cancellation claims.

**Evidence and failure scenario.** OpenAI cleanup runs only after generation and suppresses deletion errors. AWS closes a multipage PDF only after its page loop succeeds. PDFium explicitly closes none of its handles. Docling cleanup occurs after export and suppresses failures. Google unconditionally attempts prefix cleanup in `finally`, including when waiting times out. external-review-packet external-review-packet external-review-packet external-review-packet external-review-packet

For Google, a local timeout does not establish remote termination. Deleting currently visible objects can remove an active job’s input, while later output objects can still appear after cleanup finishes.

**Required change.** Define behavior for failure before submission, failure after a known submission, ambiguous submission, confirmed terminal failure and local cancellation. Cleanup must use operation-owned resources and known lifecycle state. When completion remains uncertain, report identifiers and residual-resource uncertainty rather than claiming cleanup succeeded.

Choose an observable policy for cleanup failure after successful extraction. Preserve the original parse exception when both fail. Define retry behavior for non-idempotent uploads/submissions; an ambiguous timeout must not automatically cause duplicate paid work. Executor cancellation must leave the worker responsible for eventual local cleanup.

**Exposing test.** Fail generation after upload, fail a later AWS page, fail export before Docling cleanup, fail deletion after successful extraction, and simulate a job that continues after timeout. Verify primary-error preservation, resource ownership, no premature cleanup of active work, and no duplicate submission on an ambiguous response.

### F10 — High: CLI atomicity is achievable, but the promise needs a commit boundary

**Affected issue:** 15; shared failure semantics in 3. **Blocks:** CLI output-preservation milestone only.

**Evidence and failure scenario.** `cli.py::cmd_parse` writes directly to the destination and prints a success message afterward inside the same exception handler. It can overwrite the input through an alias, truncate previous output before a write/encoding failure, or report failure after output was successfully committed but the subsequent message failed. Issue 15 addresses staging and aliases, but the specification’s unconditional preservation wording does not distinguish pre-commit and post-commit failures. external-review-packet external-review-packet external-review-packet

**Required change.** Validate output identity and create staging in the destination directory before expensive parsing. Reject input aliases using resolved paths and file identity, including hard links. Fully encode, write and close the staged file, then atomically replace the destination. That replacement is the commit point; cross-filesystem replacement must not be assumed atomic. [Python documentation](https://docs.python.org/3/library/os.html?utm_source=chatgpt.com)

Promise preservation for failures **before commit**. Do not imply rollback after replacement, atomic stdout delivery, crash durability without additional measures, or protection from shell redirection performed before PDFsmith starts. Treat post-commit diagnostic failures separately. Move the library’s “Written to…” message to stderr.

**Exposing test.** Use actual console subprocesses for same-path, symlink and hard-link aliases; controlled fault injection for encoding, partial writes, close and replacement; and a separate post-commit stderr failure. Verify old output and input hashes on every pre-commit failure.

### F11 — High: package isolation and identity repair are scheduled too late

**Affected issues:** 1–3, 5–14, 16. **Blocks:** installed-wheel milestone claims; undeclared configuration dependencies must be resolved before centralizing configuration imports.

**Evidence and failure scenario.** `config.py` imports `yaml` unconditionally, but core dependencies are empty. The recorded baseline requirements explicitly install PyYAML, masking the omission. The Google extra omits the PyMuPDF dependency that changes page-count and sync/batch routing. The `all` bundle omits Marker and the explicitly declared Unstructured `pikepdf` dependency. external-review-packet external-review-packet external-review-packet external-review-packet

Moving the configuration loader into the main API without fixing metadata would turn a currently localized dependency defect into a core-import defect.

Also, `uv run --extra …` defaults to an editable project installation. Separate requested extras do not automatically isolate lock resolution: uv resolves optional dependencies together unless conflicts are declared. [Astral Docs](https://docs.astral.sh/uv/concepts/projects/config/)

**Required change.** Move development identity, a minimal wheel-building harness and core-only dependency tests to the beginning. Decide whether PyYAML is a declared core dependency or explicitly optional. Make page-limit/routing behavior independent of unrelated installed packages; remove file-size page estimates as enforcement of advertised page limits.

Use clean wheel-target subprocesses with only the declared extra and its dependencies. Keep fixture generation and the richer test-runner environment separate where they could mask dependencies. Check advertised bundles as bundles, and narrow unsupported dependency/Python ranges or declare conflicts.

Update `tests/test_api.py::test_version`: its three-numeric-components assertion rejects `0.3.0.dev0`. Test PEP 440 validity and agreement among wheel metadata, module and CLI. external-review-packet

**Exposing test.** Build once, verify wheel/source hashes, install outside the checkout without user site or project configuration, and run core-only and each-extra probes. Exercise Google routing with and without unrelated PyMuPDF installation. Verify module paths and versions so an editable checkout cannot satisfy the test accidentally.

### F12 — Medium: several existing tests preserve defects or fail for unrelated reasons

**Affected issues:** 1, 3–5, 9–16. **Blocks:** evidentiary closure of the owning milestone, not implementation.

**Evidence and failure scenario.** The recorded 89-pass baseline excludes backend and commercial test files. Existing tests use `known_options=["ocr"]`, while Docling actually uses `do_ocr`; accept arbitrary boolean strings as false; assert that LlamaParse does not receive its mode; and accept absent Databricks data as empty output. Google’s old 20-page rejection test conflicts with the inherited batch route. Its mocked-size test uses invalid PDF bytes, so a real PDF reader can fail before the intended size branch. external-review-packet external-review-packet(1) external-review-packet(1) external-review-packet

**Required change.** Give each consequential defect one traceable chain: reachable input, actual producing branch, expected failure, repair and passing result. Update existing tests alongside new provider tests. Use strict, reason-specific expected failures and remove them in the owning repair.

Actual SDK transports and typed responses are appropriate offline evidence for serialization, response decoding and wrapper behavior. They still need independent official-contract fixtures and assertions on outgoing requests. They do not establish authentication, workspace permissions, service availability or real document processing.

**Exposing test.** Run each regression on preserved and repaired source. Verify that the old failure is the intended defect—not missing dependencies, an earlier corrupt-input error or a nonexistent new method. Require selected integration tests to execute rather than treating skips as passes.

## Issue order and simplifications

**Resolve the shared contracts, then let independent backend work proceed.** Keep the existing issue IDs for ownership, but use this execution order:

`Issue 1 + test safety + development identity → Issues 2–3 → Issue 4 → Issue 15`, with Issues 5–14 proceeding independently after the relevant shared contracts stabilize.

Clarify Issue 4’s CLI acceptance. Its configurable installed-package exercise precedes Issue 15, which introduces CLI configuration. Either Issue 4 covers API/async options plus **default CLI behavior**, leaving CLI option parity to Issue 15, or minimal CLI option support moves earlier. The current wording permits incompatible interpretations. external-review-packet external-review-packet

The plan does not need an architectural replacement. Use one option-normalization mechanism shared with constructors, static registry metadata, a small execution-policy layer for native runtimes, and one evidence matrix. Avoid maintaining separate authoritative schemas in the registry, API mappings, constructors and inventory.

Replace the repeated “Premises,” “Claims” and “Closes” blocks with compact issue acceptance tables linking defects to tests and evidence. Retain per-backend ownership without requiring a separate elaborate reporting framework for every issue.

Also reconcile completion language: Issues 7–8 can finish an **assessment** with a reproduced blocker, but that backend’s verification remains open. An environment failure must not become a completed integration merely because its cause was documented. external-review-packet external-review-packet external-review-packet

## Unresolved author decisions

| Decision | Concrete alternatives and consequences |
|---|---|
| **No-option `get_backend()` configuration lifetime** | Freeze effective configuration when the reusable instance is first created, with an explicit recreation mechanism; or keep `get_backend()` reuse while making convenience `parse()` calls fresh. Rereading environment/configuration into an existing shared instance risks contamination. |
| **Keyword compatibility** | Preserve both released `pdf_path=` and inherited `input_path=` with a documented conflict error; or restore only the released keyword and explicitly retire the inherited alias. Preserving both has little implementation cost. |
| **LlamaParse no-option behavior** | Choose a documented default tier and pinned service version under the existing backend name; or require explicit settings through a reviewed breaking migration. Neither preserves unmeasured historical service behavior automatically. |
| **Cleanup failure after successful extraction** | Raise an exception carrying `parse_completed=True` and resource identifiers, best matching the strict failure wording; or return text with a mandatory observable cleanup warning. The latter preserves useful output but must be described as extraction success with an operational failure. |
| **Configuration-file precedence** | Merge user and project files per key, matching the stated layered contract; or retain project-file shadowing and document it. Nested option replacement versus recursive merging must also be explicit. |
| **Unsupported dependency/platform combinations** | Repair and test them, or retain the integration with a precise blocked/unsupported status. Changing Python bounds or bundle contents needs an explicit support decision; documenting a failed installation is not verification. |

None of these requires authorization for paid calls or PDF-Bench experiments.

## Missing evidence and unsupported claims

**Missing evidence.** The packet does not contain installed-SDK contract results for the eight services, model/native execution results for nine local integrations, or the current installed LlamaParse SDK inspection needed to justify the exact replacement. These are expected deliverables of the owning issues, not reasons to block the two local baselines.

The text references source/raw-output archives and retained input PDFs that are not embedded in the attachment. I verified the included text hashes, but did not independently validate archive contents or reproduce the recorded baseline output hashes. Preserve the original archives, inherited diff, lockfile and README-branch evidence for implementation replay.

**Unsupported claims.** Historical pricing, “best quality,” accuracy rankings, resource estimates and model recommendations remain unsupported. Remove them from operational decisions and current capability copy. In particular, model acceptance must not depend on membership in a pricing dictionary; all three frontier constructors currently do that. Preserve useful usage reporting while distinguishing observed usage from estimates. external-review-packet external-review-packet external-review-packet

Do not add unsupported replacement claims during repair. For example, current OpenAI documentation supports PDF file inputs in Chat Completions; using that endpoint is not itself proof of an obsolete implementation. The request limits, model compatibility, completion handling and cleanup still require verification. [OpenAI Developers](https://developers.openai.com/api/docs/guides/file-inputs?utm_source=chatgpt.com)

**Optional future work.** PDF-Bench corpus/quality experiments, ParseBench reuse, comparative speed/cost evaluation, LiteParse, broader structured-result APIs and a general worker-management platform are outside the prerequisites for this repair. The necessary work is narrower: dependable invocation, effective configuration, correct failure handling, safe resource lifecycle and explicit evidence for every registered integration.
