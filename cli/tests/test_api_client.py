"""Tests for the httpx-based KindredAPI client (respx-mocked)."""
from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from kindred_client import crypto
from kindred_client.api_client import APIError, KindredAPI

BACKEND = "http://test.local"


@respx.mock
async def test_create_user_sends_ed25519_pubkey():
    sk, pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/users").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "u-1",
                "email": "a@b",
                "display_name": "Alice",
                "pubkey": crypto.pubkey_to_str(pk),
            },
        )
    )
    api = KindredAPI(BACKEND)
    out = await api.create_user("a@b", "Alice", pk)
    assert out["id"] == "u-1"
    body = json.loads(route.calls[0].request.content)
    assert body["pubkey"] == crypto.pubkey_to_str(pk)


@respx.mock
async def test_create_kindred_sends_owner_header():
    sk, pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/kindreds").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "k-1",
                "slug": "test",
                "display_name": "T",
                "description": "",
                "bless_threshold": 2,
            },
        )
    )
    api = KindredAPI(BACKEND)
    await api.create_kindred(
        owner_pubkey=pk, slug="test", display_name="T", description=""
    )
    req = route.calls[0].request
    assert req.headers["x-owner-pubkey"] == crypto.pubkey_to_str(pk)


@respx.mock
async def test_ask_sends_agent_header():
    sk, pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/ask").mock(
        return_value=httpx.Response(
            200,
            json={
                "audit_id": "a-1",
                "artifacts": [],
                "provenance": [],
                "blocked_injection": False,
            },
        )
    )
    api = KindredAPI(BACKEND)
    out = await api.ask(slug="heist", agent_pubkey=pk, query="how to X")
    assert out["audit_id"] == "a-1"
    req = route.calls[0].request
    assert req.headers["x-agent-pubkey"] == crypto.pubkey_to_str(pk)


@respx.mock
async def test_errors_surface_http_status():
    respx.post(f"{BACKEND}/v1/users").mock(
        return_value=httpx.Response(
            409, json={"error": "ConflictError", "message": "user already exists"}
        )
    )
    api = KindredAPI(BACKEND)
    sk, pk = crypto.generate_keypair()
    with pytest.raises(APIError) as exc:
        await api.create_user("a@b", "Alice", pk)
    assert exc.value.status_code == 409
    assert "already exists" in exc.value.message


@respx.mock
async def test_create_agent_signs_attestation_with_owner_sk():
    owner_sk, owner_pk = crypto.generate_keypair()
    _, agent_pk = crypto.generate_keypair()
    expires = "2026-10-18T00:00:00+00:00"
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}

    route = respx.post(f"{BACKEND}/v1/users/u-1/agents").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "a-1",
                "owner_id": "u-1",
                "pubkey": crypto.pubkey_to_str(agent_pk),
                "display_name": "dev",
            },
        )
    )
    api = KindredAPI(BACKEND)
    await api.create_agent(
        owner_id="u-1",
        owner_sk=owner_sk,
        agent_pubkey=agent_pk,
        display_name="dev",
        scope=scope,
        expires_at_iso=expires,
    )
    body = json.loads(route.calls[0].request.content)
    # Server-verifiable signature over the exact canonical payload
    expected = crypto.canonical_json(
        {
            "agent_pubkey": crypto.pubkey_to_str(agent_pk),
            "scope": scope,
            "expires_at": expires,
        }
    )
    assert crypto.verify(owner_pk, expected, bytes.fromhex(body["sig"]))


@respx.mock
async def test_join_signs_accept_body_with_agent_sk():
    ag_sk, ag_pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/join").mock(
        return_value=httpx.Response(
            201, json={"membership_id": "m-1", "kindred_id": "k-1"}
        )
    )
    api = KindredAPI(BACKEND)
    await api.join(token="tok-xyz", agent_pubkey=ag_pk, agent_sk=ag_sk)
    body = json.loads(route.calls[0].request.content)
    accept_body = base64.b64decode(body["accept_body_b64"])
    assert crypto.verify(ag_pk, accept_body, bytes.fromhex(body["accept_sig"]))


@respx.mock
async def test_leave_sends_agent_header():
    _, ag_pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/leave").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    api = KindredAPI(BACKEND)
    await api.leave(slug="heist", agent_pubkey=ag_pk)
    req = route.calls[0].request
    assert req.headers["x-agent-pubkey"] == crypto.pubkey_to_str(ag_pk)


@respx.mock
async def test_upload_artifact_payload_shape():
    _, ag_pk = crypto.generate_keypair()
    route = respx.post(f"{BACKEND}/v1/kindreds/heist/artifacts").mock(
        return_value=httpx.Response(
            201,
            json={
                "content_id": "sha256:abc",
                "type": "routine",
                "logical_name": "r1",
                "tier": "unproven",
                "valid_from": "2026-04-18T00:00:00+00:00",
                "valid_until": "2026-10-18T00:00:00+00:00",
                "outcome_uses": 0,
                "outcome_successes": 0,
            },
        )
    )
    api = KindredAPI(BACKEND)
    metadata = {"kaf_version": "0.1", "type": "routine", "logical_name": "r1"}
    body = b"hello"
    sig = b"\x00" * 64
    out = await api.upload_artifact(
        slug="heist",
        metadata=metadata,
        body=body,
        author_pubkey=ag_pk,
        author_sig=sig,
    )
    assert out["content_id"] == "sha256:abc"
    sent = json.loads(route.calls[0].request.content)
    assert sent["metadata"] == metadata
    assert base64.b64decode(sent["body_b64"]) == body
    assert sent["author_sig"] == sig.hex()
