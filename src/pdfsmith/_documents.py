"""Declared, local PDF page counting before any provider submission."""

from pathlib import Path


def pdf_page_count(path: Path) -> int:
    from pypdf import PdfReader

    with path.open("rb") as stream:
        document = PdfReader(stream)
        if document.is_encrypted and not document.decrypt(""):
            raise ValueError("Password-protected PDF is unsupported")
        count = len(document.pages)
        if count < 1:
            raise ValueError("Provider parsing requires at least one PDF page")
        return count
