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
job = Path(tempfile.mkdtemp(prefix="readme-example-", dir=r))
shutil.copytree(
    root / "src/pdfsmith",
    job / "src/pdfsmith",
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
)
for name in ["README.md", "pyproject.toml", "uv.lock", ".gitignore"]:
    shutil.copy2(root / name, job / name)
shutil.copy2(
    "/home/stefan/agents/document-evidence/data/raw/AK_38344_38344AK1060001-01.pdf",
    job / "document.pdf",
)
env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
env.update(HOME=str(r / "home"), TMPDIR=str(r / "tmp"), PYTHONDONTWRITEBYTECODE="1")
logs = []
for command in [
    ["uv", "venv", "--python", "3.12"],
    ["uv", "pip", "install", ".[pypdf,pdfplumber]"],
    ["uv", "run", "--no-project", "pdfsmith", "backends", "--all"],
]:
    p = subprocess.run(
        command, cwd=job, env=env, capture_output=True, text=True, timeout=180
    )
    logs.append(
        dict(command=command, exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
    )
    assert p.returncode == 0, p.stderr
code = (root / "README.md").read_text().split("```python\n", 1)[1].split("```", 1)[0]
p = subprocess.run(
    [str(job / ".venv/bin/python"), "-I", "-c", code],
    cwd=job,
    env=env,
    capture_output=True,
    text=True,
    timeout=60,
)
logs.append(
    dict(
        command="README Python example",
        code=code,
        exit=p.returncode,
        stdout=p.stdout,
        stderr=p.stderr,
    )
)
assert p.returncode == 0, p.stderr
(m / "readme-example.json").write_text(json.dumps(logs, indent=2) + "\n")
print("README installation and Python example passed in fresh source-copy environment")
