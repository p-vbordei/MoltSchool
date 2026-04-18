"""Helpers to set up a user + agent + kindred + (optional) artifact via the API."""
import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign


@dataclass
class ApiFixture:
    owner_sk: bytes
    owner_pk: bytes
    user_id: str
    ag_sk: bytes
    ag_pk: bytes
    kindred_id: str
    slug: str
    content_id: str | None = None


async def setup_user_agent_kindred(api_client, slug: str = "k1", email: str = "a@x",
                                   bless_threshold: int = 2,
                                   join_agent: bool = False) -> ApiFixture:
    owner_sk, owner_pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": email, "display_name": email, "pubkey": pubkey_to_str(owner_pk)},
    )
    assert r.status_code == 201, r.text

    r = await api_client.get(f"/v1/users/by-pubkey/{pubkey_to_str(owner_pk)}")
    assert r.status_code == 200
    user_id = r.json()["id"]

    ag_sk, ag_pk = generate_keypair()
    expires = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    scope = {"kindreds": ["*"], "actions": ["contribute", "read"]}
    att_payload = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires}
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

    r = await api_client.post(
        "/v1/kindreds",
        json={"slug": slug, "display_name": slug.upper(), "bless_threshold": bless_threshold},
        headers={"x-owner-pubkey": pubkey_to_str(owner_pk)},
    )
    assert r.status_code == 201, r.text
    kindred_id = r.json()["id"]

    fx = ApiFixture(
        owner_sk=owner_sk,
        owner_pk=owner_pk,
        user_id=user_id,
        ag_sk=ag_sk,
        ag_pk=ag_pk,
        kindred_id=kindred_id,
        slug=slug,
    )
    if join_agent:
        await join_agent_to_kindred(api_client, fx)
    return fx


async def join_agent_to_kindred(api_client, fx: ApiFixture) -> None:
    """Issue an invite as the owner and accept it with the agent."""
    inv_body = canonical_json(
        {"kindred_id": fx.kindred_id, "purpose": "auto-join"}
    )
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

    accept_body = canonical_json(
        {"token": token, "agent_pubkey": pubkey_to_str(fx.ag_pk)}
    )
    accept_sig = sign(fx.ag_sk, accept_body).hex()
    r = await api_client.post(
        "/v1/join",
        json={
            "token": token,
            "agent_pubkey": pubkey_to_str(fx.ag_pk),
            "accept_sig": accept_sig,
            "accept_body_b64": base64.b64encode(accept_body).decode(),
        },
    )
    assert r.status_code == 201, r.text


async def upload_artifact_via_api(api_client, fx: ApiFixture,
                                  logical_name: str = "r1") -> str:
    body = b"# R\n1. step " + logical_name.encode()
    meta = {
        "kaf_version": "0.1",
        "type": "routine",
        "logical_name": logical_name,
        "kindred_id": fx.kindred_id,
        "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00",
        "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(meta)
    sig = sign(fx.ag_sk, cid.encode()).hex()
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/artifacts",
        json={
            "metadata": meta,
            "body_b64": base64.b64encode(body).decode(),
            "author_pubkey": pubkey_to_str(fx.ag_pk),
            "author_sig": sig,
        },
    )
    assert r.status_code == 201, r.text
    fx.content_id = cid
    return cid
