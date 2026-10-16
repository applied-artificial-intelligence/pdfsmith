# How PDF parsers differ

Documentation reviewed October 16, 2026. This guide covers the 19 parsers registered
in the PDFsmith development branch. It compares documented features and the subset
exposed by PDFsmith. It contains no new parsing runs or comparative quality scores.
Upstream documentation can describe features newer than the dependencies exercised
here; check the selected library version before relying on a particular option.

Choose a parser by the information the application needs to retain. A workflow
that searches report text can use a different output from one that validates invoice
line items or highlights the exact source of an answer. A single accuracy score
cannot establish whether the output contains the fields the application requires.

## Start with the required result

The candidates below follow from documented capabilities. They are starting points
for selection, not measured winners. Their official sources appear in the tables.

| Requirement | Candidates to examine | The distinction to check |
|---|---|---|
| Searchable text from digital PDFs | pypdf, PyMuPDF, pdfminer.six, PDFium | Is the existing text layer usable, and does the reading order match the document? |
| Inspect or tune extraction of digital tables | pdfplumber, PyMuPDF | Do you need rows, cells, coordinates and debugging, rather than text arranged to look like a table? |
| Structured document conversion on local infrastructure | Docling, Marker, PyMuPDF4LLM | Which outputs preserve headings, tables, equations, images and page information? Which models are required? |
| Scanned or multilingual material | OCR-capable local pipelines, or hosted document services | Check the actual OCR engine, language packs, model and handwriting support. A text extractor can read an existing OCR layer without being able to create one. |
| Forms, checkboxes and named business fields | Textract analysis APIs, Azure model families, Google processors | Is the required field schema available in the chosen operation/model? Plain OCR is a different operation. |
| Source highlighting or audit links | Native APIs and structured outputs that retain geometry | Are there word/cell/element boxes and page references? A Markdown string or page citation alone cannot provide exact highlighting. |
| Interpret charts or answer questions about documents | Vision-language APIs and specialized chart-capable pipelines | Do you need transcription, chart data, a description or an answer? These are different outputs. |

[pypdf's text-extraction explanation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
distinguishes digital PDFs, scans and scans with an existing OCR layer. For digital
documents, rasterizing every page and applying OCR can throw away useful font and
encoding information. For an image-only scan, text extraction needs an OCR stage.

## Local libraries for text and page inspection

These libraries expose PDF objects or text extraction without requiring a hosted
service. The table distinguishes upstream capabilities from this wrapper's output.

| Library / PDFsmith backend | Documented upstream capabilities and configuration | PDFsmith's current subset |
|---|---|---|
| **pypdf** / `pypdf` | Text extraction with plain or fixed-width layout modes, orientation filters and visitor callbacks for positioned fragments. It has no OCR engine. [Text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html). | Returns text; exposes `extraction_mode`. Visitor callbacks and detailed layout controls require the native API. [Adapter](src/pdfsmith/backends/pypdf_backend.py). |
| **pdfplumber** / `pdfplumber` | Character/word geometry, cropping, configurable table extraction and visual debugging. Table settings include line- and text-based strategies and explicit boundaries. No built-in OCR; the project identifies digital PDFs as its stronger fit. [Project documentation](https://github.com/jsvine/pdfplumber). | Returns extracted text with layout and text-tolerance controls. It does **not** call the native table extraction API or return table objects. [Adapter](src/pdfsmith/backends/pdfplumber_backend.py). |
| **PyMuPDF** / `pymupdf` | Words/blocks with coordinates, sorting, table detection and extraction. [Text and tables](https://pymupdf.readthedocs.io/en/latest/recipes-text.html). Its [OCR integration](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html) uses separately installed Tesseract. | Returns text with a `sort` option. Tables, geometry and OCR are available through upstream APIs, not this adapter's interface. [Adapter](src/pdfsmith/backends/pymupdf_backend.py). |
| **pdfminer.six** / `pdfminer` | Layout objects, font information and vertical/CJK text handling. [Features](https://pdfminersix.readthedocs.io/en/latest/). `LAParams` controls character/word/line grouping and text-box ordering. [Layout parameters](https://pdfminersix.readthedocs.io/en/latest/reference/composable.html). | Returns text with selected spacing and vertical-text controls. It does not return the upstream layout tree or expose every `LAParams` field. [Adapter](src/pdfsmith/backends/pdfminer_backend.py). |
| **pypdfium2** / `pypdfium2` | PDFium bindings for rendering, text extraction, bounded text regions and character geometry. The API explicitly distinguishes these operations from semantic layout analysis such as detecting paragraphs. [Python API](https://pypdfium2.readthedocs.io/en/stable/python_api.html). | Returns per-page text joined into a string; no adapter options. Rendering and character boxes require native API use. [Adapter](src/pdfsmith/backends/pypdfium2_backend.py). |
| **Extractous** / `extractous` | Text and metadata across document formats, stream extraction, optional XML output and Tesseract OCR configuration. Its Rust/native integration includes Apache Tika. [Project documentation](https://github.com/yobix-ai/extractous). | Reads the complete text stream; no OCR configuration or metadata result is exposed. This is a text interface, not a table/geometry interface. [Adapter](src/pdfsmith/backends/extractous_backend.py). |

## Local document-conversion pipelines

These pipelines add document structure, OCR or model-based processing. Their
configuration choices affect both the result and the runtime requirements.

| Library / PDFsmith backend | Documented upstream capabilities and configuration | PDFsmith's current subset |
|---|---|---|
| **PyMuPDF4LLM** / `pymupdf4llm` | Markdown, text and JSON outputs; multi-column processing, tables, image extraction, page chunks and OCR. JSON can retain element boxes and layout data. [Overview](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/). | Returns Markdown. Exposes selected layout, table, text/image and OCR controls, with mode-dependent combinations. OCR is off by default. Structured JSON/page chunks and image assets are not returned. [Adapter](src/pdfsmith/backends/pymupdf4llm_backend.py). |
| **Docling** / `docling` | A document object model with reading order, tables, layout, OCR and structured exports, including Markdown and lossless JSON. [Project documentation](https://github.com/docling-project/docling). OCR engines, table processing and optional picture/formula/chart enrichment are configured separately. [Pipeline options](https://docling-project.github.io/docling/reference/pipeline_options/). | Returns Markdown. Exposes selected OCR/language, table, device, thread and model-asset settings. It does not return `DoclingDocument`, geometry or enrichment assets. OCR defaults to off. [Adapter](src/pdfsmith/backends/docling_backend.py). |
| **Marker** / `marker` | Markdown, JSON, HTML and chunks, with tables, equations and extracted images. Configuration includes conversion mode, OCR policy, page selection and optional additional LLM processing. Current documentation describes local Surya inference servers and batch execution. [Project documentation](https://github.com/datalab-to/marker). | Returns Markdown; exposes OCR disabling, pagination and owned local-runtime settings. Additional `use_llm=True` processing is rejected. Local model inference can still run when `use_llm=False`. Separate model assets, binaries and a compatible environment are required. [Adapter](src/pdfsmith/backends/marker_backend.py). |
| **Unstructured** / `unstructured` | Returns typed document elements. PDF strategies include `fast`, `hi_res`, `ocr_only` and `auto`; table inference and image-block extraction have their own settings. Strategy changes can alter layout classification and reading order. [Partitioning documentation](https://docs.unstructured.io/open-source/core-functionality/partitioning). | Joins element text with heading markers. Exposes three strategies and optional page breaks; OCR is configured for Tesseract/English. Table HTML, element metadata and image assets are not returned. Selecting `hi_res` does not expose all upstream table features. [Adapter](src/pdfsmith/backends/unstructured_backend.py). |
| **Kreuzberg** / `kreuzberg` | Text, tables, metadata, OCR, multiple output forms, optional chunking and embeddings. [Features](https://docs.kreuzberg.dev/features/). OCR engines and language configuration differ. [OCR guide](https://docs.kreuzberg.dev/guides/ocr/). | Returns plain text or Markdown. Exposes forced OCR using Tesseract/English; otherwise OCR is disabled. Cache and LLM augmentation are disabled. Rich extraction results and other OCR engines are outside this adapter. [Adapter](src/pdfsmith/backends/kreuzberg_backend.py). |

Local execution still has deployment requirements. Docling's [model catalog](https://docling-project.github.io/docling/usage/model_catalog/)
identifies distinct model components. Marker has an inference-server lifecycle;
OCR pipelines can need language packs and rendering tools. Provisioning assets in
advance is different from assuming a first call will work without network access.

## Hosted document services

A provider name does not identify one parsing configuration. Operation, processor,
model, API version and tier determine which features are available.

| Service / PDFsmith backend | Documented upstream capabilities and configuration | PDFsmith's current subset |
|---|---|---|
| **Amazon Textract** / `aws_textract` | Analysis operations expose forms/key-value pairs, tables, queries, signatures and layout with relationships and geometry. Synchronous and asynchronous operations serve different workflows. [Document analysis](https://docs.aws.amazon.com/textract/latest/dg/how-it-works-analyzing.html). | Uses text detection on individually supplied pages and returns lines. Region/profile/timeout are configurable. It does not invoke table/form/layout analysis; calling this adapter does not access those Textract features. [Adapter](src/pdfsmith/backends/aws_textract_backend.py). |
| **Azure Document Intelligence** / `azure_document_intelligence` | Read OCR, Layout, specialized business-document models and custom models. Layout adds structure such as tables and selection marks; optional capabilities vary by model and API version. Structured responses include geometry. [Model overview](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/model-overview?view=doc-intel-4.0.0). | Exposes Read or Layout and returns content as text, or Markdown with Layout. It does not return native table/field/geometry objects or expose specialized invoice/custom models. The live check exercised Read. [Adapter](src/pdfsmith/backends/azure_document_intelligence_backend.py). |
| **Google Document AI** / `google_document_ai` | A family of processors: OCR, forms, specialized business fields and layout/chunking. Features, languages, versions, regions and page limits differ by processor. [Processor catalog](https://docs.cloud.google.com/document-ai/docs/processors-list). | Selects an existing processor/version, synchronous or GCS-backed batch mode, and returns document text. Entities, tables and chunks are not returned. The wrapper expects text and page coverage, not every processor's output schema. [Adapter](src/pdfsmith/backends/google_document_ai_backend.py). |
| **LlamaParse** / `llamaparse` | Versioned parsing tiers with different pipelines. [Tiers](https://developers.llamaindex.ai/llamaparse/parse/guides/tiers/). Structured items and granular boxes depend on output settings, tier and version. [Geometry](https://developers.llamaindex.ai/llamaparse/parse/features/layout-and-bounding-boxes/). Other options cover tables, image assets and prompts. [Configuration](https://developers.llamaindex.ai/llamaparse/parse/guides/configuring-parse/). | Exposes tier, published version, language, cache and waiting controls; returns text/Markdown. It does not expose the full items tree, granular boxes, image assets or arbitrary prompts. Only Fast was exercised live in this update. [Adapter](src/pdfsmith/backends/llamaparse_backend.py). |
| **Databricks** / `databricks` | `ai_parse_document` produces versioned structured elements including HTML tables, page references, boxes and optional figure descriptions. It operates within Databricks SQL/data workflows. [Function reference](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document). | Submits version 2.0 SQL, disables figure descriptions and flattens supported content to a string. No structured result or image persistence is exposed. Warehouse/runtime and AI-processing costs need separate attention. Live execution was excluded. [Adapter](src/pdfsmith/backends/databricks_backend.py). |

## General vision-language APIs

These APIs accept PDFs and can interpret their content. The prompt and selected
model define the requested result; PDFsmith requests document transcription to
Markdown. That task differs from asking a question or extracting a named schema.

| API / PDFsmith backend | Documented upstream capabilities and configuration | PDFsmith's current subset |
|---|---|---|
| **Anthropic Claude** / `anthropic` | PDF text and visual understanding for charts, tables, questions and conversion. Model/context and request limits apply; sending PDFs is distinct from retaining a parser's native geometry. [PDF support](https://platform.claude.com/docs/en/build-with-claude/pdf-support). | Sends a base64 PDF with a fixed transcription prompt; exposes model, output-token limit and timeout. Returns text, with usage accessible on the backend instance. This wrapper caps input at 100 pages even where another model/API configuration supports more. [Adapter](src/pdfsmith/backends/anthropic_backend.py). |
| **OpenAI** / `openai` | Vision-capable models receive extracted PDF text and page images. File input methods differ between Responses and Chat Completions; text plus images increases context usage. [Official OpenAI file-input documentation](https://developers.openai.com/api/docs/guides/file-inputs). | Uploads a PDF and uses Chat Completions with a fixed transcription prompt. Exposes model, output-token limit and timeout; returns text and retains instance usage. Responses-specific options and custom extraction schemas are not exposed. No successful live processing in this update. [Adapter](src/pdfsmith/backends/openai_backend.py). |
| **Google Gemini** / `gemini` | Native PDF visual understanding, transcription, questions and structured extraction; model context, file/page and output limits apply. [Document understanding](https://ai.google.dev/gemini-api/docs/document-processing). | Sends inline PDF bytes through `generate_content` with a fixed transcription prompt. Exposes model, output-token limit and timeout; returns text and retains instance usage. Custom prompts, response schemas and media-resolution controls are not exposed. No successful live processing in this update. [Adapter](src/pdfsmith/backends/gemini_backend.py). |

A generous input context does not guarantee that the output budget can hold a
complete transcription. Geometry, exact transcription, valid schema syntax and
correct field values are separate requirements. An apparently complete generation
can still omit or alter content; protocol-level completion checks cannot prove
semantic fidelity.

## Configuration choices worth preserving

For tables, record whether the result retains cell boundaries, merged cells,
headers and continuation across pages. A Markdown table, HTML table and native
cell grid provide different representations. For source highlighting, retain page
identity and coordinate conventions along with the text. Azure's [geometry documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/model-overview?view=doc-intel-4.0.0#bounding-box-and-polygon-coordinates)
and Databricks' [element schema](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document#understanding-elements)
illustrate why coordinate units cannot be assumed to match between providers.

Record OCR policy and language, layout/table mode, output format, model or processor
version and any prompt. These choices define the candidate being compared. The
complete current PDFsmith option lists and defaults live in the [README](README.md)
and each adapter's `options_schema`; this guide does not duplicate that reference.

For recurring ingestion, also record document identity and whether cached output
was reused. A parser invocation is not an ingestion scheduler. Local pipelines
need resource/concurrency planning; hosted jobs add submission, polling, service
quotas and retained-upload handling. Google's [processor-specific sync/batch limits](https://docs.cloud.google.com/document-ai/docs/processors-list)
and LlamaParse's [version/cache behavior](https://developers.llamaindex.ai/llamaparse/parse/guides/tiers/)
show why these operating choices belong alongside the parsing configuration.
This guide makes no throughput or cheapest-provider claim.

For deployment, check data movement, installed assets and the licenses of the code
and selected models. For example, Docling explicitly distinguishes its code license
from [individual model licenses](https://github.com/docling-project/docling#license).
Self-hosting and hosted-service terms are separate choices.

## What PDFsmith retains

PDFsmith supplies a common PDF-to-string API/CLI, selected validated options and
explicit operational failures. Every current adapter accepts PDFs only, even when
the upstream library supports other formats. Output may be plain text or
backend-produced Markdown; the interface does not normalize every parser into the
same semantic representation. Only Docling automatically loads layered option
files/environment settings; other adapters take explicit options plus their
documented provider configuration.

Use the native API when the application needs an upstream document tree, table
objects, confidence fields, geometry, image assets or options this wrapper does
not expose. There is no requirement to expand PDFsmith to cover every native API.

The [execution inventory](.workspace/work/2026-10-14-pdfsmith-update/backend-inventory.json)
records 11 local execution passes and five scoped hosted API/CLI passes. OpenAI
and Gemini have documentation and real-SDK offline checks; their live attempts
stopped at depleted balances and further live verification was waived. Databricks
was excluded from live execution. These limits describe this update's evidence,
not the upstream services' full capabilities or historical use.

For external quality evidence, [LlamaIndex's ParseBench announcement](https://www.llamaindex.ai/blog/parsebench)
separates tables, charts, content faithfulness, semantic formatting and visual
grounding. It is a vendor-authored evaluation with its own methods and settings.
Its results are not PDFsmith measurements and do not establish a universal parser
ranking for another workload.
