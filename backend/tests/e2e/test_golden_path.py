import base64
from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign


async def _register_user_agent(client, email):
    owner_sk, owner_pk = generate_keypair()
    ag_sk, ag_pk = generate_keypair()
    r = await client.post(
        "/v1/users",
        json={
            "email": email,
            "display_name": email,
            "pubkey": pubkey_to_str(owner_pk),
        },
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    att = canonical_json(
        {
            "agent_pubkey": pubkey_to_str(ag_pk),
            "scope": scope,
            "expires_at": expires,
        }
    )
    r = await client.post(
        f"/v1/users/{user_id}/agents",
        json={
            "agent_pubkey": pubkey_to_str(ag_pk),
            "display_name": f"{email}-bot",
            "scope": scope,
            "expires_at": expires,
            "sig": sign(owner_sk, att).hex(),
        },
    )
    assert r.status_code == 201, r.text
    return owner_sk, owner_pk, ag_sk, ag_pk, user_id


async def test_golden_path_end_to_end(e2e_client):
    # 1. Alice + her agent
    alice_sk, alice_pk, alice_ag_sk, alice_ag_pk, _alice_id = await _register_user_agent(
        e2e_client, "alice@x"
    )

    # 2. Alice creates kindred
    r = await e2e_client.post(
        "/v1/kindreds",
        json={"slug": "heist-crew", "display_name": "Heist Crew"},
        headers={"x-owner-pubkey": pubkey_to_str(alice_pk)},
    )
    assert r.status_code == 201, r.text
    kid = r.json()["id"]

    # 3. Alice issues invite for Bob
    inv_body = canonical_json({"kindred_id": kid})
    r = await e2e_client.post(
        "/v1/kindreds/heist-crew/invites",
        json={
            "expires_in_days": 7,
            "max_uses": 1,
            "issuer_sig": sign(alice_sk, inv_body).hex(),
            "inv_body_b64": base64.b64encode(inv_body).decode(),
        },
        headers={"x-owner-pubkey": pubkey_to_str(alice_pk)},
    )
    assert r.status_code == 201, r.text
    invite_token = r.json()["token"]

    # 4. Bob registers + joins via invite
    _bob_sk, _bob_pk, bob_ag_sk, bob_ag_pk, _bob_id = await _register_user_agent(
        e2e_client, "bob@x"
    )
    accept_body = canonical_json({"invite_token": invite_token})
    r = await e2e_client.post(
        "/v1/join",
        json={
            "token": invite_token,
            "agent_pubkey": pubkey_to_str(bob_ag_pk),
            "accept_sig": sign(bob_ag_sk, accept_body).hex(),
            "accept_body_b64": base64.b64encode(accept_body).decode(),
        },
    )
    assert r.status_code == 201, r.text

    # 5. Alice uploads artifact (peer-shared initially, 0 blessings)
    body = b"# Migration Structure\n1. One migration per change."
    meta = {
        "kaf_version": "0.1",
        "type": "routine",
        "logical_name": "migrations",
        "kindred_id": kid,
        "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00",
        "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(meta)
    r = await e2e_client.post(
        "/v1/kindreds/heist-crew/artifacts",
        json={
            "metadata": meta,
            "body_b64": base64.b64encode(body).decode(),
            "author_pubkey": pubkey_to_str(alice_ag_pk),
            "author_sig": sign(alice_ag_sk, cid.encode()).hex(),
        },
    )
    assert r.status_code == 201, r.text
    art = r.json()
    assert art["tier"] == "peer-shared"

    # 6. Carol registers + joins (threshold 2 requires two non-author blessings)
    _carol_sk, _carol_pk, carol_ag_sk, carol_ag_pk, _carol_id = await _register_user_agent(
        e2e_client, "carol@x"
    )
    inv_body2 = canonical_json({"kindred_id": kid, "second": True})
    r = await e2e_client.post(
        "/v1/kindreds/heist-crew/invites",
        json={
            "expires_in_days": 7,
            "max_uses": 1,
            "issuer_sig": sign(alice_sk, inv_body2).hex(),
            "inv_body_b64": base64.b64encode(inv_body2).decode(),
        },
        headers={"x-owner-pubkey": pubkey_to_str(alice_pk)},
    )
    assert r.status_code == 201
    carol_invite = r.json()["token"]
    accept_body2 = canonical_json({"invite_token": carol_invite})
    r = await e2e_client.post(
        "/v1/join",
        json={
            "token": carol_invite,
            "agent_pubkey": pubkey_to_str(carol_ag_pk),
            "accept_sig": sign(carol_ag_sk, accept_body2).hex(),
            "accept_body_b64": base64.b64encode(accept_body2).decode(),
        },
    )
    assert r.status_code == 201

    # 7. Bob blesses
    r = await e2e_client.post(
        f"/v1/kindreds/heist-crew/artifacts/{cid}/bless",
        json={
            "signer_pubkey": pubkey_to_str(bob_ag_pk),
            "sig": sign(bob_ag_sk, cid.encode()).hex(),
        },
    )
    assert r.status_code == 201, r.text

    # 8. Carol blesses (threshold 2 now met)
    r = await e2e_client.post(
        f"/v1/kindreds/heist-crew/artifacts/{cid}/bless",
        json={
            "signer_pubkey": pubkey_to_str(carol_ag_pk),
            "sig": sign(carol_ag_sk, cid.encode()).hex(),
        },
    )
    assert r.status_code == 201, r.text

    # 9. List artifacts — expect tier class-blessed
    r = await e2e_client.get("/v1/kindreds/heist-crew/artifacts")
    arts = r.json()
    assert len(arts) == 1
    assert arts[0]["tier"] == "class-blessed"
