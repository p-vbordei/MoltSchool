"""Tests for `kin join`."""
from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from kindred_client import crypto
from kindred_client.cli import app
from kindred_client.commands.join import parse_invite_url
from kindred_client.config import load_config
from kindred_client.keystore import get_kin_dir, list_agents

BACKEND = "http://test.local"
INVITE_URL = f"{BACKEND}/k/heist-crew?inv=tok-xyz"

runner = CliRunner()


def test_parse_invite_url_basic():
    backend, slug, tok = parse_invite_url(INVITE_URL)
    assert backend == BACKEND
    assert slug == "heist-crew"
    assert tok == "tok-xyz"


def test_parse_invite_url_missing_token():
    with pytest.raises(ValueError):
        parse_invite_url(f"{BACKEND}/k/heist-crew")


def test_parse_invite_url_bad_path():
    with pytest.raises(ValueError):
        parse_invite_url(f"{BACKEND}/oops/heist-crew?inv=t")


@respx.mock
def test_join_full_flow_writes_files_and_calls_api(fake_home):
    # Mock all four endpoints kin join hits.
    users_route = respx.post(f"{BACKEND}/v1/users").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "user-1",
                "email": "a@b",
                "display_name": "Alice",
                "pubkey": "ed25519:00",
            },
        )
    )
    agents_route = respx.post(f"{BACKEND}/v1/users/user-1/agents").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "agent-1",
                "owner_id": "user-1",
                "pubkey": "ed25519:00",
                "display_name": "Alice",
            },
        )
    )
    join_route = respx.post(f"{BACKEND}/v1/join").mock(
        return_value=httpx.Response(
            201, json={"membership_id": "m-1", "kindred_id": "k-1"}
        )
    )

    result = runner.invoke(
        app,
        ["join", INVITE_URL, "--email", "a@b", "--name", "Alice"],
    )
    assert result.exit_code == 0, result.stdout
    assert "Joined" in result.stdout

    # Files on disk
    assert (get_kin_dir() / "config.toml").exists()
    agents = list_agents()
    assert "owner" in agents
    assert any(a.startswith("agent-") for a in agents)

    cfg = load_config()
    assert cfg.active_owner_id == "owner"
    assert cfg.active_agent_id and cfg.active_agent_id.startswith("agent-")
    assert cfg.find_kindred("heist-crew") is not None
    assert cfg.find_kindred("heist-crew").user_id == "user-1"

    # HTTP calls
    assert users_route.called
    assert agents_route.called
    assert join_route.called

    # Attestation payload validates under the owner's public key
    attest_body = json.loads(agents_route.calls[0].request.content)
    # Fetch owner_pk from stored keypair
    from kindred_client.keystore import load_keypair

    _, owner_pk = load_keypair("owner")
    payload = crypto.canonical_json(
        {
            "agent_pubkey": attest_body["agent_pubkey"],
            "scope": attest_body["scope"],
            "expires_at": attest_body["expires_at"],
        }
    )
    assert crypto.verify(owner_pk, payload, bytes.fromhex(attest_body["sig"]))

    # Accept body verifies under the agent's public key
    join_body = json.loads(join_route.calls[0].request.content)
    accept_body = base64.b64decode(join_body["accept_body_b64"])
    ag_pk = crypto.str_to_pubkey(join_body["agent_pubkey"])
    assert crypto.verify(ag_pk, accept_body, bytes.fromhex(join_body["accept_sig"]))


@respx.mock
def test_join_with_existing_owner_skips_registration(fake_home):
    # Seed an existing owner keypair + config.
    from kindred_client.config import Config, save_config
    from kindred_client.keystore import store_keypair

    owner_sk, owner_pk = crypto.generate_keypair()
    store_keypair("owner", owner_sk, owner_pk)
    cfg = Config(
        backend_url=BACKEND, active_owner_id="owner", active_agent_id=None
    )
    save_config(cfg)

    users_create = respx.post(f"{BACKEND}/v1/users").mock(
        return_value=httpx.Response(500, json={"message": "should not be called"})
    )
    respx.get(f"{BACKEND}/v1/users/by-pubkey/{crypto.pubkey_to_str(owner_pk)}").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "user-existing",
                "email": "a@b",
                "display_name": "Alice",
                "pubkey": crypto.pubkey_to_str(owner_pk),
            },
        )
    )
    respx.post(f"{BACKEND}/v1/users/user-existing/agents").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "a",
                "owner_id": "user-existing",
                "pubkey": "ed25519:00",
                "display_name": "Alice",
            },
        )
    )
    respx.post(f"{BACKEND}/v1/join").mock(
        return_value=httpx.Response(
            201, json={"membership_id": "m-1", "kindred_id": "k-1"}
        )
    )

    result = runner.invoke(app, ["join", INVITE_URL])
    assert result.exit_code == 0, result.stdout
    assert not users_create.called


@respx.mock
def test_join_surfaces_api_errors(fake_home):
    respx.post(f"{BACKEND}/v1/users").mock(
        return_value=httpx.Response(
            409, json={"error": "ConflictError", "message": "user exists"}
        )
    )
    result = runner.invoke(
        app,
        ["join", INVITE_URL, "--email", "a@b", "--name", "Alice"],
    )
    assert result.exit_code == 1
    assert "user exists" in result.stdout or "user exists" in (result.stderr or "")
