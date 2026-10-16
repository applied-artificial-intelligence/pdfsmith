import hashlib
import json
import os
import subprocess
from pathlib import Path

w = Path(__file__).resolve().parents[2]
r = w / "runtime"
m = w / "milestones/16-final"
job = Path((r / "unstructured-assets-job.txt").read_text().strip())
python = job / "env/bin/python"
state = json.loads((job / "model-state.json").read_text())
config = Path(state["config"])
saved = Path(state["saved"])
assert saved.exists() and not config.exists()
wheel = r / "final-wheels/pdfsmith-0.3.0.dev0-py3-none-any.whl"
subprocess.run(
    [
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--reinstall",
        "--no-deps",
        str(wheel),
    ],
    check=True,
)
tap = job / "download-attempts.jsonl"
before = tap.read_bytes()
source = Path(
    "/home/stefan/agents/document-evidence/data/raw/AK_38344_38344AK1060001-01.pdf"
)
env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
env.update(
    HOME=str(r / "home"),
    TMPDIR=str(r / "tmp"),
    _PDFSMITH_TEST_OFFLINE="1",
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    OMP_NUM_THREADS="2",
)
cmd = [
    str(python),
    "-I",
    "-c",
    "from pdfsmith import parse;parse("
    + repr(str(source))
    + ',backend="unstructured")',
]
p = subprocess.run(cmd, env=env, cwd=r, capture_output=True, text=True, timeout=180)
record = dict(
    command=cmd,
    exit=p.returncode,
    stdout=p.stdout,
    stderr=p.stderr,
    new_download_attempts=tap.read_bytes() != before,
    wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
    input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
)
(m / "unstructured-corrupt-after.json").write_text(json.dumps(record, indent=2) + "\n")
assert (
    p.returncode != 0
    and "Repair the model installation" in p.stderr
    and tap.read_bytes() == before
)
saved.rename(config)
assert hashlib.sha256(config.read_bytes()).hexdigest() == state["sha256"]
cmd = [str(job / "env/bin/pdfsmith"), "parse", str(source), "--backend", "unstructured"]
restored = subprocess.run(cmd, env=env, cwd=r, capture_output=True, timeout=180)
(m / "unstructured-restored-output.txt").write_bytes(restored.stdout)
record = dict(
    command=cmd,
    exit=restored.returncode,
    stderr=restored.stderr.decode(),
    output_bytes=len(restored.stdout),
    output_sha256=hashlib.sha256(restored.stdout).hexdigest(),
    model_config_restored_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
    new_download_attempts=tap.read_bytes() != before,
    dependencies=subprocess.check_output(
        ["uv", "pip", "freeze", "--python", str(python)], text=True
    ),
    package_files={
        str(x.relative_to(config.parents[2])): hashlib.sha256(
            x.read_bytes()
        ).hexdigest()
        for x in sorted((config.parents[2] / "pdfsmith").rglob("*.py"))
    },
)
(m / "unstructured-restored.json").write_text(json.dumps(record, indent=2) + "\n")
assert (
    restored.returncode == 0
    and b"Premera" in restored.stdout
    and tap.read_bytes() == before
)
(config.parents[2] / "sitecustomize.py").unlink()
print(
    "Corrupt model rejected; model restored; actual CLI passed",
    len(restored.stdout),
)
