"""Shared fixtures — isolate `~/.kin/` per test via a fake HOME."""
from __future__ import annotations

import pytest


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Point $HOME at a tmp dir so keystore/config writes are isolated per test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # pathlib.Path.home() on POSIX consults HOME directly; on some platforms
    # pwd is consulted — setting HOME is sufficient for CI/macOS/Linux.
    return tmp_path
