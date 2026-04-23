"""Tests for `kin report <audit_id> <result>`."""
from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from kindred_client.cli import app
from kindred_client.config import Config, save_config

BACKEND = "http://test.local"
runner = CliRunner()


def _seed_config(fake_home) -> None:
    save_config(Config(backend_url=BACKEND))


@respx.mock
def test_report_success_posts_to_outcome_endpoint(fake_home):
    _seed_config(fake_home)
    route = respx.post(f"{BACKEND}/v1/ask/outcome").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    r = runner.invoke(app, [
        "report", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "success",
        "--chose", "ART-abc",
    ])
    assert r.exit_code == 0, r.output
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["audit_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert body["result"] == "success"
    assert body["chosen_content_id"] == "ART-abc"
    assert body["notes"] == ""


@respx.mock
def test_report_without_chose_sends_null(fake_home):
    _seed_config(fake_home)
    route = respx.post(f"{BACKEND}/v1/ask/outcome").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    r = runner.invoke(app, [
        "report", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "partial",
    ])
    assert r.exit_code == 0, r.output
    body = json.loads(route.calls[0].request.content)
    assert body["chosen_content_id"] is None
    assert body["result"] == "partial"


@respx.mock
def test_report_backend_error_exit_code_1(fake_home):
    _seed_config(fake_home)
    respx.post(f"{BACKEND}/v1/ask/outcome").mock(
        return_value=httpx.Response(400, json={"message": "bad audit"})
    )
    r = runner.invoke(app, [
        "report", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "success",
    ])
    assert r.exit_code == 1
    assert "Backend error" in r.output
