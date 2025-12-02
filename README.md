# pdfsmith

> PDF to Markdown conversion with multiple backend support

[![PyPI version](https://badge.fury.io/py/pdfsmith.svg)](https://badge.fury.io/py/pdfsmith)
[![CI](https://github.com/applied-artificial-intelligence/pdfsmith/actions/workflows/ci.yaml/badge.svg)](https://github.com/applied-artificial-intelligence/pdfsmith/actions/workflows/ci.yaml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified interface to 19+ PDF parsing libraries including frontier LLMs. Pick the right tool for the job, or let pdfsmith choose for you.

## Why pdfsmith?

- **One API, many backends** - Switch between parsers without changing your code
- **Auto-selection** - Automatically uses the best available parser
- **Lightweight core** - Install only the backends you need
- **Battle-tested** - Wrappers refined through extensive benchmarking

## Installation

```bash
# Core package (no backends)
pip install pdfsmith

# With lightweight backends
pip install pdfsmith[light]

# Recommended stack (good balance of quality and speed)
pip install pdfsmith[recommended]

# All open-source backends
pip install pdfsmith[all]

# Frontier LLMs (GPT, Claude, Gemini)
pip install pdfsmith[frontier]

# Commercial cloud APIs
pip install pdfsmith[commercial]

# Specific backend
pip install pdfsmith[docling]
```

## Quick Start

```python
from pdfsmith import parse

# Auto-select best available backend
markdown = parse("document.pdf")

# Use a specific backend
markdown = parse("document.pdf", backend="docling")

# Check available backends
from pdfsmith import available_backends
for backend in available_backends():
    print(f"{backend.name}: {backend.description}")
```

## CLI Usage

```bash
# Parse PDF to stdout
pdfsmith parse document.pdf

# Parse to file
pdfsmith parse document.pdf -o output.md

# Use specific backend
pdfsmith parse document.pdf -b docling

# List available backends
pdfsmith backends
```

## Available Backends

### Open Source

| Backend | Weight | Best For |
|---------|--------|----------|
| `docling` | heavy | Highest quality, complex documents |
| `marker` | heavy | Academic papers, LaTeX content |
| `pymupdf4llm` | medium | Good balance of speed and quality |
| `kreuzberg` | medium | Fast extraction with OCR |
| `unstructured` | medium | Versatile document processing |
| `pdfplumber` | light | Tables and structured data |
| `pymupdf` | light | Fast general-purpose extraction |
| `pypdf` | light | Lightweight, pure Python |
| `pdfminer` | light | Mature, handles encodings well |
| `pypdfium2` | light | Chrome's PDF engine |
| `extractous` | medium | Rust-based extraction |

### Commercial Cloud APIs

| Backend | Provider | Cost | Best For |
|---------|----------|------|----------|
| `aws_textract` | AWS | $1.50/1k pages | High-accuracy OCR |
| `azure_document_intelligence` | Azure | $1.50/1k pages | Enterprise documents |
| `google_document_ai` | Google Cloud | $1.50/1k pages | Multi-language support |
| `databricks` | Databricks | ~$3/1k pages | SQL-based workflows |
| `llamaparse` | LlamaIndex | $0.003/page | Cost-effective API |

### Frontier LLMs

| Backend | Model | Cost | Best For |
|---------|-------|------|----------|
| `anthropic` | Claude Sonnet 4.5 | ~$0.04/page | High accuracy |
| `openai` | GPT-4o | ~$0.02/page | General purpose |
| `gemini` | Gemini 2.0 Flash | ~$0.001/page | Budget LLM option |

**Note**: Frontier LLM backends require API keys set via environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`).

### Choosing a Backend

- **Best quality**: `anthropic` or `openai` - Frontier LLM accuracy (highest cost)
- **Best value**: `llamaparse` - Near-LLM quality at 10x lower cost
- **Structure preservation**: `docling` - Deep learning, GPU recommended
- **Academic papers**: `marker` - Optimized for LaTeX/equations
- **Tables**: `pdfplumber` - Excellent table detection
- **Speed**: `pymupdf` or `kreuzberg` - Fast extraction
- **Minimal dependencies**: `pypdf` - Pure Python, no binaries
- **Budget LLM**: `gemini` with gemini-2.0-flash - Very low cost LLM option

### System Dependencies

Some backends require system packages for OCR functionality:

**Tesseract OCR** (for `kreuzberg` and `unstructured` with OCR):
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

Without tesseract, these backends will still work for text-based PDFs but cannot extract text from scanned/image PDFs.

## Async Support

```python
from pdfsmith import parse_async

# Async parsing (uses backend's native async if available)
markdown = await parse_async("document.pdf")
```

## Benchmarks

pdfsmith's backend wrappers were developed and refined through the [pdf-bench](https://github.com/applied-artificial-intelligence/pdf-bench) benchmarking project, which evaluates parser performance across diverse document types.

## License

MIT

## Contributing

Contributions welcome! Please read our contributing guidelines before submitting PRs.
