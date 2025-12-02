"""LlamaParse backend for pdfsmith.

LlamaParse is LlamaIndex's GenAI-native document parsing service using LLMs
to convert PDFs to markdown format optimized for RAG pipelines.

Requirements:
    - llama-parse

Configuration:
    Set LLAMA_CLOUD_API_KEY environment variable.
    Get your key from: https://cloud.llamaindex.ai/api-key

Pricing (credits per page):
    - fast: 1 credit = $0.001/page (no AI)
    - cost_effective: 3 credits = $0.003/page (default)
    - agentic: 10 credits = $0.01/page
    - premium: 90 credits = $0.09/page

Free tier: 1,000 pages/day, 7,000 pages/week
"""

import os
from pathlib import Path

try:
    from llama_parse import LlamaParse
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class LlamaParseBackend:
    """PDF parser using LlamaIndex's LlamaParse cloud service.

    LlamaParse uses LLMs for GenAI-native document understanding,
    providing excellent results for complex documents and tables.
    """

    name = "llamaparse"

    # Parsing modes with their costs per page
    PARSING_MODES = {
        "fast": 0.001,
        "cost_effective": 0.003,
        "agentic": 0.01,
        "premium": 0.09,
    }

    def __init__(
        self,
        parsing_mode: str = "cost_effective",
        language: str = "en",
    ) -> None:
        """Initialize LlamaParse backend.

        Args:
            parsing_mode: One of 'fast', 'cost_effective', 'agentic', 'premium'.
                Default is 'cost_effective' ($0.003/page).
            language: Document language code (default: 'en')

        Raises:
            ImportError: If llama-parse is not installed
            ValueError: If LLAMA_CLOUD_API_KEY is not set or invalid mode
        """
        if not AVAILABLE:
            raise ImportError(
                "llama-parse is required. "
                "Install with: pip install pdfsmith[llamaparse]"
            )

        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise ValueError(
                "LLAMA_CLOUD_API_KEY environment variable must be set. "
                "Get your key from https://cloud.llamaindex.ai/api-key"
            )

        if parsing_mode not in self.PARSING_MODES:
            raise ValueError(
                f"Invalid parsing_mode '{parsing_mode}'. "
                f"Must be one of: {list(self.PARSING_MODES.keys())}"
            )

        self.parsing_mode = parsing_mode
        self.language = language

        self.client = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            language=language,
            verbose=False,
        )

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using LlamaParse.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If LlamaParse API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            # LlamaParse returns list of Document objects
            documents = self.client.load_data(str(pdf_path))
        except Exception as e:
            raise RuntimeError(f"LlamaParse processing failed: {e}") from e

        # Combine document texts
        parts = []
        for doc in documents:
            if hasattr(doc, "text") and doc.text:
                parts.append(doc.text.strip())
            elif hasattr(doc, "content") and doc.content:
                parts.append(doc.content.strip())
            elif isinstance(doc, str):
                parts.append(doc.strip())

        return "\n\n".join(parts) if parts else ""
