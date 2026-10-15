# Spec: Update and verify every registered PDFsmith integration

Alignment brief: `start-here.txt`, commissioned by Stefan on October 14, 2026.
Stefan selected "Verify every registered backend now" in the alignment reply and
requested consideration of LlamaIndex's ParseBench announcement. This replaces
the proposed baseline-only scope. This specification describes the required end
state; implementation requires the returned external reviews specified below.

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

## Acceptance criteria

1. A self-contained specification/implementation packet is reviewed externally
   by GPT and Claude. Retain the actual returned reports, their identities and
   hashes, and a disposition of consequential findings. No substantial source
   implementation starts before those findings are reconciled. Baseline diagnostic
   work is permitted by the brief.
2. Inventory public source, released distribution and inherited working tree
   separately, including source hashes and initial dirty state. Preserve all
   inherited files. Record known chronology separately from unknown authorship;
   do not absorb unrelated files into commits.
3. Account for all 19 existing registry names in one backend verification matrix.
   Each row identifies its install extra and SDK/runtime dependencies, input types,
   supported options, sync/async behavior, configuration, actual test evidence and
   retain/repair/replace disposition. No backend silently disappears or is called
   working solely because it is registered or imports.
4. Every local integration has a fresh isolated installed-package parse of an
   identified public PDF and controlled text/blank/corrupt fixtures, or an exact
   reproduced environment/upstream failure that prevents a support claim. A failure
   remains open engineering work, not a passing verification. Baseline parsers can
   finish their milestones independently of another backend's blocker.
5. Every service integration has current official-API verification, isolated SDK
   and request/response contract checks, missing-configuration and error-path
   checks, and a reproducible live-run protocol. Actual service verification needs
   separately authorized inputs, provider/configuration and spending. Until a real
   run occurs its status remains live-unverified, even if offline tests pass.
6. Preserve `parse(path, backend=...) -> str`, `parse_async(...) -> str`, released
   `pdf_path=` keyword use, backend identifiers, direct loader/constructor/parse
   usage needed by PDF-Bench, and existing CLI parse/output/backend commands.
   Retain no-option `get_backend()` instance reuse unless a reviewed compatibility
   migration explicitly supersedes it. New configuration cannot leak between calls.
7. Explicit selection never silently changes backend. Default selection is
   deterministic for a declared installed environment, stays local/unpaid, reports
   its selected name through the public selection surface, and does not claim
   quality ranking. An unavailable or broken selected integration cannot silently
   substitute a different parser after parsing begins.
8. Discovery distinguishes registry membership, dependency availability,
   configuration and successful parsing. Listing backends cannot initialize models,
   obtain credentials, invoke remote services or create provider resources.
   Installation guidance uses an extra that actually installs the integration.
9. Supported options reach the producing SDK/parser calls. Unknown options, wrong
   types, invalid presets and unsupported common options fail explicitly. Sync and
   async entry points apply the same validation and precedence. Regression evidence
   demonstrates an output-affecting option on a fixture that makes it observable.
   Advertised settings cannot be accepted without effect.
10. Local path/configuration errors occur before parser/model/client initialization
    or remote requests. Missing paths, directories, corrupt inputs, unsupported
    formats, unavailable integrations and invalid options have documented outcomes.
    Input files and existing output files remain unchanged when an operation fails.
11. Backend exceptions and provider-declared partial, failed or truncated responses
    cannot become apparently successful completed output. Valid empty content
    remains distinguishable from an exception, and empty-content evidence is
    reported separately from content recovery. PDFsmith does not guarantee detection
    of silent semantic omissions by an upstream parser.
12. CLI failure returns nonzero, keeps diagnostics on stderr, and preserves any
    previous output on parse, serialization or write failure. Successful file output
    is complete UTF-8 text. CLI options express the supported Python configuration
    contract, with invalid configuration rejected before processing.
13. Async parsing preserves content/errors and allows unrelated loop work to run
    during imports, initialization and blocking extraction. Document cancellation
    boundaries, including work in executor threads that cannot be forcibly stopped.
    Repeated/concurrent calls do not mix options or mutable result accounting.
14. Files, native documents, page handles, streams and temporary remote resources
    have defined cleanup on success and failure. Cleanup failure cannot conceal the
    original parse failure. Remote calls cannot be rolled back; any remaining
    artifacts or uncertain service completion must be reported honestly.
15. The unpublished development build has one consistent PEP 440 version across
    wheel metadata, module and CLI. Record the unchanged public/released 0.2.0
    identity separately. No package release or claim that old artifacts used the
    new implementation follows from this metadata repair.
16. Each completed engineering milestone includes scoped source/package identities,
    exact commands, fresh pass/fail results, backend dependency snapshots, input and
    output hashes, supported behaviors, exclusions and runnable API/CLI examples.
    Regression tests fail on actual reproduced producing-code defects and pass on
    repaired code. Existing failures and lint/type drift encountered are resolved
    within the reviewed scope rather than suppressed.
17. A final installed-wheel exercise runs outside this checkout using only declared
    extras. Core-only import, no-backend behavior and per-extra installation are
    tested. Supported Python/platform bounds reflect observed compatibility; no
    workstation-only model/cache state is silently required.
18. One concise website-editorial handoff supplies verified identities and claim
    boundaries. It does not change website, editorial, PDF-Bench or historical
    experiment files, and it cannot imply universal parser quality or production
    validation from smoke tests.

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

- External design reviews are not yet returned. Stefan supplies the reports; this
  owner resolves consequential findings before the affected implementation.
- Live-service runs require Stefan's exact provider/configuration/input and spend
  authorization. Prepare concrete protocols after offline repair; no implicit use
  of existing credentials or free credits.
- Dependency/model/runtime incompatibilities must be reproduced per backend.
  This owner repairs them against current official APIs after review; an upstream
  or machine-only blocker gets exact evidence and a support exclusion, not a pass.
- Existing-work authorship is unknown. Preserve and hash the inherited bytes;
  review and attribute integration decisions without inventing author provenance.

## Next actions

Stefan returns GPT and Claude reviews of the completed packet before substantial
implementation. Live-provider spending remains a separate later decision.
