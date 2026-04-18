from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.config import Settings
from kindred.db import make_engine, make_session_factory
from kindred.embeddings.provider import EmbeddingProvider, get_provider
from kindred.storage.object_store import InMemoryObjectStore, MinioObjectStore, ObjectStore

_settings: Settings | None = None
_engine = None
_session_factory = None
_store: ObjectStore | None = None
_provider: EmbeddingProvider | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_session_factory():
    global _engine, _session_factory
    if _session_factory is None:
        _engine = make_engine(get_settings())
        _session_factory = make_session_factory(_engine)
    return _session_factory


def get_object_store() -> ObjectStore:
    global _store
    if _store is None:
        s = get_settings()
        if s.env == "dev" and s.object_store_endpoint.endswith(":0"):
            _store = InMemoryObjectStore()
        else:
            _store = MinioObjectStore(
                s.object_store_endpoint,
                s.object_store_access_key,
                s.object_store_secret_key.get_secret_value(),
                s.object_store_bucket,
            )
    return _store


async def db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = get_provider(get_settings())
    return _provider


async def require_owner_pubkey(x_owner_pubkey: str = Header(...)) -> bytes:
    """Dev-mode auth: owner sends pubkey in header. Plan 06 replaces with OAuth tokens."""
    if not x_owner_pubkey.startswith("ed25519:"):
        raise HTTPException(status_code=401, detail="expected ed25519:hex prefix")
    try:
        return bytes.fromhex(x_owner_pubkey[len("ed25519:"):])
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


__all__ = [
    "Depends",
    "db_session",
    "get_embedding_provider",
    "get_object_store",
    "get_session_factory",
    "get_settings",
    "require_owner_pubkey",
]
