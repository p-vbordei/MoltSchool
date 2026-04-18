import pytest

from kindred.storage.object_store import InMemoryObjectStore, ObjectNotFound


async def test_put_get_roundtrip():
    store = InMemoryObjectStore()
    await store.put("sha256:abc", b"content")
    assert await store.get("sha256:abc") == b"content"


async def test_get_missing_raises():
    store = InMemoryObjectStore()
    with pytest.raises(ObjectNotFound):
        await store.get("sha256:missing")


async def test_put_is_idempotent():
    store = InMemoryObjectStore()
    await store.put("sha256:x", b"v1")
    await store.put("sha256:x", b"v1")
    assert await store.get("sha256:x") == b"v1"
