"""E2E: register → kindred → join → upload 3 artefacts → bless → ask → outcome.

Covers the full Facilitator flow with real HTTP calls (no service-layer shortcuts).
Uses the same FakeEmbeddingProvider path the test `api_test_deps` wires up, so
the retrieval step actually runs cosine similarity.
"""
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
        json={"email": email, "display_name": email, "pubkey": pubkey_to_str(owner_pk)},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires}
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


async def _upload(client, kid, slug, ag_sk, ag_pk, logical_name, body_text):
    body = body_text.encode()
    meta = {
        "kaf_version": "0.1", "type": "routine", "logical_name": logical_name,
        "kindred_id": kid, "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(meta)
    r = await client.post(
        f"/v1/kindreds/{slug}/artifacts",
        json={
            "metadata": meta, "body_b64": base64.b64encode(body).decode(),
            "author_pubkey": pubkey_to_str(ag_pk),
            "author_sig": sign(ag_sk, cid.encode()).hex(),
        },
    )
    assert r.status_code == 201, r.text
    return cid


async def test_ask_flow_end_to_end(e2e_client):
    # 1. Alice + agent
    alice_sk, alice_pk, alice_ag_sk, alice_ag_pk, _ = await _register_user_agent(
        e2e_client, "alice@x",
    )

    # 2. Alice creates kindred with bless_threshold=1 (self-bless flips tier)
    r = await e2e_client.post(
        "/v1/kindreds",
        json={"slug": "crew", "display_name": "Crew", "bless_threshold": 1},
        headers={"x-owner-pubkey": pubkey_to_str(alice_pk)},
    )
    assert r.status_code == 201, r.text
    kid = r.json()["id"]

    # 3. Alice's agent joins via invite
    inv_body = canonical_json({"kindred_id": kid, "seat": "alice"})
    r = await e2e_client.post(
        "/v1/kindreds/crew/invites",
        json={
            "expires_in_days": 7, "max_uses": 1,
            "issuer_sig": sign(alice_sk, inv_body).hex(),
            "inv_body_b64": base64.b64encode(inv_body).decode(),
        },
        headers={"x-owner-pubkey": pubkey_to_str(alice_pk)},
    )
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    accept_body = canonical_json(
        {"token": token, "agent_pubkey": pubkey_to_str(alice_ag_pk)}
    )
    r = await e2e_client.post(
        "/v1/join",
        json={
            "token": token, "agent_pubkey": pubkey_to_str(alice_ag_pk),
            "accept_sig": sign(alice_ag_sk, accept_body).hex(),
            "accept_body_b64": base64.b64encode(accept_body).decode(),
        },
    )
    assert r.status_code == 201, r.text

    # 4. Upload 3 distinct artefacts
    cid_pg = await _upload(
        e2e_client, kid, "crew", alice_ag_sk, alice_ag_pk,
        "postgres-bloat", "postgres-bloat VACUUM FULL on bloated tables routine",
    )
    await _upload(
        e2e_client, kid, "crew", alice_ag_sk, alice_ag_pk,
        "react-hooks", "react-hooks useEffect patterns for cleanup",
    )
    await _upload(
        e2e_client, kid, "crew", alice_ag_sk, alice_ag_pk,
        "nginx-config", "nginx-config gzip pipeline for static assets",
    )

    # 5. Bless postgres-bloat (threshold=1 → class-blessed)
    r = await e2e_client.post(
        f"/v1/kindreds/crew/artifacts/{cid_pg}/bless",
        json={
            "signer_pubkey": pubkey_to_str(alice_ag_pk),
            "sig": sign(alice_ag_sk, cid_pg.encode()).hex(),
        },
    )
    assert r.status_code == 201, r.text

    # 6. /ask — expect postgres-bloat on top
    r = await e2e_client.post(
        "/v1/kindreds/crew/ask",
        json={"query": "postgres-bloat VACUUM FULL on bloated tables routine"},
        headers={"x-agent-pubkey": pubkey_to_str(alice_ag_pk)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audit_id"]
    assert len(body["artifacts"]) >= 1
    assert body["artifacts"][0]["content_id"] == cid_pg
    assert body["provenance"][0]["logical_name"] == "postgres-bloat"
    assert body["provenance"][0]["tier"] == "class-blessed"

    # 7. Report success
    r = await e2e_client.post(
        "/v1/ask/outcome",
        json={"audit_id": body["audit_id"], "result": "success"},
    )
    assert r.status_code == 200, r.text

    # 8. List artefacte → postgres-bloat success rate == 1.0
    r = await e2e_client.get("/v1/kindreds/crew/artifacts")
    arts = r.json()
    pg = next(a for a in arts if a["content_id"] == cid_pg)
    assert pg["outcome_uses"] == 1
    assert pg["outcome_successes"] == 1
