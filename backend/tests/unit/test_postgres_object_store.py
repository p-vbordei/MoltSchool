"""Tests for PostgresObjectStore — bodies stored directly in Postgres.

Uses the same in-memory SQLite fixture as the rest of the unit tests.
SQLAlchemy's LargeBinary type compiles to BYTEA on Postgres and BLOB on
SQLite, so the adapter code works against both.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kindred.storage.object_store import ObjectNotFoundError, PostgresObjectStore


@pytest_asyncio.fixture
async def pg_store(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    return PostgresObjectStore(factory)


async def test_put_get_roundtrip(pg_store):
    await pg_store.put("sha256:abc", b"content")
    assert await pg_store.get("sha256:abc") == b"content"


async def test_get_missing_raises(pg_store):
    with pytest.raises(ObjectNotFoundError):
        await pg_store.get("sha256:missing")


async def test_put_is_idempotent(pg_store):
    await pg_store.put("sha256:x", b"v1")
    await pg_store.put("sha256:x", b"v1")  # same cid, same bytes → no-op
    assert await pg_store.get("sha256:x") == b"v1"


async def test_exists(pg_store):
    assert not await pg_store.exists("sha256:y")
    await pg_store.put("sha256:y", b"hello")
    assert await pg_store.exists("sha256:y")


async def test_binary_bytes_survive_roundtrip(pg_store):
    # Not UTF-8 text — arbitrary bytes, including nulls.
    payload = bytes(range(256)) * 10
    await pg_store.put("sha256:binary", payload)
    assert await pg_store.get("sha256:binary") == payload


async def test_survives_instance_replacement(db_engine):
    """The whole point of this backend: bodies outlive the process.

    Simulates a redeploy: write via one PostgresObjectStore instance, then
    instantiate a second one against the same DB and read. Must still see
    the body — this is what InMemoryObjectStore fails.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    store_a = PostgresObjectStore(factory)
    await store_a.put("sha256:persist", b"I survive redeploys")

    store_b = PostgresObjectStore(factory)  # "redeployed" — fresh object, same DB
    assert await store_b.get("sha256:persist") == b"I survive redeploys"
