#!/usr/bin/env bash
set -euo pipefail

work_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
document="${1:-/home/stefan/agents/document-evidence/data/raw/AK_38344_38344AK1060001-01.pdf}"
mkdir -p "$work_dir/runtime"
replay_dir="$(mktemp -d "$work_dir/runtime/replay-XXXXXX")"

python3 - "$work_dir" "$replay_dir" "$document" <<'PY'
from pathlib import Path
import hashlib, json, sys, tarfile, urllib.request
work, replay, document = map(Path, sys.argv[1:])
expected = 'd93b3432fee068291117ba8d057233c5e1e70a7415be3052f88ccb5204872e80'
assert hashlib.sha256(document.read_bytes()).hexdigest() == expected, 'Input differs'
with tarfile.open(work / 'initial-source.tar.gz') as archive:
    archive.extractall(replay, filter='data')
identity = json.loads((work / 'baseline/release-identity.json').read_text())
wheel = urllib.request.urlopen(identity['url'], timeout=60).read()
assert hashlib.sha256(wheel).hexdigest() == identity['sha256'], 'Wheel differs'
(replay / identity['filename']).write_bytes(wheel)
PY

for install_kind in public working release; do
  uv venv --python 3.12 "$replay_dir/$install_kind-env"
  package_path="$replay_dir/$install_kind-source"
  if [[ "$install_kind" == release ]]; then
    package_path="$replay_dir/pdfsmith-0.2.0-py3-none-any.whl"
  fi
  uv pip install --python "$replay_dir/$install_kind-env/bin/python" \
    "$package_path" -r "$work_dir/baseline/requirements.txt"
done

"$replay_dir/public-env/bin/python" - "$replay_dir" <<'PY'
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
fixtures = Path(sys.argv[1]) / 'fixtures'
fixtures.mkdir()
c = canvas.Canvas(str(fixtures / 'text.pdf'), invariant=1)
c.drawString(72, 720, 'PDFsmith controlled fixture')
c.drawString(72, 690, 'Invoice PS-1042 Total USD 123.45')
c.save()
c = canvas.Canvas(str(fixtures / 'blank.pdf'), invariant=1)
c.showPage()
c.save()
(fixtures / 'corrupt.pdf').write_bytes(b'%PDF-1.7\ncorrupt control\n')
PY

python3 - "$work_dir" "$replay_dir" "$document" <<'PY'
from pathlib import Path
import json, os, subprocess, sys
work, replay, document = map(Path, sys.argv[1:])
env = {k: v for k, v in os.environ.items()
       if k in {'PATH', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}}
(replay / 'home').mkdir()
env.update(HOME=str(replay / 'home'), PYTHONDONTWRITEBYTECODE='1')
for kind in ('public', 'working', 'release'):
    command = [str(replay / (kind + '-env') / 'bin/python'),
               str(work / 'baseline_probe.py'), '--document', str(document),
               '--fixtures', str(replay / 'fixtures'), '--output',
               str(replay / 'outputs' / kind), '--kind', kind]
    result = subprocess.run(command, cwd=replay, env=env, capture_output=True,
                            text=True, timeout=180, check=True)
    (replay / (kind + '-probe.log')).write_text(result.stdout + result.stderr)
    fresh = json.loads((replay / 'outputs' / kind / 'results.json').read_text())
    old = json.loads((work / 'baseline' / (kind + '.json')).read_text())
    assert fresh['module_hashes'] == old['module_hashes'], kind + ': implementation drift'
    def stable_checks(checks):
        return {k: {field: value for field, value in row.items() if field != 'message'}
                for k, row in checks.items()}
    assert stable_checks(fresh['checks']) == stable_checks(old['checks']), kind + ': behavior differs'
    for label, outcome in old['cli'].items():
        assert fresh['cli'][label]['returncode'] == outcome['returncode'], label
        assert fresh['cli'][label]['stdout_sha256'] == outcome['stdout_sha256'], label
    assert fresh['fixture_sha256'] == old['fixture_sha256'], kind + ': fixture differs'
    print(kind + ': reproduced baseline observations and hashes')
print('Replay artifacts: ' + str(replay))
PY
