# Spec: Update and verify every registered PDFsmith integration

Alignment brief: `start-here.txt`, commissioned by Stefan on October 14, 2026.
Stefan selected "Verify every registered backend now" in the alignment reply and
requested consideration of LlamaIndex's ParseBench announcement. This replaces
the proposed baseline-only scope. This specification describes the required end
state. GPT and Claude reports were returned on October 15, 2026 and reconciled
in reviews/dispositions.txt. Shared design decisions below resolve their planning
blockers; affected integrations still need their prescribed runtime evidence.

## Objective

A caller can install, discover, configure and invoke PDFsmith's registered
parsers through a dependable Python API and CLI, identify failures and empty
output, and inspect exactly which integrations have fresh end-to-end evidence.

## Terms

Context: pdfsmith, document-parsing-library

| Term | Readings | Status | Basis |
|---|---|---|---|
| Backend scope | Two local baselines only; or every currently registered integration | resolved-by-author | Stefan selected verification of every registered backend. All 19 names in the inherited registry are in scope, including LlamaParse. |
| Verified integration | Import or mock test passes; or installed package parses an identified document through the actual integration | resolved-by-author | The brief requires fresh end-to-end runs and explicitly says mocked provider tests do not establish a working paid integration. |
| Available | Registered; dependencies installed; configured; or proven to work on a document | resolved-by-author | The brief requires discovery versus actual availability to be addressed. These states must remain distinguishable; dependency detection cannot assert service readiness. |
| Default selection | A document-specific best-parser decision; or a fixed preference order | resolved-by-author | The brief and public capability packet require truthful fixed-order selection, without parser-quality inference. |
| Failure | Every empty output; or an exception, rejected input/configuration, or provider-declared unsuccessful/incomplete operation | resolved-by-author | The brief requires failure and partial/empty output handling. A valid blank PDF may return an empty string; it must be recorded as empty, not as recovered content. |
| Version identity | Module string alone; or distribution, module, source and backend identities together | resolved-by-author | The brief explicitly requires investigation of pyproject/module disagreement and exact milestone identities. |
| Completion | Plan or passing mocks; or reviewed implementation with declared evidence and unresolved live-service gates visible | resolved-by-author | The brief requires engineering milestones after actual GPT and Claude reviews and separately prohibits unauthorized paid calls. |

## Why

PDF-Bench needs pypdf and pdfplumber on identical inputs, controlled options and
accurate implementation identity. Application callers also need the other
registered integrations to have honest installation and operating contracts.
The old public API, inherited API proposal and working provider changes currently
describe different behavior. A wrapper that accepts an option but ignores it can
invalidate a consumer's experiment without producing an obvious exception.

LlamaParse is an active dependency, and its current API needs assessment rather
than assuming the old wrapper still expresses current service settings.
ParseBench is relevant prior work on document evaluation. Its findings do not
establish the behavior or quality of a PDFsmith integration.

## Reviewed contract and acceptance criteria

1. Preserve the original review packet and source archives. Retain returned report
   bytes/hashes, GPT/Claude attribution supplied by Stefan, and dispositions. No
   specific reviewer model version was supplied. A resolved design finding is not
   a claim that its implementation or runtime verification has passed.
2. All 19 names remain in one evidence matrix. Record independent evidence states:
   registered, dependency-present, constructible, offline-contract, local-e2e and
   live-e2e. These are observations, not a total ordering or readiness guarantee.
   find_spec/metadata detection is dependency presence, not proven importability.
   Configuration discovery lists required variable names; values are not read and
   configuration status is not-checked. Per-integration Python bounds are explicit
   registry metadata; default selection excludes an unsupported runtime and direct
   requests fail with the required range. Missing runs and skips never count as passes.
3. Discovery reads static metadata and top-level dependency information without
   loading backend wrappers, SDKs or models or changing process environment. Keep
   the released available_backends() local preference order and add a full
   registered_backends() inventory. Actual loading can report installed-but-broken
   dependencies separately. Default selection stays in its released local order.
4. Constructors bind validated backend-specific options. They perform no credential
   resolution, client creation, model acquisition or network calls. parse(path)
   checks existence, regular-file identity, supported type and cheap signature
   consistency before expensive initialization. Structural corruption can require
   parsing; no generic magic-byte check promises to detect all corruption.
5. API calls and direct loader()->class(**options)->parse(path) calls use the same
   constructor schemas. parse()/parse_async() return str, preserve pdf_path= and
   accept inherited input_path= as an alias; supplying both is an error. No-option
   get_backend() returns a locked reusable instance whose effective configuration
   freezes at first construction. Explicit backend_options, including {}, create a
   fresh instance; convenience parse calls always use fresh instances. Failed
   initialization is retryable and never installs a half-initialized cached object.
6. Retire the unreleased preset/ocr parameters and quality aliases. Preserve their
   historical bytes in the source archive, not as a misleading runtime interface.
   Callers use backend_options and per-backend documented keys. Unsupported kwargs
   fail, and no default/automatic/file/environment configuration may enable paid
   augmentation. Marker use_llm remains unsupported in this local-wrapper update.
7. Explicit constructor/API options override PDFSMITH-prefixed environment, then
   legacy backend-prefixed environment, project YAML, user YAML and defaults.
   Automatic file/environment loading is retained for the already released Docling
   contract only; other backends get explicit options until their owning schema
   documents additional sources. Project and user files merge by top-level key;
   nested values replace whole values and are deep-copied. Constructor None means
   omitted only for documented optional parameters; null on other keys is invalid.
   Strict bool strings are true/false/1/0/yes/no/on/off; invalid values raise.
   Numeric values reject bools and invalid ranges. Unknown option keys and unknown
   PDFSMITH_<backend>_ variables raise; unrelated provider credential variables are
   outside option scanning. Alias conflicts at equal precedence raise. Docling's
   documented OCR/THREADS/TABLE_STRUCTURE aliases normalize to canonical keys.
   Docling uses local Tesseract for OCR; its constructor schema defines language
   aliases and table modes. Image-asset generation options are rejected because
   the string result cannot deliver their assets.
   Effective options are normalized once, copied defensively and exposed without
   credentials. Constructors do not reread options after validation. Core import
   and pdfsmith.config import work without PyYAML; YAML use requires a declared
   optional extra and gives an actionable error if absent.
8. Every backend starts PDF-only. Images are added per actual wrapper and format
   after a real controlled-image run, including .tif/.tiff. No service image claim
   comes from an underlying provider's general capability. Unsupported formats and
   extension/signature mismatches fail before client initialization or upload.
9. Native execution policy covers direct sync and async entry points. PyMuPDF and
   PyMuPDF4LLM extraction/rendering run in spawned child processes, never competing
   worker threads. PDFium calls use one runtime-wide synchronization boundary;
   Docling/Marker native conversions are process-isolated. Cloud page counting
   uses a declared parser, not optional fitz or file-size estimates. Rust/Java/OCR
   wrappers get tested policy in their own milestone. Blocking imports/setup and
   extraction do not run on the async event loop. Sync async-backed wrappers work
   inside a running loop using a dedicated thread/loop. Cancellation does not
   pretend to kill threads or roll back remote work; the worker owns final cleanup.
10. Completion requires the backend's documented terminal-success predicates,
    expected result fields and declared page coverage/order. Explicit failure,
    refusal, token truncation, failed pages, missing expansions/shards and partial
    local conversions raise, even if some text exists. Valid complete blank content
    may return an empty string. Silent semantic omissions remain outside this
    library's guarantee. Offline transport evidence never establishes server-side
    authentication, workspace permissions or actual document processing.
11. Service requests are not retried after ambiguous non-idempotent submission.
    Known active jobs get bounded polling and best-effort cancellation. Do not
    delete resources still used by an operation whose terminal state is unknown;
    report operation/resource identifiers and residual uncertainty. Always close
    owned local handles. If parsing and cleanup both fail, preserve the parse error
    and attach cleanup diagnostics. Cleanup failure after extraction raises an
    operational exception carrying parse_completed=True, recovered content and
    resource identifiers; useful paid output is not lost or silently called clean.
12. CLI file output stages in the destination directory before parsing, rejects
    same-path/symlink/hard-link input aliases, encodes complete UTF-8 and closes the
    staged file before os.replace. Replace is the commit point. Pre-commit failure
    preserves input and prior destination bytes. Post-commit diagnostic failure
    cannot claim the output was rolled back. stdout is streaming and not atomic;
    shell redirection is outside this guarantee. stdout and file output emit the
    returned UTF-8 content exactly, without adding a newline; diagnostics use stderr.
    Completed content carried by an operational cleanup error is saved separately
    as a private pdfsmith-recovery-*.json file beside the requested output, or in
    the system temporary directory for stdout mode. Exit remains nonzero, the prior
    destination stays intact and stderr reports the recovery path and resource IDs.
    Recovery storage failure is reported separately; no successful save is claimed.
13. Ordinary pytest collection/execution cannot enable live tests via environment
    flags, including RUN_COMMERCIAL_TESTS=0/false/1. The test process denies outbound
    DNS/TCP connections, strips inherited credentials and uses controlled HOME.
    Offline SDK tests supply synthetic credentials and strict transports. Authorized
    live protocols are separate explicit commands tied to provider, input, options
    and spending authority; no such authority has been supplied.
14. Move one-source unpublished 0.3.0.dev0 identity and core-only installed-wheel
    tests to the first milestone. Module, distribution and CLI agree on PEP 440
    identity. Per-extra installed-wheel checks use fresh environments, no editable
    source, no fixture-generator/test packages masking dependencies. Test declared
    Python 3.10-3.13 core/baselines or narrow support from reproduced results.
    Unstructured 0.27.27 requires Python 3.11-3.13 and a preinstalled spaCy model.
    Keep its incompatible Pillow dependencies separate from Marker; the all bundle
    already excludes Marker. No optional extra silently grants unsupported runtime
    capability when its dependency marker excludes the SDK.
15. Each backend needs actual local E2E or separately authorized live E2E before a
    working-integration claim. Offline SDK checks are labeled offline-contract;
    documented SQL/API compatibility is labeled documentation-backed. Baseline local
    milestones can finish independently of other providers. An assessed upstream
    blocker leaves that integration open, with exact evidence and no passing claim.
16. Each milestone records source/wheel/backend identities, exact commands, fresh
    outcomes, input/output hashes and supported exclusions. Regressions fail on the
    actual producing defect with reachable input and pass after repair. Update tests
    that encoded old defects. Expected failures, if temporarily necessary, are
    reason-specific and strict. No broad skips or mocked success establish closure.
17. LlamaParse replacement is conditional on inspecting the installed legacy SDK's
    distributions/re-export, effective options, serialization, error-swallowing,
    endpoints, page-index base, polling/retry and cache controls. Use one SDK path
    under the existing name. V2 calls require explicit tier and pinned published
    service version, rejecting moving latest aliases and legacy parsing_mode with
    a migration message. disable_cache defaults true and is recorded in effective
    request identity; cache-hit status stays unknown unless confirmed. Requested
    and provider-confirmed version/tier remain distinct. The inspected llama-cloud
    2.18.x response exposes no resolved runtime version or cache-hit guarantee;
    confirmed_version/cache_hit stay unknown, and raw request-version echoes are
    recorded separately. Accept the SDK-published 2026-06-15, 2026-09-28 and
    2026-09-29 versions with fast/cost_effective/agentic/agentic_plus tiers; these
    versions support markdown on fast. Validate job/page status,
    coverage/order/duplicates, output expansions and tier/version compatibility.
18. Preserve original source/unrelated files and the earlier README correction.
    Keep PDF-Bench experiments, website/editorial changes, release/public-main
    merge, publication and deployment separately owned and unauthorized here.

## In scope

- All registered local backends: pypdf, pdfplumber, pymupdf, pymupdf4llm,
  pdfminer, pypdfium2, unstructured, kreuzberg, extractous, docling and marker.
- All registered service backends: aws_textract, azure_document_intelligence,
  google_document_ai, databricks, llamaparse, anthropic, openai and gemini.
- Python/CLI contracts, optional dependencies, configuration, resource management,
  supported PDF/image capabilities and evidence-based documentation corrections.
- Current LlamaParse API migration assessment, effective mode/tier and version
  controls, plus a dated account of ParseBench's relevance and ownership boundary.

## Out of scope

- PDF-Bench corpus/reference construction, experiments, scores and comparisons.
- Reimplementing ParseBench, claiming its scores as our results, universal quality
  rankings, provider-price tables or performance claims from successful execution.
- New parser integrations beyond the current registry without a separate scope
  decision. LiteParse is a follow-on candidate, not silently added here.
- Paid or free-credit service calls, public-main merge, package release, website
  writes, publication, scheduling and deployment without separate authorization.
- New chats, hidden agents and unrelated inherited-work cleanup that discards work.

## Constraints

- Work in this checkout and work unit. Secrets, `.env`, MCP settings, old prompts
  and credential files cannot enter review packets or Git checkpoints.
- This repository is PUBLIC, verified using `gh repo view`. Use scoped branches;
  branch pushes are allowed, public-main merge is not authorized.
- Use uv and repository checks. Isolate incompatible parser dependency stacks;
  an advertised bundle must resolve, or its compatibility limits must be explicit.
- Actual external reviews are a required dependency. A locally written review
  prompt or an internal self-review does not satisfy that dependency.
- Full live-service verification can remain blocked on Stefan's separate run
  authorization. It cannot be represented as complete offline verification.

## Environment / prior art

- Public main is `fe66170231dd580d9f919662ed3b89947f091763`, confirmed against
  `git ls-remote`; PyPI's current release is 0.2.0. The inherited module says 0.3.0
  while `pyproject.toml` says 0.2.0. `baseline/` records fresh installation evidence.
- Seven tracked modifications predate this work: module/API, four provider files
  and uv.lock. The December 14, 2025 API proposal matches the API modification
  chronology; provider modification timestamps are March 10, 2026. Authors are
  unknown from Git. These are preservation facts, not approved implementation.
- `CLAUDE.md` references `.claude/PROJECT_MAP.md`, generated November 2025.
  Its backend counts, quality claims and API line references are historical.
- Registry loaders and backend constructors already support PDF-Bench's direct
  adapter use. PDF-Bench's current reconstruction spec requires pypdf/pdfplumber
  first and independently owns caching, reference truth and attempt accounting.
- The existing README correction is remote branch
  `codex/public-capability-copy-2026-10-09`, commit
  `cb5094e6b2690b50da748bcea4875adaa8c74dfc`. Preserve and reconcile it rather
  than duplicating or overwriting that work.
- [ParseBench announcement](https://www.llamaindex.ai/blog/parsebench), published
  April 13, 2026, and [LlamaParse migration guide](https://developers.llamaindex.ai/llamaparse/parse/guides/migration-v1-to-v2/),
  checked for this plan. Benchmark claims remain attributed to their authors.

## Existing surface (must not break)

- Released Python string API, keyword compatibility, backend names and CLI syntax.
- PDF-Bench loader/constructor use and access to the backend `name` attribute.
- Existing useful inherited API/provider work, configuration files, historical
  review artifacts and the independent README correction branch.
- Historical evidence remains byte-for-byte historical. New results name their
  actual package, backend versions, options and inputs.

## Open questions

- Shared review contracts are resolved in reviews/dispositions.txt. Per-provider
  SDK facts and runtime regressions remain dependencies of their owning milestone,
  not unresolved user design questions or global implementation blockers.
- Live-service runs require Stefan's exact provider/configuration/input and spend
  authorization. Prepare concrete protocols after offline repair; no implicit use
  of existing credentials or free credits.
- Dependency/model/runtime incompatibilities must be reproduced per backend.
  This owner repairs them against current official APIs after review; an upstream
  or machine-only blocker gets exact evidence and a support exclusion, not a pass.
- Existing-work authorship is unknown. Preserve and hash the inherited bytes;
  review and attribute integration decisions without inventing author provenance.

## Next actions

No further planning approval is needed. Live-provider input/configuration/spending
authorization remains a separate decision once concrete offline protocols exist.
