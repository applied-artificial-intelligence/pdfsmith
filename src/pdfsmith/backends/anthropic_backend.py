"""Anthropic Claude backend for pdfsmith.

Claude's frontier multimodal models for PDF parsing with native PDF vision.

Requirements:
    - anthropic

Configuration:
    Set ANTHROPIC_API_KEY environment variable.
    Get your key from: https://console.anthropic.com/settings/keys

Supported Models:
    - claude-sonnet-4-5: Latest flagship (~$3/1M input, $15/1M output)
    - claude-haiku-4-5: Fast and cheap (~$1/1M input, $5/1M output)
    - claude-3-5-haiku: Previous haiku (~$0.80/1M input, $4/1M output)
    - claude-3-opus: Top-tier legacy (~$15/1M input, $75/1M output)

Limits:
    - Max file size: 32MB
    - Max pages: 100 pages per request
    - Context window: 200K tokens
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

try:
    import anthropic

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    anthropic = None  # type: ignore

try:
    import fitz  # PyMuPDF for page counting

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# Pricing per 1M tokens (verified November 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
}

# Model ID mappings
MODEL_IDS: dict[str, str] = {
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-haiku-4-5": "claude-haiku-4-5-20251015",
    "claude-3-5-haiku": "claude-3-5-haiku-latest",
    "claude-3-opus": "claude-3-opus-latest",
}

# Token estimates per page
TOKENS_PER_PAGE_INPUT = 2000
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


class AnthropicBackend:
    """PDF parser using Anthropic's Claude multimodal models."""

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-3-5-haiku",
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic backend.

        Args:
            model: Claude model to use. Options:
                - "claude-sonnet-4-5": Latest Sonnet (balanced performance)
                - "claude-3-5-haiku": Fast and cheap (recommended for benchmarking)
                - "claude-3-opus": Top-tier (most accurate, highest cost)
            **kwargs: Additional options (ignored for compatibility)

        Raises:
            ImportError: If anthropic is not installed
            ValueError: If API key not set or invalid model
        """
        if not AVAILABLE:
            raise ImportError(
                "anthropic is required. Install with: pip install pdfsmith[anthropic]"
            )

        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable must be set. "
                "Get your key from https://console.anthropic.com/settings/keys"
            )

        if model not in MODEL_PRICING:
            raise ValueError(
                f"Invalid model '{model}'. "
                f"Available models: {list(MODEL_PRICING.keys())}"
            )

        self.model = model
        self.model_id = MODEL_IDS.get(model, model)
        self.pricing = MODEL_PRICING[model]
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Cost tracking
        self.last_parsing_cost = 0.0
        self.total_cost = 0.0
        self.pages_processed = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using Claude.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF exceeds limits
            RuntimeError: If Anthropic API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Check file size (32MB limit)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 32:
            raise ValueError(f"PDF file too large ({file_size_mb:.1f}MB). Max: 32MB")

        # Get page count
        page_count = self._get_page_count(pdf_path)
        if page_count > 100:
            raise ValueError(f"PDF has {page_count} pages. Max: 100 pages")

        try:
            # Read and encode PDF as base64
            pdf_data = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")

            # Call API with PDF document
            message = self.client.messages.create(
                model=self.model_id,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data,
                                },
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
            markdown = ""
            for block in message.content:
                if hasattr(block, "text"):
                    markdown += block.text

            # Get token usage
            input_tokens = page_count * TOKENS_PER_PAGE_INPUT
            output_tokens = len(markdown) // 4

            if message.usage:
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens

        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}") from e

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
            "model_id": self.model_id,
            "pricing": self.pricing,
            "last_parsing_cost": self.last_parsing_cost,
            "total_cost": self.total_cost,
            "pages_processed": self.pages_processed,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }
