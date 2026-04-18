"""Tests for `kin leave`."""
from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from kindred_client import crypto
from kindred_client.cli import app
from kindred_client.config import Config, KindredEntry, load_config, save_config
from kindred_client.keystore import store_keypair

BACKEND = "http://test.local"
runner = CliRunner()


def _seed(fake_home) -> bytes:
    ag_sk, ag_pk = crypto.generate_keypair()
    store_keypair("agent-xyz", ag_sk, ag_pk)
    cfg = Config(
        backend_url=BACKEND,
        active_agent_id="agent-xyz",
        kindreds=[
            KindredEntry(slug="heist", backend_url=BACKEND, user_id="u-1"),
            KindredEntry(slug="keep", backend_url=BACKEND, user_id="u-1"),
        ],
    )
    save_config(cfg)
    return ag_pk


@respx.mock
def test_leave_removes_remote_and_local(fake_home):
    ag_pk = _seed(fake_home)
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/leave").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = runner.invoke(app, ["leave", "heist"])
    assert result.exit_code == 0, result.stdout
    assert "Left" in result.stdout
    assert route.called
    req = route.calls[0].request
    assert req.headers["x-agent-pubkey"] == crypto.pubkey_to_str(ag_pk)

    cfg = load_config()
    assert cfg.find_kindred("heist") is None
    assert cfg.find_kindred("keep") is not None


@respx.mock
def test_leave_when_remote_fails_still_removes_local(fake_home):
    _seed(fake_home)
    respx.post(f"{BACKEND}/v1/kindreds/heist/leave").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    result = runner.invoke(app, ["leave", "heist"])
    assert result.exit_code == 0
    assert "Removed locally only" in result.stdout
    cfg = load_config()
    assert cfg.find_kindred("heist") is None


def test_leave_no_such_kindred_is_noop(fake_home):
    save_config(Config(backend_url=BACKEND))
    result = runner.invoke(app, ["leave", "nope"])
    # no active agent, no entry — prints local-only message, exits 0
    assert result.exit_code == 0
    assert "Removed locally only" in result.stdout or "Left" in result.stdout
