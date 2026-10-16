"""Textract synchronous requests over isolated, individually validated PDF pages."""

import base64
import importlib.util
import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.backends._cleanup import close_client
from pdfsmith.backends._process import extract_in_process
from pdfsmith.config import Option, normalize_options

AVAILABLE = importlib.util.find_spec("boto3") is not None
MAX_PAGE_BYTES = 10_000_000


class AWSTextractBackend:
    name = "aws_textract"
    options_schema = {
        "region": Option("us-east-1", str),
        "profile": Option(None, str, allow_none=True),
        "request_timeout": Option(60.0, float, minimum=0.001),
    }

    def __init__(
        self, region: str | None = None, profile: str | None = None, **options: Any
    ) -> None:
        explicit = {
            **options,
            "region": region
            if region is not None
            else (
                os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            ),
            "profile": profile if profile is not None else os.getenv("AWS_PROFILE"),
        }
        self._options = normalize_options(self.name, explicit, self.options_schema)
        if not re.fullmatch(r"[a-z0-9-]+", self._options["region"]):
            raise ValueError("aws_textract.region must be an AWS region name")
        if (
            self._options["profile"] is not None
            and not self._options["profile"].strip()
        ):
            raise ValueError("aws_textract.profile must be nonempty")

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        import boto3
        from botocore.config import Config

        timeout = self._options["request_timeout"]
        return boto3.Session(
            profile_name=self._options["profile"], region_name=self._options["region"]
        ).client(
            "textract",
            config=Config(
                connect_timeout=min(10.0, timeout),
                read_timeout=timeout,
                retries={"max_attempts": 0, "mode": "standard"},
            ),
        )

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        count = pdf_page_count(path)
        client: Any = None
        content = None
        resources: dict[str, str] = {}
        try:
            parts = []
            for page in range(count):
                encoded = extract_in_process(
                    "_aws_page", path, {"page": page, "page_count": count}
                )
                data = base64.b64decode(encoded, validate=True)
                if (
                    not data.startswith(b"\x89PNG\r\n\x1a\n")
                    or len(data) > MAX_PAGE_BYTES
                ):
                    raise ValueError(
                        "AWS page must be PNG and at most 10,000,000 bytes"
                    )
                if client is None:
                    client = self._create_client()
                response = client.detect_document_text(Document={"Bytes": data})
                request_id = response.get("ResponseMetadata", {}).get("RequestId")
                if request_id:
                    resources[f"page_{page + 1}_request"] = request_id
                parts.extend(self._extract_blocks(response))
            content = "\n\n".join(parts).strip()
            return content
        except Exception as exc:
            if client is None:
                raise
            from botocore.exceptions import ClientError

            if isinstance(exc, ClientError) and exc.response.get("Error", {}).get(
                "Code"
            ) in {
                "InvalidParameterException",
                "BadDocumentException",
                "DocumentTooLargeException",
                "UnsupportedDocumentException",
            }:
                raise ValueError(f"Textract rejected the document: {exc}") from exc
            raise
        finally:
            if client is not None:
                close_client(
                    client,
                    self.name,
                    content=content,
                    resource_ids=resources,
                    primary=sys.exc_info()[1],
                )

    def _extract_blocks(self, response: dict[str, Any]) -> list[str]:
        metadata = response.get("DocumentMetadata", {})
        if type(metadata.get("Pages")) is not int or metadata["Pages"] != 1:
            raise RuntimeError("Textract did not confirm one complete rendered page")
        blocks = response.get("Blocks")
        if not isinstance(blocks, list):
            raise RuntimeError("Textract omitted page blocks")
        pages = [block for block in blocks if block.get("BlockType") == "PAGE"]
        if len(pages) != 1:
            raise RuntimeError("Textract returned incomplete page coverage")
        text = []
        for block in blocks:
            if block.get("BlockType") == "LINE":
                value = block.get("Text")
                if not isinstance(value, str):
                    raise RuntimeError("Textract omitted line text")
                if value.strip():
                    text.append(value.strip())
        return text
