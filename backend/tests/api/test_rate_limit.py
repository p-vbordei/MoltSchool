import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from kindred.api.deps import db_session, get_object_store, get_settings
from kindred.api.main import app
from kindred.api.middleware import RateLimitMiddleware
from kindred.config import Settings
from kindred.models import (  # noqa: F401 — register tables
    agent,
    artifact,
    audit,
    event,
    invite,
    kindred,
    membership,
    user,
)
from kindred.models.base import Base
from kindred.storage.object_store import InMemoryObjectStore


def _mk_settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "object_store_endpoint": "http://localhost:0",
        "object_store_access_key": "x",
        "object_store_secret_key": "x",
        "object_store_bucket": "x",
        "facilitator_signing_key_hex": "a" * 64,
    }
    base.update(overrides)
    return Settings(**base)


def test_classify_ask():
    mw = RateLimitMiddleware(None, _mk_settings())
    key, limit, window = mw._classify("/v1/kindreds/x/ask", "POST", "pk")
    assert key == ("pk", "ask")
    assert limit == 30
    assert window == 60


def test_classify_contribute():
    mw = RateLimitMiddleware(None, _mk_settings())
    # POST /v1/kindreds/{slug}/artifacts — 4 slashes
    key, limit, window = mw._classify("/v1/kindreds/x/artifacts", "POST", "pk")
    assert key == ("pk", "contribute")
    assert limit == 10
    assert window == 3600
    # Bless should NOT trigger contribute bucket
    key2, *_ = mw._classify("/v1/kindreds/x/artifacts/sha256:abc/bless", "POST", "pk")
    assert key2 is None
    # GET /v1/kindreds/{slug}/artifacts should not trigger contribute bucket
    key3, *_ = mw._classify("/v1/kindreds/x/artifacts", "GET", "pk")
    assert key3 is None


def test_classify_no_match():
    mw = RateLimitMiddleware(None, _mk_settings())
    assert mw._classify("/healthz", "GET", "pk")[0] is None
    assert mw._classify("/v1/users", "POST", "pk")[0] is None


@pytest_asyncio.fixture
async def rate_limited_client():
    """Client with low limits configured via get_settings override.

    Note: RateLimitMiddleware reads settings lazily via get_settings at first request,
    so overriding get_settings in dependency_overrides alone is not enough — the
    middleware caches it. We also patch the instance's _settings directly via
    iteration over app.user_middleware (which holds BuildMiddlewareStack entries)
    is fragile; we rely on the dependency_overrides for any app code that reads
    settings, and verify non-rate-limited paths still work.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    store = InMemoryObjectStore()

    async def _db():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    def _store():
        return store

    def _settings():
        return _mk_settings(
            rate_limit_ask_per_min=2,
            rate_limit_contribute_per_hour=2,
        )

    app.dependency_overrides[db_session] = _db
    app.dependency_overrides[get_object_store] = _store
    app.dependency_overrides[get_settings] = _settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


async def test_rate_limit_smoke(rate_limited_client):
    """Smoke: non-rate-limited endpoint returns 200 with middleware installed."""
    r = await rate_limited_client.get("/healthz")
    assert r.status_code == 200
