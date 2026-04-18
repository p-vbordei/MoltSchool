import base64
from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from tests.api.helpers import setup_user_agent_kindred


async def test_join_via_invite(api_client):
    # Owner + kindred
    fx = await setup_user_agent_kindred(api_client, slug="join-test", email="owner@x")

    # Issue invite as owner
    inv_body = b"invite-body"
    issuer_sig = sign(fx.owner_sk, inv_body).hex()
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/invites",
        json={
            "expires_in_days": 7,
            "max_uses": 1,
            "issuer_sig": issuer_sig,
            "inv_body_b64": base64.b64encode(inv_body).decode(),
        },
        headers={"x-owner-pubkey": pubkey_to_str(fx.owner_pk)},
    )
    assert r.status_code == 201, r.text
    token = r.json()["token"]

    # Create a second user + agent (joining agent)
    joiner_owner_sk, joiner_owner_pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": "joiner@x", "display_name": "Joiner",
              "pubkey": pubkey_to_str(joiner_owner_pk)},
    )
    assert r.status_code == 201, r.text
    r = await api_client.get(f"/v1/users/by-pubkey/{pubkey_to_str(joiner_owner_pk)}")
    joiner_user_id = r.json()["id"]

    j_ag_sk, j_ag_pk = generate_keypair()
    expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att_payload = canonical_json(
        {"agent_pubkey": pubkey_to_str(j_ag_pk), "scope": scope, "expires_at": expires}
    )
    att_sig = sign(joiner_owner_sk, att_payload).hex()
    r = await api_client.post(
        f"/v1/users/{joiner_user_id}/agents",
        json={
            "agent_pubkey": pubkey_to_str(j_ag_pk),
            "display_name": "joiner-bot",
            "scope": scope,
            "expires_at": expires,
            "sig": att_sig,
        },
    )
    assert r.status_code == 201, r.text

    # Now agent joins via invite
    accept_body = b"accept-body"
    accept_sig = sign(j_ag_sk, accept_body).hex()
    r = await api_client.post(
        "/v1/join",
        json={
            "token": token,
            "agent_pubkey": pubkey_to_str(j_ag_pk),
            "accept_sig": accept_sig,
            "accept_body_b64": base64.b64encode(accept_body).decode(),
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["membership_id"]
    assert data["kindred_id"] == fx.kindred_id


async def test_join_bad_accept_body_b64_is_400(api_client):
    r = await api_client.post(
        "/v1/join",
        json={
            "token": "x" * 32,
            "agent_pubkey": "ed25519:" + "0" * 64,
            "accept_sig": "deadbeef",
            "accept_body_b64": "not!base64!!!",
        },
    )
    assert r.status_code == 400
