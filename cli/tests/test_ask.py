"""Tests for `kin ask`."""
from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from kindred_client import crypto
from kindred_client.cli import app
from kindred_client.config import Config, KindredEntry, save_config
from kindred_client.keystore import store_keypair

BACKEND = "http://test.local"
runner = CliRunner()


def _seed_agent(fake_home) -> bytes:
    ag_sk, ag_pk = crypto.generate_keypair()
    store_keypair("agent-xyz", ag_sk, ag_pk)
    cfg = Config(
        backend_url=BACKEND,
        active_agent_id="agent-xyz",
        kindreds=[
            KindredEntry(slug="heist", backend_url=BACKEND, user_id="user-1")
        ],
    )
    save_config(cfg)
    return ag_pk


@respx.mock
def test_ask_sends_agent_header_and_renders(fake_home):
    ag_pk = _seed_agent(fake_home)
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/ask").mock(
        return_value=httpx.Response(
            200,
            json={
                "audit_id": "audit-1",
                "artifacts": [
                    {
                        "content_id": "sha256:a",
                        "tier": "blessed",
                        "framed": "[Artifact 1]\nDo the thing carefully.",
                    },
                    {
                        "content_id": "sha256:b",
                        "tier": "unproven",
                        "framed": "[Artifact 2]\nMaybe try this.",
                    },
                ],
                "provenance": [
                    {
                        "content_id": "sha256:a",
                        "logical_name": "thing-routine",
                        "type": "routine",
                        "tier": "blessed",
                        "author_pubkey": crypto.pubkey_to_str(ag_pk),
                        "outcome_success_rate": 0.8,
                        "valid_until": "2026-10-18T00:00:00+00:00",
                    },
                    {
                        "content_id": "sha256:b",
                        "logical_name": "maybe",
                        "type": "routine",
                        "tier": "unproven",
                        "author_pubkey": crypto.pubkey_to_str(ag_pk),
                        "outcome_success_rate": 0.0,
                        "valid_until": "2026-10-18T00:00:00+00:00",
                    },
                ],
                "blocked_injection": False,
            },
        )
    )
    result = runner.invoke(app, ["ask", "heist", "how do we pull the heist?"])
    assert result.exit_code == 0, result.stdout

    req = route.calls[0].request
    assert req.headers["x-agent-pubkey"] == crypto.pubkey_to_str(ag_pk)
    body = json.loads(req.content)
    assert body["query"] == "how do we pull the heist?"
    assert body["k"] == 5
    assert body["include_peer_shared"] is False

    # rendered content contains framed bodies and audit id
    assert "Do the thing carefully" in result.stdout
    assert "Maybe try this" in result.stdout
    assert "audit-1" in result.stdout


@respx.mock
def test_ask_empty_results_renders_message(fake_home):
    _seed_agent(fake_home)
    respx.post(f"{BACKEND}/v1/kindreds/heist/ask").mock(
        return_value=httpx.Response(
            200,
            json={
                "audit_id": "audit-2",
                "artifacts": [],
                "provenance": [],
                "blocked_injection": False,
            },
        )
    )
    result = runner.invoke(app, ["ask", "heist", "xyz"])
    assert result.exit_code == 0
    assert "No artifacts matched" in result.stdout


@respx.mock
def test_ask_peer_shared_flag_forwarded(fake_home):
    _seed_agent(fake_home)
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/ask").mock(
        return_value=httpx.Response(
            200,
            json={
                "audit_id": "a", "artifacts": [], "provenance": [],
                "blocked_injection": False,
            },
        )
    )
    result = runner.invoke(app, ["ask", "heist", "q", "--peer-shared", "--k", "3"])
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["include_peer_shared"] is True
    assert body["k"] == 3


def test_ask_no_agent_errors(fake_home):
    # No config / agent seeded
    result = runner.invoke(app, ["ask", "heist", "q"])
    assert result.exit_code == 2
    assert "no active agent" in result.stdout


@respx.mock
def test_ask_json_flag_prints_valid_json(fake_home):
    _seed_agent(fake_home)
    respx.post(f"{BACKEND}/v1/kindreds/heist/ask").mock(
        return_value=httpx.Response(
            200,
            json={
                "audit_id": "audit-json-1",
                "artifacts": [
                    {
                        "content_id": "sha256:zzz",
                        "tier": "blessed",
                        "framed": "[Artifact]\nBody.",
                    }
                ],
                "provenance": [],
                "blocked_injection": False,
            },
        )
    )
    result = runner.invoke(app, ["ask", "heist", "q", "--json", "--k", "1"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["audit_id"] == "audit-json-1"
    assert payload["artifacts"][0]["content_id"] == "sha256:zzz"
