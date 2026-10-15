import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

root = Path.cwd()
w = root / ".workspace/work/2026-10-14-pdfsmith-update"
r = w / "runtime"
m = w / "milestones/16-final"
job = Path(tempfile.mkdtemp(prefix="package-regression-", dir=r))
source = job / "source"
source.mkdir()
for name in ["src/pdfsmith", "tests"]:
    shutil.copytree(
        root / name,
        source / name,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
for name in ["pyproject.toml", "README.md", "uv.lock", ".gitignore"]:
    shutil.copy2(root / name, source / name)
(source / "private-note.txt").write_text(
    "SYNTHETIC-PACKAGING-CANARY-NOT-A-REAL-CREDENTIAL\n"
)
(source / ".env").write_text("SYNTHETIC_ONLY=packaging-canary\n")
(source / ".workspace").mkdir()
(source / ".workspace/private-input.txt").write_text("SYNTHETIC-PACKAGING-CANARY\n")
project = (source / "pyproject.toml").read_text()
(source / "pyproject.toml").write_text(
    project.replace('dynamic = ["version"]', 'version = "0.2.0"')
)
env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
env.update(HOME=str(r / "home"), TMPDIR=str(r / "tmp"), PYTHONDONTWRITEBYTECODE="1")
records = []
for phase in ["before", "after"]:
    if phase == "after":
        (source / "pyproject.toml").write_text(project)
    out = job / phase
    command = ["uv", "build", "--out-dir", str(out)]
    p = subprocess.run(
        command, cwd=source, env=env, capture_output=True, text=True, timeout=180
    )
    assert p.returncode == 0, p.stderr
    wheel = next(out.glob("*.whl"))
    sdist = next(out.glob("*.tar.gz"))
    venv = job / f"env-{phase}"
    subprocess.run(
        ["uv", "venv", "--python", "3.12", str(venv)],
        env=env,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["uv", "pip", "install", "--python", str(venv / "bin/python"), str(wheel)],
        env=env,
        capture_output=True,
        check=True,
    )
    command = [
        str(venv / "bin/python"),
        "-I",
        str(root / "tests/verify_distribution.py"),
        "--wheel",
        str(wheel),
        "--sdist",
        str(sdist),
        "--result",
        str(m / f"package-regression-{phase}.json"),
    ]
    p = subprocess.run(
        command, env=env, cwd=job, capture_output=True, text=True, timeout=120
    )
    records.append(
        dict(
            phase=phase,
            command=command,
            exit=p.returncode,
            stdout=p.stdout,
            stderr=p.stderr,
            wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
            sdist_sha256=hashlib.sha256(sdist.read_bytes()).hexdigest(),
        )
    )
    assert (
        (
            p.returncode != 0
            and "distribution.version == pdfsmith.__version__" in p.stderr
        )
        if phase == "before"
        else p.returncode == 0
    ), p.stdout + p.stderr
(m / "package-regression.json").write_text(json.dumps(records, indent=2) + "\n")
print("Version defect rejected; corrected package and canary exclusion passed")
