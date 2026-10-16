"""Prevent inherited environment flags from authorizing paid test execution."""

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("flag", [None, "0", "false", "1"])
def test_live_tests_never_run_from_environment_flags(tmp_path: Path, flag: str | None):
    plugin = tmp_path / "live_tripwire.py"
    plugin.write_text(
        "import sys, types, os, pytest\n"
        "def pytest_configure():\n"
        "    module = types.ModuleType('pdfsmith.backends.aws_textract_backend')\n"
        "    class Tripwire:\n"
        "        def __init__(self):\n"
        "            raise AssertionError('LIVE_TEST_BODY_EXECUTED')\n"
        "    module.AWSTextractBackend = Tripwire\n"
        "    sys.modules[module.__name__] = module\n"
        "@pytest.hookimpl(tryfirst=True)\n"
        "def pytest_runtest_setup(item):\n"
        "    os.environ['AWS_ACCESS_KEY_ID'] = 'synthetic-test-access'\n"
        "    os.environ['AWS_SECRET_ACCESS_KEY'] = 'synthetic-test-secret'\n"
    )
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "LANG"}}
    env.update(
        PYTHONPATH=str(tmp_path),
        HOME=str(tmp_path),
        AWS_ACCESS_KEY_ID="synthetic-test-access",
        AWS_SECRET_ACCESS_KEY="synthetic-test-secret",
        PYTHONDONTWRITEBYTECODE="1",
    )
    if flag is not None:
        env["RUN_COMMERCIAL_TESTS"] = flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_commercial_integration.py"
            "::TestAWSTextractIntegration::test_parse_real_pdf",
            "-p",
            "live_tripwire",
            "-q",
            "--tb=short",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 skipped" in result.stdout


def test_ordinary_test_process_denies_dns_and_tcp():
    with pytest.raises(RuntimeError, match="Outbound networking is disabled"):
        socket.getaddrinfo("metadata.google.internal", 80)
    with (
        socket.socket() as connection,
        pytest.raises(RuntimeError, match="Outbound networking is disabled"),
    ):
        connection.connect(("203.0.113.1", 443))
