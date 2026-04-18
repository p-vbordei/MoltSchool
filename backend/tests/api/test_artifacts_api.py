import base64
from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign


async def test_upload_artifact_flow(api_client):
    # Register owner user
    owner_sk, owner_pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": "a@x", "display_name": "A", "pubkey": pubkey_to_str(owner_pk)},
    )
    assert r.status_code == 201, r.text

    r = await api_client.get(f"/v1/users/by-pubkey/{pubkey_to_str(owner_pk)}")
    assert r.status_code == 200
    user_id = r.json()["id"]

    # Register agent
    ag_sk, ag_pk = generate_keypair()
    expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att_payload = canonical_json(
        {
            "agent_pubkey": pubkey_to_str(ag_pk),
            "scope": scope,
            "expires_at": expires,
        }
    )
    att_sig = sign(owner_sk, att_payload).hex()
    r = await api_client.post(
        f"/v1/users/{user_id}/agents",
        json={
            "agent_pubkey": pubkey_to_str(ag_pk),
            "display_name": "bot",
            "scope": scope,
            "expires_at": expires,
            "sig": att_sig,
        },
    )
    assert r.status_code == 201, r.text

    # Create kindred
    r = await api_client.post(
        "/v1/kindreds",
        json={"slug": "k1", "display_name": "K1"},
        headers={"x-owner-pubkey": pubkey_to_str(owner_pk)},
    )
    assert r.status_code == 201, r.text

    r = await api_client.get("/v1/kindreds/k1")
    kid = r.json()["id"]

    # Upload artifact
    body = b"# R\n1. step"
    meta = {
        "kaf_version": "0.1",
        "type": "routine",
        "logical_name": "r1",
        "kindred_id": kid,
        "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00",
        "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(meta)
    sig = sign(ag_sk, cid.encode()).hex()
    r = await api_client.post(
        "/v1/kindreds/k1/artifacts",
        json={
            "metadata": meta,
            "body_b64": base64.b64encode(body).decode(),
            "author_pubkey": pubkey_to_str(ag_pk),
            "author_sig": sig,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["tier"] == "peer-shared"  # 0 blessings, default threshold 2
    assert r.json()["content_id"] == cid

    # List artifacts
    r = await api_client.get("/v1/kindreds/k1/artifacts")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["content_id"] == cid
