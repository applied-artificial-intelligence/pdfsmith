# Spec: Explain PDF parser capabilities and configuration tradeoffs

Stefan requested a documentation-based overview on October 16, 2026 and confirmed
"Yes, a repository guide first" after the scope playback. This is a separate
documentation work unit. The earlier implementation and its evidence remain intact.

## Objective

A developer can use one sourced repository guide to distinguish the capabilities,
configuration choices and operating requirements of PDFsmith's 19 registered
parsers, including when the underlying API offers more than PDFsmith exposes.

## Terms

Context: pdfsmith, parser-feature-documentation

| Term | Readings | Status | Basis |
|---|---|---|---|
| Feature support | Upstream documentation; PDFsmith exposure; exercised behavior | resolved-by-author | The confirmed scope distinguishes all three; upstream documentation alone never establishes a PDFsmith runtime pass. |
| Comparison | A feature comparison; or measured extraction-quality rankings | resolved-by-author | Stefan requested documentation research; the confirmed scope excludes benchmarks and quality rankings. |
| Repository guide | A reviewable repository document; or a published website article | resolved-by-author | Stefan selected "Yes, a repository guide first". Publication remains separate. |
| Parsing frequency | Scheduled ingestion and batch/throughput requirements; or measured parser speed | resolved-by-author | The confirmed guide covers operating requirements. Discuss workload implications without inventing speed measurements or adding a scheduler. |

## Why

Parser names and GitHub popularity do not establish whether an API supplies the
OCR, tables, geometry, structured output or operating model a workflow requires.
PDFsmith's string interface exposes only part of upstream functionality. The guide
should help internal evaluation and application work without expanding the library.

## Acceptance criteria

1. One tracked repository guide covers all 19 registry names, grouped for reading.
2. Every upstream feature row links to official documentation or the project's
   own repository. Sources have an explicit research date.
3. The guide compares text versus scans/OCR, table structure, reading order,
   geometry/provenance, output forms, configuration and local/hosted execution.
4. It explains document-workflow tradeoffs and recurring/batch work without
   claiming measured latency, accuracy, cost savings or a universal winner.
5. It distinguishes upstream features, PDFsmith's exposed subset, and actual
   verification evidence, with links to existing code and evidence.
6. OpenAI and Gemini's remaining live checks are recorded as waived by Stefan;
   prior billing failures remain historical facts, not successful processing.
   Databricks remains excluded from live execution. No provider calls occur.
7. Only owned documentation changes are committed. No library code, dependencies,
   benchmark results, website files, releases or deployment settings change.
8. Source coverage, local links and the final diff are checked without installing
   parsers or running extraction tests. Existing unrelated files remain untouched.

## In scope

- A practical explanation with compact comparison tables and source links.
- Existing integrations' upstream capability and PDFsmith configuration boundaries.
- Closing the paid verification work with the user's accepted evidence limitations.

## Out of scope

- Paid calls, top-ups, benchmarks, new features, expanded option schemas or backends.
- Website changes, public-main merge, release, deployment or a marketing campaign.
- Exhaustive API mirroring, legal advice, a maintained price catalog or model rankings.

## Constraints

- Single agent; use public documentation and existing source/evidence only.
- No credentials are needed for research. Preserve inherited untracked work.
- Describe vendor and project claims as documented capabilities, not independently
  measured quality. Unverified or version-dependent features stay qualified.
- A source page's missing feature is not proof that the upstream library lacks it.

## Environment / prior art

- `src/pdfsmith/backends/registry.py` registers 11 local and eight hosted adapters.
- `README.md` and adapter `options_schema` definitions describe exposed options.
- `.workspace/work/2026-10-14-pdfsmith-update/` holds reviewed engineering and
  separate local, real-SDK offline and scoped live execution evidence.
- `docs/` contains inherited untracked work and must not be absorbed into commits.
- The primary checkout is on `codex/pdfsmith-update-2026-10-14`; public main is
  unchanged. This guide can be reviewed on that branch without publication.

## Existing surface (must not break)

- Public API/CLI behavior, backend names, versions and dependency constraints.
- Historical review packets, raw execution receipts, cost records and their hashes.
- Unrelated files, credentials and the sibling PDF-Bench/website repositories.

## Open questions

None block this guide. Publication location and timing are deferred to Stefan;
the accepted deliverable is a repository document for review.
