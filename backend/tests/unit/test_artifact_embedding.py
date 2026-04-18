from datetime import UTC, datetime, timedelta

import pytest

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.embeddings.provider import FakeEmbeddingProvider
from kindred.services.agents import register_agent
from kindred.services.artifacts import upload_artifact
from kindred.services.kindreds import create_kindred
from kindred.services.users import register_user
from kindred.storage.object_store import InMemoryObjectStore


async def _setup(db_session):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email="e@x", display_name="e", pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    await register_agent(
        db_session, owner_id=u.id, agent_pubkey=ag_pk, display_name="e",
        scope=scope, expires_at=expires, sig=att_sig,
    )
    k = await create_kindred(db_session, owner_id=u.id, slug="emb", display_name="Emb")
    return ag_sk, ag_pk, k


def _build_metadata(k_id, logical="x", tags=None, body=b"hello"):
    return {
        "kaf_version": "0.1", "type": "routine", "logical_name": logical,
        "kindred_id": str(k_id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": tags or [],
        "body_sha256": compute_content_id(body),
    }


@pytest.mark.asyncio
async def test_artifact_without_provider_stores_none_embedding(db_session):
    ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    body = b"hello"
    meta = _build_metadata(k.id, logical="n1", body=body)
    cid = compute_content_id(meta)
    art = await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=meta, body=body,
        author_pubkey=ag_pk, author_sig=sign(ag_sk, cid.encode()),
    )
    assert art.embedding is None


@pytest.mark.asyncio
async def test_artifact_with_provider_stores_embedding(db_session):
    ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    body = b"something"
    meta = _build_metadata(k.id, logical="pg-bloat", tags=["database"], body=body)
    cid = compute_content_id(meta)
    provider = FakeEmbeddingProvider()
    art = await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=meta, body=body,
        author_pubkey=ag_pk, author_sig=sign(ag_sk, cid.encode()),
        embedding_provider=provider,
    )
    assert isinstance(art.embedding, list)
    assert len(art.embedding) == 64
    assert all(isinstance(x, float) for x in art.embedding)
