"""Tests for `kin save this` — auto-reports latest history entry with an audit_id."""
from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from kindred_client.cli import app
from kindred_client.config import Config, save_config

BACKEND = "http://test.local"
runner = CliRunner()


def _seed_config() -> None:
    save_config(Config(backend_url=BACKEND))


@respx.mock
def test_save_picks_latest_unconsumed_history_and_reports(fake_home):
    _seed_config()
    hist = fake_home / ".kin" / "history"
    hist.mkdir(parents=True)
    (hist / "20260423T101500Z.json").write_text(json.dumps({
        "tool": "Bash", "exit_code": "0", "timestamp": "20260423T101500Z",
        "output_snippet": "12 passed",
        "audit_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }))
    route = respx.post(f"{BACKEND}/v1/ask/outcome").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    r = runner.invoke(app, ["save", "this"])
    assert r.exit_code == 0, r.output
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["audit_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert body["result"] == "success"
    assert body["notes"] == "12 passed"
    # Entry renamed with .consumed suffix.
    entries = list(hist.iterdir())
    assert any(p.name.endswith(".consumed") for p in entries)
    assert not any(p.name.endswith(".json") and not p.name.endswith(".json.consumed") for p in entries)


def test_save_no_history_exits_cleanly(fake_home):
    _seed_config()
    (fake_home / ".kin" / "history").mkdir(parents=True)
    r = runner.invoke(app, ["save", "this"])
    assert r.exit_code == 0
    assert "no history" in r.output.lower()


@respx.mock
def test_save_entry_without_audit_id_consumed_silently(fake_home):
    _seed_config()
    hist = fake_home / ".kin" / "history"
    hist.mkdir(parents=True)
    (hist / "20260423T120000Z.json").write_text(json.dumps({
        "tool": "Bash", "exit_code": "0", "timestamp": "20260423T120000Z",
        "output_snippet": "n/a",
    }))
    # No backend call expected
    route = respx.post(f"{BACKEND}/v1/ask/outcome").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    r = runner.invoke(app, ["save", "this"])
    assert r.exit_code == 0, r.output
    assert not route.called
    assert "no audit_id" in r.output.lower()
    # Entry still renamed to consumed (so it's not picked up again).
    entries = list(hist.iterdir())
    assert any(p.name.endswith(".consumed") for p in entries)
