import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

w = Path(__file__).parent.parent
r = w / "runtime"
m = w / "milestones/09-ocr"
wheel = r / "ocr-wheels/pdfsmith-0.3.0.dev0-py3-none-any.whl"
env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG"}}
env.update(
    HOME=str(r / "home"),
    TMPDIR=str(r / "tmp"),
    _PDFSMITH_TEST_OFFLINE="1",
    AWS_EC2_METADATA_DISABLED="true",
    PYTHONDONTWRITEBYTECODE="1",
)


def run(item):
    py, backend, extra = item
    run_dir = Path(tempfile.mkdtemp(prefix=f"ocr-{extra}-{py}-", dir=r))
    target = run_dir / "env"
    subprocess.run(
        ["uv", "venv", "--python", py, str(target)],
        capture_output=True,
        check=True,
    )
    install = [
        "uv",
        "pip",
        "install",
        "--python",
        str(target / "bin/python"),
        str(wheel) + "[" + extra + "]",
    ]
    p = subprocess.run(install, capture_output=True, text=True, timeout=180)
    (m / f"install-{extra}-{py}.txt").write_text(p.stdout + p.stderr)
    assert p.returncode == 0, p.stderr
    output = run_dir / "outputs"
    cmd = [
        str(target / "bin/python"),
        "-I",
        str(w / "milestones/ocr_probe.py"),
        "--backend",
        backend,
        "--fixtures",
        str(r / "ocr-fixtures"),
        "--transport",
        str(w.parent.parent.parent / "tests/ocr_transport.py"),
        "--output",
        str(output),
    ]
    p = subprocess.run(cmd, env=env, cwd=r, capture_output=True, text=True, timeout=180)
    (m / f"run-{extra}-{py}.txt").write_text(
        (
            "Command: "
            + repr(cmd)
            + "\nExit: "
            + str(p.returncode)
            + "\n"
            + p.stdout
            + p.stderr
        ).rstrip()
        + "\n"
    )
    assert p.returncode == 0, p.stdout + p.stderr
    result = json.loads((output / "result.json").read_text())
    result.update(
        command=cmd,
        install_command=install,
        wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
    )
    (m / f"installed-{extra}-{py}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(extra, py, "offline installed contracts passed", flush=True)
    return output


items = [
    (py, backend, extra)
    for py in ["3.10", "3.11", "3.12", "3.13"]
    for backend, extra in [
        ("aws_textract", "aws"),
        ("azure_document_intelligence", "azure"),
    ]
]
with ThreadPoolExecutor(max_workers=2) as pool:
    outputs = list(pool.map(run, items))
with tarfile.open(m / "raw-outputs.tar.gz", "w:gz") as a:
    for (py, _backend, extra), output in zip(items, outputs, strict=False):
        a.add(output, arcname=f"{extra}-{py}")
    a.add(r / "ocr-fixtures", arcname="fixtures")
