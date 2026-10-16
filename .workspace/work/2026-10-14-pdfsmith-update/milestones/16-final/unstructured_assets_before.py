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
site = Path(
    subprocess.check_output(
        [
            str(python),
            "-I",
            "-c",
            'import sysconfig;print(sysconfig.get_paths()["purelib"])',
        ],
        text=True,
    ).strip()
)
cfg = list((site / "en_core_web_sm").rglob("config.cfg"))
assert len(cfg) == 1
config = cfg[0]
saved = config.with_name("config.cfg.held-original")
assert not saved.exists()
config.rename(saved)
(job / "model-state.json").write_text(
    json.dumps(
        {
            "config": str(config),
            "saved": str(saved),
            "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
        },
        indent=2,
    )
    + "\n"
)
hook = site / "sitecustomize.py"
assert not hook.exists()
tap = job / "download-attempts.jsonl"
hook.write_text(
    "import socket, urllib.request, json\n"
    "from pathlib import Path\n"
    "def denied(*a, **kw):\n"
    '    raise RuntimeError("Network disabled for asset audit")\n'
    "socket.socket.connect = denied\n"
    "socket.getaddrinfo = denied\n"
    "def blocked(url, *a, **kw):\n"
    f"    p = Path({str(tap)!r})\n"
    '    with p.open("a") as f:\n'
    '        f.write(json.dumps({"url": str(url)}) + "\\n")\n'
    '    raise RuntimeError("Controlled implicit model download prevented")\n'
    "urllib.request.urlopen = blocked\n"
)
source = "/home/stefan/agents/document-evidence/data/raw/AK_38344_38344AK1060001-01.pdf"
cmd = [
    str(python),
    "-I",
    "-c",
    "from pdfsmith import parse;parse(" + repr(source) + ',backend="unstructured")',
]
env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
env.update(
    HOME=str(r / "home"),
    TMPDIR=str(r / "tmp"),
    _PDFSMITH_TEST_OFFLINE="1",
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    OMP_NUM_THREADS="2",
)
p = subprocess.run(cmd, env=env, cwd=r, capture_output=True, text=True, timeout=180)
record = dict(
    command=cmd,
    exit=p.returncode,
    stdout=p.stdout,
    stderr=p.stderr,
    input_path=source,
    input_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
    model_config_sha256=hashlib.sha256(saved.read_bytes()).hexdigest(),
    download_attempts=[json.loads(x) for x in tap.read_text().splitlines()]
    if tap.exists()
    else [],
)
(m / "unstructured-corrupt-before.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
assert p.returncode != 0 and record["download_attempts"]
