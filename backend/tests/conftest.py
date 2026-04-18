# tests/conftest.py
import os

# Seed test-safe env BEFORE any kindred module imports (config.Settings reads env at init).
os.environ.setdefault("KINDRED_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("KINDRED_OBJECT_STORE_ENDPOINT", "http://localhost:0")
os.environ.setdefault("KINDRED_OBJECT_STORE_ACCESS_KEY", "x")
os.environ.setdefault("KINDRED_OBJECT_STORE_SECRET_KEY", "x")
os.environ.setdefault("KINDRED_OBJECT_STORE_BUCKET", "x")
os.environ.setdefault("KINDRED_FACILITATOR_SIGNING_KEY_HEX", "a" * 64)

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
from tests.helpers import make_user_agent_kindred_artifact


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def artifact_and_agent(db_session):
    return await make_user_agent_kindred_artifact(db_session)
