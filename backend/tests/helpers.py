from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.services.agents import register_agent
from kindred.services.artifacts import upload_artifact
from kindred.services.invites import issue_invite
from kindred.services.kindreds import create_kindred
from kindred.services.memberships import join_kindred
from kindred.services.users import register_user
from kindred.storage.object_store import InMemoryObjectStore


async def make_user_agent_kindred_artifact(
    db_session, email="a@x", slug="x", embedding_provider=None,
):
    """Create user + agent + kindred + one artifact, and auto-join the agent.

    The creator's agent is now a member of the kindred by default — matches the
    real-world flow where a kindred owner immediately claims a seat. Tests that
    need non-member behaviour should create a separate agent.
    """
    sk, pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute", "read"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    agent = await register_agent(
        db_session, owner_id=u.id, agent_pubkey=ag_pk,
        display_name="x", scope=scope, expires_at=expires, sig=att_sig,
    )
    k = await create_kindred(db_session, owner_id=u.id, slug=slug, display_name="X")

    # Auto-join creator's agent via a single-use invite → membership.
    token = f"tok-{slug}-{ag_pk.hex()[:32]}"
    inv_expires = datetime.now(UTC) + timedelta(days=7)
    inv_body = canonical_json(
        {"kindred_id": str(k.id), "token": token, "expires_at": inv_expires.isoformat()}
    )
    issuer_sig = sign(sk, inv_body)
    await issue_invite(
        db_session, kindred_id=k.id, issued_by=u.id, token=token,
        expires_at=inv_expires, issuer_sig=issuer_sig, issuer_pubkey=pk,
        inv_body=inv_body, max_uses=1,
    )
    accept_body = canonical_json({"token": token, "agent_pubkey": pubkey_to_str(ag_pk)})
    accept_sig = sign(ag_sk, accept_body)
    await join_kindred(
        db_session, token=token, agent_pubkey=ag_pk,
        accept_sig=accept_sig, accept_body=accept_body,
    )

    store = InMemoryObjectStore()
    body = b"# R\n1. step"
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "r1",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    art = await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=metadata, body=body,
        author_pubkey=ag_pk, author_sig=sig, embedding_provider=embedding_provider,
    )
    # Backward-compatible 4-tuple: (artifact, agent_signing_key, agent_pubkey, agent_id).
    # Tests needing the kindred or user signing key call `make_full_setup` instead.
    return art, ag_sk, ag_pk, agent.id


async def make_full_setup(db_session, email="a@x", slug="x", embedding_provider=None):
    """Extended variant returning kindred + user signing key alongside the 4-tuple."""
    sk, pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute", "read"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    agent = await register_agent(
        db_session, owner_id=u.id, agent_pubkey=ag_pk,
        display_name="x", scope=scope, expires_at=expires, sig=att_sig,
    )
    k = await create_kindred(db_session, owner_id=u.id, slug=slug, display_name="X")

    token = f"tok-{slug}-{ag_pk.hex()[:32]}"
    inv_expires = datetime.now(UTC) + timedelta(days=7)
    inv_body = canonical_json(
        {"kindred_id": str(k.id), "token": token, "expires_at": inv_expires.isoformat()}
    )
    issuer_sig = sign(sk, inv_body)
    await issue_invite(
        db_session, kindred_id=k.id, issued_by=u.id, token=token,
        expires_at=inv_expires, issuer_sig=issuer_sig, issuer_pubkey=pk,
        inv_body=inv_body, max_uses=1,
    )
    accept_body = canonical_json({"token": token, "agent_pubkey": pubkey_to_str(ag_pk)})
    accept_sig = sign(ag_sk, accept_body)
    await join_kindred(
        db_session, token=token, agent_pubkey=ag_pk,
        accept_sig=accept_sig, accept_body=accept_body,
    )

    store = InMemoryObjectStore()
    body = b"# R\n1. step"
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "r1",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(metadata)
    author_sig = sign(ag_sk, cid.encode())
    art = await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=metadata, body=body,
        author_pubkey=ag_pk, author_sig=author_sig, embedding_provider=embedding_provider,
    )
    return {
        "art": art, "ag_sk": ag_sk, "ag_pk": ag_pk, "agent_id": agent.id,
        "kindred": k, "user_sk": sk, "user_pk": pk, "user": u, "store": store,
    }
