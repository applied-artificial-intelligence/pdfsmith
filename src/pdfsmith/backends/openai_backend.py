"""OpenAI GPT backend for pdfsmith.

OpenAI's frontier multimodal models for PDF parsing using the Files API.

Requirements:
    - openai

Configuration:
    Set OPENAI_API_KEY environment variable.
    Get your key from: https://platform.openai.com/api-keys

Supported Models:
    - gpt-5.1: Latest flagship (~$1.25/1M input, $10/1M output)
    - gpt-4o: Multimodal model (~$2.50/1M input, $10/1M output)
    - gpt-4o-mini: Fast and cheap (~$0.15/1M input, $0.60/1M output)
    - gpt-4-turbo: Previous flagship (~$10/1M input, $30/1M output)
    - o1: Reasoning model (~$15/1M input, $60/1M output)
    - o1-mini: Cheaper reasoning (~$3/1M input, $12/1M output)

Limits:
    - Context window: 128K-1M tokens (model dependent)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    OpenAI = None  # type: ignore

try:
    import fitz  # PyMuPDF for page counting

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# Pricing per 1M tokens (verified November 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.1": {"input": 1.25, "output": 10.00},
    "gpt-5.1-chat-latest": {"input": 1.25, "output": 10.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
}

# Token estimates per page
TOKENS_PER_PAGE_INPUT = 1500
TOKENS_PER_PAGE_OUTPUT = 800

PDF_TO_MARKDOWN_PROMPT = """Convert this PDF document to clean Markdown.

Instructions:
1. Preserve the document structure (headings, paragraphs, lists)
2. Convert tables to Markdown table format
3. Preserve any important formatting (bold, italic, code)
4. Extract text accurately, maintaining reading order
5. For multi-column layouts, merge into single-column reading order
6. Include figure/image captions as descriptive text
7. Do not add any commentary or explanations - just output the converted content

Output only the Markdown content, nothing else."""


class OpenAIBackend:
    """PDF parser using OpenAI's GPT multimodal models."""

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI backend.

        Args:
            model: GPT model to use. Options:
                - "gpt-5.1": Latest flagship model
                - "gpt-4o": Multimodal model (recommended for accuracy)
                - "gpt-4o-mini": Fast and cheap (recommended for benchmarking)
                - "o1": Reasoning model (expensive)
            **kwargs: Additional options (ignored for compatibility)

        Raises:
            ImportError: If openai is not installed
            ValueError: If API key not set or invalid model
        """
        if not AVAILABLE:
            raise ImportError(
                "openai is required. "
                "Install with: pip install pdfsmith[openai]"
            )

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable must be set. "
                "Get your key from https://platform.openai.com/api-keys"
            )

        if model not in MODEL_PRICING:
            raise ValueError(
                f"Invalid model '{model}'. "
                f"Available models: {list(MODEL_PRICING.keys())}"
            )

        self.model = model
        self.pricing = MODEL_PRICING[model]
        self.client = OpenAI(api_key=self.api_key)

        # Cost tracking
        self.last_parsing_cost = 0.0
        self.total_cost = 0.0
        self.pages_processed = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using OpenAI GPT.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If OpenAI API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Get page count
        page_count = self._get_page_count(pdf_path)

        try:
            # Upload PDF file
            with open(pdf_path, "rb") as f:
                file = self.client.files.create(file=f, purpose="user_data")

            # Call API with PDF file reference
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "file",
                                "file": {"file_id": file.id},
                            },
                            {
                                "type": "text",
                                "text": PDF_TO_MARKDOWN_PROMPT,
                            },
                        ],
                    }
                ],
            )

            # Extract markdown from response
            markdown = response.choices[0].message.content or ""

            # Get token usage
            input_tokens = page_count * TOKENS_PER_PAGE_INPUT
            output_tokens = len(markdown) // 4

            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            # Clean up uploaded file (best effort)
            import contextlib
            with contextlib.suppress(Exception):
                self.client.files.delete(file.id)

        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

        # Track costs
        input_cost = (input_tokens / 1_000_000) * self.pricing["input"]
        output_cost = (output_tokens / 1_000_000) * self.pricing["output"]
        cost = input_cost + output_cost

        self.last_parsing_cost = cost
        self.total_cost += cost
        self.pages_processed += page_count
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        return markdown

    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count from PDF."""
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(pdf_path)
                count = len(doc)
                doc.close()
                return count
            except Exception:
                pass
        return max(1, pdf_path.stat().st_size // 75000)

    def get_cost_info(self) -> dict[str, Any]:
        """Get cost information for this backend.

        Returns:
            Dictionary with cost information
        """
        return {
            "backend": self.name,
            "model": self.model,
            "pricing": self.pricing,
            "last_parsing_cost": self.last_parsing_cost,
            "total_cost": self.total_cost,
            "pages_processed": self.pages_processed,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }
