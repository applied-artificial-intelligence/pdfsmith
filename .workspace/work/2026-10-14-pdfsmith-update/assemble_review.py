"""Assemble review evidence from an explicit artifact and source allowlist."""

import hashlib
import re
import tarfile
from pathlib import Path


def main() -> None:
    work = Path(__file__).resolve().parent
    files = [
        work / name
        for name in (
            "review-request.txt",
            "review-context.txt",
            "spec.md",
            "plan.md",
            "backend-inventory.json",
            "baseline_probe.py",
            "reproduce-baseline.sh",
        )
    ]
    files.extend(sorted((work / "baseline").glob("*.json")))
    files.extend(sorted((work / "baseline").glob("*-pytest.txt")))
    files.append(work / "baseline/requirements.txt")
    entries = [(str(p.relative_to(work)), p.read_bytes()) for p in files]
    with tarfile.open(work / "initial-source.tar.gz") as archive:
        for member in sorted(archive.getmembers(), key=lambda entry: entry.name):
            if not member.isfile():
                continue
            name = member.name
            selected = name.startswith("working-source/") and (
                name.endswith(".py") or name.endswith("pyproject.toml")
            )
            selected |= name in {
                "public-source/src/pdfsmith/api.py",
                "public-source/src/pdfsmith/__init__.py",
                "public-source/src/pdfsmith/backends/registry.py",
            }
            if selected:
                stream = archive.extractfile(member)
                assert stream is not None
                entries.append((name, stream.read()))
    patterns = [
        rb"llx-[A-Za-z0-9_-]{20,}",
        rb"sk-[A-Za-z0-9_-]{20,}",
        rb"AKIA[A-Z0-9]{16}",
        rb"AIza[A-Za-z0-9_-]{30,}",
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    parts = [
        "PDFsmith external design-review packet\n",
        "Proposed plan; no external review or implementation completion claimed.\n",
        "All source below is the preserved INITIAL state, not a proposed patch.\n",
        "Historical source comments/pricing/model lists are unvalidated evidence.\n",
        "Source and inherited patch: initial-source.tar.gz.\n",
        "Raw outputs: baseline/raw-outputs.tar.gz. Both have manifest hashes.\n\n",
    ]
    manifest = []
    for name, data in entries:
        assert not any(
            re.search(pattern, data) for pattern in patterns
        ), f"Possible secret in allowlisted file: {name}"
        digest = hashlib.sha256(data).hexdigest()
        manifest.append(f"{digest}  {name}\n")
        parts.extend(
            [
                f"BEGIN FILE {name} SHA256 {digest}\n",
                data.decode("utf-8"),
                f"\nEND FILE {name}\n\n",
            ]
        )
    (work / "external-review-packet.txt").write_text(
        "".join(parts).rstrip() + "\n", encoding="utf-8"
    )
    (work / "packet-contents.sha256").write_text("".join(manifest), encoding="utf-8")
    print(f"Assembled {len(entries)} files into external-review-packet.txt")


if __name__ == "__main__":
    main()
