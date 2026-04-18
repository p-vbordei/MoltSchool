from datetime import UTC, datetime, timedelta

import pytest

from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import sign
from kindred.embeddings.provider import FakeEmbeddingProvider
from kindred.facilitator.librarian import _cosine, retrieve_top_k
from kindred.services.artifacts import upload_artifact
from kindred.storage.object_store import InMemoryObjectStore
from tests.helpers import make_full_setup


async def _add_artifact(
    setup, *, logical_name, tags, body, valid_until=None, provider=None,
):
    store = InMemoryObjectStore()
    vu = valid_until or datetime.now(UTC) + timedelta(days=30)
    meta = {
        "kaf_version": "0.1", "type": "routine", "logical_name": logical_name,
        "kindred_id": str(setup["kindred"].id),
        "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": vu.isoformat(),
        "tags": tags,
        "body_sha256": compute_content_id(body),
    }
    from kindred.db import make_engine  # noqa: F401 - just checking import ok
    cid = compute_content_id(meta)
    sig = sign(setup["ag_sk"], cid.encode())
    return await upload_artifact(
        setup["db"], store=store, kindred_id=setup["kindred"].id, metadata=meta, body=body,
        author_pubkey=setup["ag_pk"], author_sig=sig, embedding_provider=provider,
    )


def test_cosine_orthogonal_is_zero():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_identical_is_one():
    assert abs(_cosine([0.6, 0.8], [0.6, 0.8]) - 1.0) < 1e-9


def test_cosine_handles_zero_vector():
    assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


@pytest.mark.asyncio
async def test_retrieve_top_k_finds_relevant(db_session):
    provider = FakeEmbeddingProvider()
    setup = await make_full_setup(db_session, slug="rag1", embedding_provider=provider)
    setup["db"] = db_session
    # Add two more artefacts with distinct logical names & bodies
    await _add_artifact(
        setup, logical_name="postgres-bloat", tags=["database"],
        body=b"VACUUM FULL on bloated tables", provider=provider,
    )
    await _add_artifact(
        setup, logical_name="react-hooks", tags=["frontend"],
        body=b"useEffect cleanup patterns", provider=provider,
    )
    # Query that should match the first artefact closely
    results = await retrieve_top_k(
        db_session, kindred_id=setup["kindred"].id,
        query="postgres-bloat database VACUUM FULL on bloated tables",
        provider=provider, k=2,
    )
    assert len(results) >= 1
    top = results[0][0]
    assert top.logical_name == "postgres-bloat"
    # Score is a float in [-1, 1]
    assert -1.0 <= results[0][1] <= 1.0


@pytest.mark.asyncio
async def test_retrieve_filters_expired(db_session):
    provider = FakeEmbeddingProvider()
    setup = await make_full_setup(db_session, slug="rag2", embedding_provider=provider)
    setup["db"] = db_session
    expired = datetime.now(UTC) - timedelta(days=1)
    await _add_artifact(
        setup, logical_name="stale-doc", tags=[],
        body=b"old content here", valid_until=expired, provider=provider,
    )
    hits_default = await retrieve_top_k(
        db_session, kindred_id=setup["kindred"].id,
        query="stale-doc old content here", provider=provider, k=10,
    )
    names = {a.logical_name for a, _ in hits_default}
    assert "stale-doc" not in names

    hits_include = await retrieve_top_k(
        db_session, kindred_id=setup["kindred"].id,
        query="stale-doc old content here", provider=provider, k=10,
        include_expired=True,
    )
    names_inc = {a.logical_name for a, _ in hits_include}
    assert "stale-doc" in names_inc


@pytest.mark.asyncio
async def test_retrieve_skips_null_embedding(db_session):
    provider = FakeEmbeddingProvider()
    setup = await make_full_setup(db_session, slug="rag3")  # NO provider → no embedding
    setup["db"] = db_session
    # Seed artefact has no embedding — should be excluded
    results = await retrieve_top_k(
        db_session, kindred_id=setup["kindred"].id,
        query="anything", provider=provider, k=10,
    )
    assert results == []
