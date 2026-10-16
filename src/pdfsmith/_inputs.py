"""Cheap local input checks shared by public and direct backend entry points."""

from pathlib import Path


def validate_input(path: str | Path, formats: tuple[str, ...] = ("pdf",)) -> Path:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Input file not found: {target}")
    if not target.is_file():
        raise ValueError(f"Input must be a regular file: {target}")
    suffix = target.suffix.lower().lstrip(".")
    if suffix not in formats:
        raise ValueError(
            f"Input format '{suffix}' is not supported; supported: {formats}"
        )
    with target.open("rb") as stream:
        header = stream.read(1024)
    if suffix == "pdf" and b"%PDF-" not in header:
        raise ValueError(f"Input does not contain a PDF header: {target}")
    return target
