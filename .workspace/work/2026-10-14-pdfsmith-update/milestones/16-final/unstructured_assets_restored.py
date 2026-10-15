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
assert config.exists()
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
cmd = [str(job / "env/bin/pdfsmith"), "parse", str(source), "--backend", "unstructured"]
p = subprocess.run(cmd, env=env, cwd=r, capture_output=True, timeout=180)
(m / "unstructured-restored-output.txt").write_bytes(p.stdout)
record = dict(
    command=cmd,
    exit=p.returncode,
    stderr=p.stderr.decode(),
    output_bytes=len(p.stdout),
    output_sha256=hashlib.sha256(p.stdout).hexdigest(),
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
assert p.returncode == 0 and b"Premera" in p.stdout and tap.read_bytes() == before
(config.parents[2] / "sitecustomize.py").unlink()
print(
    "Corrupt model rejected; model restored; actual CLI passed",
    len(p.stdout),
)
