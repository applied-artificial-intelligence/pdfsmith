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
base = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
base.update(
    HOME=str(r / "home"),
    TMPDIR=str(r / "tmp"),
    PYTHONDONTWRITEBYTECODE="1",
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    OMP_NUM_THREADS="2",
)


def run(py):
    job = Path(tempfile.mkdtemp(prefix=f"final-ci-{py}-", dir=r))
    env = base.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(job / "env")
    install = ["uv", "sync", "--locked", "--no-editable", "--python", py]
    for extra in [
        "dev",
        "light",
        "pymupdf4llm",
        "pdfminer",
        "pypdfium2",
        "commercial",
        "frontier",
    ]:
        install += ["--extra", extra]
    p = subprocess.run(install, env=env, capture_output=True, text=True, timeout=600)
    (m / f"ci-{py}-install.txt").write_text(
        "Command: "
        + repr(install)
        + "\nExit: "
        + str(p.returncode)
        + "\n"
        + p.stdout
        + p.stderr
    )
    assert p.returncode == 0, p.stderr
    command = ["uv", "run", "--no-sync", "pytest", "-q", "--tb=short"]
    p = subprocess.run(command, env=env, capture_output=True, text=True, timeout=300)
    (m / f"ci-{py}-tests.txt").write_text(
        "Command: "
        + repr(command)
        + "\nExit: "
        + str(p.returncode)
        + "\n"
        + p.stdout
        + p.stderr
    )
    print(py, p.stdout[-1500:], flush=True)
    assert p.returncode == 0, p.stdout + p.stderr
    for command in [
        ["uv", "run", "--no-sync", "ruff", "check", "src", "tests"],
        ["uv", "run", "--no-sync", "ruff", "format", "--check", "src", "tests"],
        ["uv", "run", "--no-sync", "mypy", "src", "--ignore-missing-imports"],
    ]:
        p = subprocess.run(
            command, env=env, capture_output=True, text=True, timeout=120
        )
        (m / f"ci-{py}-{command[3]}-{command[4]}.txt").write_text(
            "Command: "
            + repr(command)
            + "\nExit: "
            + str(p.returncode)
            + "\n"
            + p.stdout
            + p.stderr
        )
        assert p.returncode == 0, p.stdout + p.stderr
    return str(job)


with ThreadPoolExecutor(max_workers=2) as pool:
    jobs = list(pool.map(run, ["3.10", "3.11", "3.12", "3.13"]))
(m / "ci-environments.json").write_text(json.dumps(jobs, indent=2) + "\n")
