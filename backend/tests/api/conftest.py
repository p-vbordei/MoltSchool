import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from kindred.api.deps import db_session, get_object_store
from kindred.api.main import app
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


@pytest_asyncio.fixture
async def api_test_deps():
    # StaticPool + single shared connection so in-memory sqlite state is visible
    # across requests (each request opens a new session from the factory).
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    store = InMemoryObjectStore()

    async def override_db_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_object_store():
        return store

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[get_object_store] = override_get_object_store
    yield {"engine": engine, "factory": factory, "store": store}
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(api_test_deps):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
