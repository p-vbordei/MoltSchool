from datetime import UTC, datetime, timedelta

import pytest

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.errors import SignatureError, ValidationError
from kindred.services.agents import register_agent
from kindred.services.artifacts import upload_artifact
from kindred.services.kindreds import create_kindred
from kindred.services.users import register_user
from kindred.storage.object_store import InMemoryObjectStore


async def _setup(db_session):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email="a@x", display_name="A", pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    a = await register_agent(db_session, owner_id=u.id, agent_pubkey=ag_pk,
                             display_name="x", scope=scope, expires_at=expires, sig=att_sig)
    k = await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    return u, a, ag_sk, ag_pk, k


async def test_upload_artifact(db_session):
    _u, _a, ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    content_body = b"# Handle Postgres Bloat\n1. ..."
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "handle-bloat",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": ["postgres"],
        "body_sha256": compute_content_id(content_body),
    }
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    art = await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=metadata,
        body=content_body, author_pubkey=ag_pk, author_sig=sig,
    )
    assert art.content_id == cid
    assert await store.exists(metadata["body_sha256"])


async def test_upload_rejects_bad_sig(db_session):
    _u, _a, _ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "x",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": compute_content_id(b"x"),
    }
    with pytest.raises(SignatureError):
        await upload_artifact(
            db_session, store=store, kindred_id=k.id, metadata=metadata,
            body=b"x", author_pubkey=ag_pk, author_sig=b"\x00"*64,
        )


async def test_upload_rejects_mismatched_body_hash(db_session):
    _u, _a, ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "x",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": "sha256:" + "0"*64,
    }
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    with pytest.raises(ValidationError):
        await upload_artifact(
            db_session, store=store, kindred_id=k.id, metadata=metadata,
            body=b"actual body", author_pubkey=ag_pk, author_sig=sig,
        )
