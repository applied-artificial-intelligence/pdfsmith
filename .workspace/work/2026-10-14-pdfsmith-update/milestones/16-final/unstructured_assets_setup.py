import json
import subprocess
import tempfile
from pathlib import Path

w = Path(__file__).resolve().parents[2]
r = w / "runtime"
m = w / "milestones/16-final"
m.mkdir(exist_ok=True)
job = Path(tempfile.mkdtemp(prefix="unstructured-assets-", dir=r))
env = job / "env"
subprocess.run(
    ["uv", "venv", "--python", "3.12", str(env)], check=True, capture_output=True
)
wheel = r / "gemini-wheels/pdfsmith-0.3.0.dev0-py3-none-any.whl"
commands = [
    [
        "uv",
        "pip",
        "install",
        "--python",
        str(env / "bin/python"),
        str(wheel) + "[unstructured]",
    ],
    [
        "uv",
        "pip",
        "install",
        "--python",
        str(env / "bin/python"),
        "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl#sha256=1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85",
    ],
]
logs = []
for command in commands:
    p = subprocess.run(command, capture_output=True, text=True, timeout=300)
    logs.append(
        {
            "command": command,
            "exit": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    )
    assert p.returncode == 0, p.stderr
(m / "unstructured-assets-install.json").write_text(json.dumps(logs, indent=2) + "\n")
(r / "unstructured-assets-job.txt").write_text(str(job) + "\n")
print(job)
