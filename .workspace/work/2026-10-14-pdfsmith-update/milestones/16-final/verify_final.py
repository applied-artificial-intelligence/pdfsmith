import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root = Path.cwd()
w = root / ".workspace/work/2026-10-14-pdfsmith-update"
r = w / "runtime"
m = w / "milestones/16-final"
wheel = r / "final-distributions/pdfsmith-0.3.0.dev0-py3-none-any.whl"
sdist = r / "final-distributions/pdfsmith-0.3.0.dev0.tar.gz"
base = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
base.update(
    HOME=str(r / "home"),
    TMPDIR=str(r / "tmp"),
    PYTHONDONTWRITEBYTECODE="1",
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    OMP_NUM_THREADS="2",
)
bundles = {
    "core": [],
    "light": ["pypdf", "pdfplumber", "pymupdf"],
    "recommended": ["pypdf", "pdfplumber", "pymupdf4llm", "kreuzberg"],
    "commercial": [
        "aws_textract",
        "azure_document_intelligence",
        "google_document_ai",
        "databricks",
        "llamaparse",
    ],
    "frontier": ["anthropic", "openai", "gemini"],
    "all": [
        "pypdf",
        "pdfplumber",
        "pymupdf",
        "pymupdf4llm",
        "pdfminer",
        "pypdfium2",
        "kreuzberg",
        "extractous",
        "docling",
        "unstructured",
    ],
}
source = "/home/stefan/agents/document-evidence/data/raw/AK_38344_38344AK1060001-01.pdf"


def check(job):
    py, bundle = job
    directory = Path(tempfile.mkdtemp(prefix=f"final-{bundle}-{py}-", dir=r))
    target = directory / "env"
    env = base.copy()
    env["VIRTUAL_ENV"] = str(target)
    subprocess.run(
        ["uv", "venv", "--python", py, str(target)],
        check=True,
        capture_output=True,
        env=env,
    )
    install = [
        "uv",
        "pip",
        "install",
        "--python",
        str(target / "bin/python"),
        str(wheel) + (f"[{bundle}]" if bundle != "core" else ""),
    ]
    p = subprocess.run(install, env=env, capture_output=True, text=True, timeout=600)
    (m / f"bundle-{bundle}-{py}-install.txt").write_text(p.stdout + p.stderr)
    assert p.returncode == 0, p.stderr
    expected = [
        x for x in bundles[bundle] if not (x == "unstructured" and py == "3.10")
    ]
    command = [
        str(target / "bin/python"),
        "-I",
        str(root / "tests/verify_distribution.py"),
        "--wheel",
        str(wheel),
        "--sdist",
        str(sdist),
        "--expected-backends",
        ",".join(expected),
        "--result",
        str(m / f"bundle-{bundle}-{py}.json"),
    ]
    if bundle != "core":
        command += ["--document", source]
    p = subprocess.run(
        command, env=env, cwd=directory, capture_output=True, text=True, timeout=180
    )
    (m / f"bundle-{bundle}-{py}-run.txt").write_text(
        "Install: "
        + repr(install)
        + "\nCommand: "
        + repr(command)
        + "\nExit: "
        + str(p.returncode)
        + "\n"
        + p.stdout
        + p.stderr
    )
    assert p.returncode == 0, p.stdout + p.stderr
    print(bundle, py, "installed distribution passed", flush=True)
    return str(directory)


with ThreadPoolExecutor(max_workers=2) as pool:
    directories = list(
        pool.map(
            check, [(p, b) for p in ["3.10", "3.11", "3.12", "3.13"] for b in bundles]
        )
    )
(m / "bundle-environments.json").write_text(json.dumps(directories, indent=2) + "\n")
