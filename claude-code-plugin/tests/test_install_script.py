"""Syntax-check the installer and PostToolUse hook.

We use `bash -n` (no-op parse) as a baseline — shellcheck is optional: if
installed we run it too, otherwise skip.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    PLUGIN_ROOT / "install.sh",
    PLUGIN_ROOT / "hooks" / "post_tool_use.sh",
]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script: Path):
    assert script.exists(), f"missing {script}"
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_shebang(script: Path):
    first = script.read_text().splitlines()[0]
    assert first.startswith("#!") and "bash" in first


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_executable(script: Path):
    # Ensure executable bit is set (chmod +x).
    assert script.stat().st_mode & 0o111, f"{script} is not executable"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_shellcheck_if_available(script: Path):
    if not shutil.which("shellcheck"):
        pytest.skip("shellcheck not installed")
    subprocess.run(["shellcheck", str(script)], check=True)
