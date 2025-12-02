"""Google Gemini backend for pdfsmith.

Google's frontier multimodal models for PDF parsing with native PDF vision.

Requirements:
    - google-genai

Configuration:
    Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
    Get your key from: https://aistudio.google.com/apikey

Supported Models:
    - gemini-3-pro-preview: Latest flagship (~$2/1M input, $12/1M output)
    - gemini-2.5-pro-preview-06-05: Previous pro (~$1.25/1M input, $10/1M output)
    - gemini-2.5-flash-preview-05-20: Fast, cheap (~$0.15/1M input, $0.60/1M output)
    - gemini-2.0-flash: Stable flash (~$0.10/1M input, $0.40/1M output)
    - gemini-1.5-pro: Legacy pro (~$1.25/1M input, $5/1M output)
    - gemini-1.5-flash: Legacy flash (~$0.075/1M input, $0.30/1M output)

Limits:
    - Max file size: 50MB
    - Max pages: 1000 pages per request
    - Context window: 1M tokens (for 2.5 Pro)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from google import genai
    from google.genai import types

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    genai = None  # type: ignore
    types = None  # type: ignore

try:
    import fitz  # PyMuPDF for page counting

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# Pricing per 1M tokens (verified November 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-3-pro-preview": {"input": 2.00, "output": 12.00},
    "gemini-3-pro-latest": {"input": 2.00, "output": 12.00},
    "gemini-2.5-pro-preview-06-05": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash-preview-05-20": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

# Token estimates per page
TOKENS_PER_PAGE_INPUT = 258  # Per Google docs
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


class GeminiBackend:
    """PDF parser using Google's Gemini multimodal models."""

    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        **kwargs: Any,
    ) -> None:
        """Initialize Gemini backend.

        Args:
            model: Gemini model to use. Options:
                - "gemini-3-pro-preview": Latest flagship (most accurate)
                - "gemini-2.5-flash-preview-05-20": Latest flash (fast, cheap)
                - "gemini-2.0-flash": Stable flash model (recommended)
                - "gemini-1.5-pro": Previous flagship
            **kwargs: Additional options (ignored for compatibility)

        Raises:
            ImportError: If google-genai is not installed
            ValueError: If API key not set or invalid model
        """
        if not AVAILABLE:
            raise ImportError(
                "google-genai is required. Install with: pip install pdfsmith[gemini]"
            )

        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY environment variable must be set. "
                "Get your key from https://aistudio.google.com/apikey"
            )

        if model not in MODEL_PRICING:
            raise ValueError(
                f"Invalid model '{model}'. "
                f"Available models: {list(MODEL_PRICING.keys())}"
            )

        self.model = model
        self.pricing = MODEL_PRICING[model]
        self.client = genai.Client(api_key=self.api_key)

        # Cost tracking
        self.last_parsing_cost = 0.0
        self.total_cost = 0.0
        self.pages_processed = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using Gemini vision.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF exceeds limits
            RuntimeError: If Gemini API call fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Check file size (50MB limit)
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 50:
            raise ValueError(f"PDF file too large ({file_size_mb:.1f}MB). Max: 50MB")

        # Get page count
        page_count = self._get_page_count(pdf_path)
        if page_count > 1000:
            raise ValueError(f"PDF has {page_count} pages. Max: 1000 pages")

        try:
            # Read PDF bytes
            pdf_data = pdf_path.read_bytes()

            # Call Gemini API with PDF
            pdf_part = types.Part.from_bytes(
                data=pdf_data,
                mime_type="application/pdf",
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=[pdf_part, PDF_TO_MARKDOWN_PROMPT],  # type: ignore[arg-type]
            )

            # Extract markdown from response
            markdown = response.text or ""

            # Get token usage if available
            input_tokens = page_count * TOKENS_PER_PAGE_INPUT
            output_tokens = len(markdown) // 4

            if response.usage_metadata is not None:
                usage = response.usage_metadata
                if hasattr(usage, "prompt_token_count") and usage.prompt_token_count:
                    input_tokens = int(usage.prompt_token_count)
                candidates_count = getattr(usage, "candidates_token_count", None)
                if candidates_count is not None:
                    output_tokens = int(candidates_count)

        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

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
