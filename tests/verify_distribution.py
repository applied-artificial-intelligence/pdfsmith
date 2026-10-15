"""Check installed distribution identity, console and baseline extraction."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import sysconfig
import tarfile
import zipfile
from pathlib import Path


def verify(
    wheel: Path, sdist: Path, document: Path | None, expected_backends: list[str]
) -> dict:
    import pdfsmith

    package = Path(pdfsmith.__file__).resolve()
    assert Path(sys.prefix).resolve() in package.parents, package
    distribution = importlib.metadata.distribution("pdfsmith")
    assert distribution.version == pdfsmith.__version__
    assert not any(
        ";" not in requirement for requirement in distribution.requires or []
    ), "Core acquired a mandatory runtime dependency"
    console = Path(sysconfig.get_path("scripts")) / "pdfsmith"
    version = subprocess.run(
        [str(console), "--version"], capture_output=True, text=True, check=True
    )
    assert version.stdout == f"pdfsmith {distribution.version}\n"
    inventory = subprocess.run(
        [str(console), "backends", "--all"],
        capture_output=True,
        text=True,
        check=True,
    )
    names = [info.name for info in pdfsmith.registered_backends()]
    assert len(names) == 19 and all(
        f"{name}: registered;" in inventory.stdout for name in names
    )
    for name in expected_backends:
        options = (
            {"tier": "fast", "version": "2026-09-29"} if name == "llamaparse" else {}
        )
        instance = pdfsmith.get_backend(name, backend_options=options)
        assert instance.name == name
    with zipfile.ZipFile(wheel) as archive:
        wheel_sources = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.startswith("pdfsmith/")
        }
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(*Path(member.name).parts[1:])
            assert path.parts and (
                path.parts[0] in {"src", "tests"}
                or path.as_posix()
                in {
                    ".gitignore",
                    "README.md",
                    "LICENSE",
                    "pyproject.toml",
                    "uv.lock",
                    "PKG-INFO",
                }
            ), f"Unexpected source-distribution member: {path}"
        source_bytes = {
            Path(*Path(member.name).parts[2:]).as_posix(): stream.read()
            for member in members
            if member.isfile() and Path(member.name).parts[1:3] == ("src", "pdfsmith")
            if (stream := archive.extractfile(member)) is not None
        }
    assert source_bytes == wheel_sources, "Wheel and source distribution code diverge"
    for name, content in wheel_sources.items():
        assert package.parent.joinpath(*Path(name).parts[1:]).read_bytes() == content
    result: dict[str, object] = {
        "python": sys.version,
        "version": distribution.version,
        "constructible_backends": expected_backends,
        "package_path": str(package),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "sdist_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        "package_sources": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(wheel_sources.items())
        },
        "dependencies": {
            item.metadata["Name"]: item.version
            for item in importlib.metadata.distributions()
        },
    }
    if document is not None:
        text = pdfsmith.parse(document, backend="pypdf")
        assert text.strip(), "Identified nonblank public input returned empty text"
        assert text == asyncio.run(pdfsmith.parse_async(document, backend="pypdf"))
        direct = pdfsmith.get_backend("pypdf", backend_options={})
        assert text == direct.parse(document)
        command = [str(console), "parse", str(document), "-b", "pypdf"]
        parsed = subprocess.run(command, capture_output=True, check=True)
        assert parsed.stdout == text.encode("utf-8")
        result["input_sha256"] = hashlib.sha256(document.read_bytes()).hexdigest()
        result["output_sha256"] = hashlib.sha256(parsed.stdout).hexdigest()
        result["output_bytes"] = len(parsed.stdout)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--expected-backends", default="")
    parser.add_argument("--result", required=True, type=Path)
    arguments = parser.parse_args()
    observed = verify(
        arguments.wheel,
        arguments.sdist,
        arguments.document,
        [name for name in arguments.expected_backends.split(",") if name],
    )
    arguments.result.write_text(json.dumps(observed, indent=2) + "\n")
    print(f"Installed distribution passed on Python {sys.version.split()[0]}")
