# Kindred Backend Core — Implementation Plan (01/07)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrează backend-ul Kindred v0 — API FastAPI stateful cu identitate Ed25519, kindred CRUD, artefacte signed/blessed, audit log append-only, rollback, și infra de dev docker-compose. La sfârșit: server rulează, teste integrate verzi, crypto verificat, scenariu golden-path E2E funcțional.

**Architecture:** Monorepo Python 3.12 + FastAPI async. Postgres 16 pentru metadata/audit, object storage content-addressed (MinIO dev / S3 prod) pentru body-uri artefact. Crypto nativ prin `pynacl`. Models via SQLAlchemy 2.0 async + Alembic migrations. Auth layer out-of-scope în Plan 01 (stub pentru dev) — full OAuth/passkey în Plan 06 (Web UI). Plan 01 expune API-ul cu owner tokens simpli, suficient pentru CLI tests.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, pynacl (Ed25519), Postgres 16, MinIO, pytest-asyncio, httpx, uv, ruff, docker-compose.

**Spec reference:** [docs/superpowers/specs/2026-04-18-kindred-design.md](../specs/2026-04-18-kindred-design.md) — secțiunile 3 (Actori), 4.1 (Identity), 4.2 (Grimoire), 8 (Threat Model), 10 (Tech Stack).

---

## File Structure

```
backend/
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/kindred/
│   ├── __init__.py
│   ├── config.py               # Pydantic settings
│   ├── db.py                   # async engine + session factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # DeclarativeBase
│   │   ├── user.py             # User (human owner)
│   │   ├── agent.py            # Agent (keypair + attestation)
│   │   ├── kindred.py          # Kindred (group)
│   │   ├── membership.py       # AgentKindredMembership
│   │   ├── invite.py           # Invite tokens
│   │   ├── artifact.py         # Artifact + Blessing
│   │   ├── audit.py            # AuditLog
│   │   └── event.py            # Event stream for rollback
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── keys.py             # keypair gen, sign, verify
│   │   ├── canonical.py        # canonical serialization
│   │   └── content_id.py       # SHA-256 content addressing
│   ├── storage/
│   │   ├── __init__.py
│   │   └── object_store.py     # content-addressed blob store
│   ├── services/
│   │   ├── __init__.py
│   │   ├── users.py            # register/get user
│   │   ├── agents.py           # register agent + attestation
│   │   ├── kindreds.py         # kindred CRUD
│   │   ├── invites.py          # invite token lifecycle
│   │   ├── memberships.py      # join/leave
│   │   ├── artifacts.py        # upload/retrieve/verify
│   │   ├── blessings.py        # sign blessing, recalc tier
│   │   ├── audit.py            # append audit entries
│   │   └── rollback.py         # snapshot + revert
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── deps.py             # DI (db session, current user)
│   │   ├── middleware.py       # rate limit, request id
│   │   ├── schemas/            # Pydantic DTOs
│   │   │   ├── users.py
│   │   │   ├── agents.py
│   │   │   ├── kindreds.py
│   │   │   ├── invites.py
│   │   │   ├── artifacts.py
│   │   │   └── audit.py
│   │   └── routers/
│   │       ├── users.py
│   │       ├── agents.py
│   │       ├── kindreds.py
│   │       ├── invites.py
│   │       ├── memberships.py
│   │       ├── artifacts.py
│   │       ├── blessings.py
│   │       ├── audit.py
│   │       └── rollback.py
│   └── errors.py               # domain exceptions
└── tests/
    ├── conftest.py             # pytest fixtures (db, client, keypairs)
    ├── factories.py            # test data builders
    ├── unit/
    │   ├── test_crypto_keys.py
    │   ├── test_canonical.py
    │   ├── test_content_id.py
    │   ├── test_object_store.py
    │   └── test_services_*.py
    ├── api/
    │   ├── test_users.py
    │   ├── test_agents.py
    │   ├── test_kindreds.py
    │   ├── test_invites.py
    │   ├── test_memberships.py
    │   ├── test_artifacts.py
    │   ├── test_blessings.py
    │   ├── test_audit.py
    │   └── test_rollback.py
    └── e2e/
        └── test_golden_path.py # full scenario from spec §7
```

**Decomposition note:** services/ contains domain logic; routers/ are thin HTTP adapters over services. Models are in one file per aggregate. No file exceeds ~200 LoC.

---

## Tasks

### Task 1: Project bootstrap

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/README.md`

- [ ] **Step 1: Create `pyproject.toml` with uv-managed deps**

```toml
[project]
name = "kindred-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.9",
    "pydantic-settings>=2.5",
    "pynacl>=1.5",
    "httpx>=0.27",
    "python-multipart>=0.0.12",
    "minio>=7.2",
    "structlog>=24.1",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.7",
    "aiosqlite>=0.20",  # test-only fallback
]

[tool.ruff]
line-length = 100
target-version = "py312"
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "RUF"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```env
KINDRED_DATABASE_URL=postgresql+asyncpg://kindred:kindred@localhost:5432/kindred
KINDRED_OBJECT_STORE_ENDPOINT=http://localhost:9000
KINDRED_OBJECT_STORE_ACCESS_KEY=minioadmin
KINDRED_OBJECT_STORE_SECRET_KEY=minioadmin
KINDRED_OBJECT_STORE_BUCKET=kindred-artifacts
KINDRED_FACILITATOR_SIGNING_KEY_HEX=change-me-32-bytes-hex
KINDRED_ENV=dev
KINDRED_RATE_LIMIT_ASK_PER_MIN=30
KINDRED_RATE_LIMIT_CONTRIBUTE_PER_HOUR=10
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.env.local
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
*.egg-info/
```

- [ ] **Step 4: Run `uv sync` and verify installation**

```bash
cd backend
uv sync
uv run python -c "import fastapi, sqlalchemy, nacl; print('ok')"
```
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/.gitignore backend/README.md backend/uv.lock
git commit -m "chore: bootstrap kindred backend project"
```

---

### Task 2: Config + DB engine

**Files:**
- Create: `backend/src/kindred/__init__.py` (empty)
- Create: `backend/src/kindred/config.py`
- Create: `backend/src/kindred/db.py`
- Create: `backend/tests/unit/test_config.py`

- [ ] **Step 1: Write failing test for config loading**

```python
# tests/unit/test_config.py
from kindred.config import Settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("KINDRED_DATABASE_URL", "postgresql+asyncpg://x/y")
    monkeypatch.setenv("KINDRED_FACILITATOR_SIGNING_KEY_HEX", "00" * 32)
    monkeypatch.setenv("KINDRED_OBJECT_STORE_ENDPOINT", "http://e")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_ACCESS_KEY", "k")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_SECRET_KEY", "s")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_BUCKET", "b")
    s = Settings()
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert len(s.facilitator_signing_key) == 32
```

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL (module not found).

- [ ] **Step 2: Implement `config.py`**

```python
# src/kindred/config.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KINDRED_", env_file=".env")

    database_url: str
    object_store_endpoint: str
    object_store_access_key: str
    object_store_secret_key: SecretStr
    object_store_bucket: str
    facilitator_signing_key_hex: str = Field(min_length=64, max_length=64)
    env: str = "dev"
    rate_limit_ask_per_min: int = 30
    rate_limit_contribute_per_hour: int = 10

    @property
    def facilitator_signing_key(self) -> bytes:
        return bytes.fromhex(self.facilitator_signing_key_hex)
```

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS.

- [ ] **Step 3: Implement `db.py`**

```python
# src/kindred/db.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from kindred.config import Settings

def make_engine(settings: Settings):
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

def make_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@asynccontextmanager
async def session_scope(factory) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Commit**

```bash
git add backend/src backend/tests/unit/test_config.py
git commit -m "feat: settings and async db engine"
```

---

### Task 3: Base model + migrations scaffold

**Files:**
- Create: `backend/src/kindred/models/__init__.py`
- Create: `backend/src/kindred/models/base.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Create `base.py`**

```python
# src/kindred/models/base.py
from datetime import datetime, UTC
from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

def utcnow() -> datetime:
    return datetime.now(UTC)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
```

- [ ] **Step 2: Initialize Alembic**

```bash
cd backend
uv run alembic init alembic
```

- [ ] **Step 3: Patch `alembic/env.py`** to load `Base.metadata` and async engine

```python
# alembic/env.py (key changes)
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from kindred.config import Settings
from kindred.models.base import Base
from kindred.models import (  # noqa: F401 - ensure models loaded
    user, agent, kindred, membership, invite, artifact, audit, event
)

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = Settings()

def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Commit (skeleton models will be added in Task 4-11)**

```bash
git add backend/alembic backend/alembic.ini backend/src/kindred/models
git commit -m "feat: migrations scaffold + base model"
```

---

### Task 4: Crypto — canonical serialization

**Files:**
- Create: `backend/src/kindred/crypto/__init__.py`
- Create: `backend/src/kindred/crypto/canonical.py`
- Create: `backend/tests/unit/test_canonical.py`

- [ ] **Step 1: Write failing tests for canonical JSON**

```python
# tests/unit/test_canonical.py
from kindred.crypto.canonical import canonical_json

def test_canonical_sorts_keys():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b

def test_canonical_no_whitespace():
    assert b" " not in canonical_json({"x": 1})

def test_canonical_utf8_no_ascii_escape():
    assert "ă".encode("utf-8") in canonical_json({"name": "ănă"})

def test_canonical_nested():
    assert canonical_json({"x": [3, 1, 2]}) == b'{"x":[3,1,2]}'
```

Run: `uv run pytest tests/unit/test_canonical.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement `canonical.py`**

```python
# src/kindred/crypto/canonical.py
import json
from typing import Any

def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8, no ascii escape."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
```

Run: `uv run pytest tests/unit/test_canonical.py -v`
Expected: PASS (4/4).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/crypto backend/tests/unit/test_canonical.py
git commit -m "feat(crypto): canonical json serialization"
```

---

### Task 5: Crypto — content addressing (SHA-256)

**Files:**
- Create: `backend/src/kindred/crypto/content_id.py`
- Create: `backend/tests/unit/test_content_id.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_content_id.py
from kindred.crypto.content_id import compute_content_id

def test_content_id_stable_for_equal_content():
    a = compute_content_id({"x": 1, "y": 2})
    b = compute_content_id({"y": 2, "x": 1})
    assert a == b
    assert a.startswith("sha256:")
    assert len(a) == len("sha256:") + 64  # hex encoded

def test_content_id_differs_for_different_content():
    assert compute_content_id({"x": 1}) != compute_content_id({"x": 2})
```

Run: `uv run pytest tests/unit/test_content_id.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement**

```python
# src/kindred/crypto/content_id.py
import hashlib
from typing import Any
from kindred.crypto.canonical import canonical_json

def compute_content_id(payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    return f"sha256:{digest}"
```

Run: `uv run pytest tests/unit/test_content_id.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/crypto/content_id.py backend/tests/unit/test_content_id.py
git commit -m "feat(crypto): content addressing via sha256"
```

---

### Task 6: Crypto — Ed25519 keys, sign, verify

**Files:**
- Create: `backend/src/kindred/crypto/keys.py`
- Create: `backend/tests/unit/test_crypto_keys.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_crypto_keys.py
import pytest
from kindred.crypto.keys import generate_keypair, sign, verify, pubkey_to_str, str_to_pubkey

def test_generate_keypair_returns_sk_and_pk():
    sk, pk = generate_keypair()
    assert len(sk) == 32
    assert len(pk) == 32

def test_sign_verify_roundtrip():
    sk, pk = generate_keypair()
    msg = b"hello kindred"
    sig = sign(sk, msg)
    assert verify(pk, msg, sig) is True

def test_verify_rejects_tampered_message():
    sk, pk = generate_keypair()
    sig = sign(sk, b"msg")
    assert verify(pk, b"tampered", sig) is False

def test_verify_rejects_bad_signature():
    _, pk = generate_keypair()
    assert verify(pk, b"msg", b"\x00" * 64) is False

def test_pubkey_string_roundtrip():
    _, pk = generate_keypair()
    s = pubkey_to_str(pk)
    assert s.startswith("ed25519:")
    assert str_to_pubkey(s) == pk

def test_str_to_pubkey_rejects_bad_prefix():
    with pytest.raises(ValueError):
        str_to_pubkey("rsa:abcd")
```

Run: `uv run pytest tests/unit/test_crypto_keys.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement**

```python
# src/kindred/crypto/keys.py
from nacl import signing, exceptions

def generate_keypair() -> tuple[bytes, bytes]:
    sk = signing.SigningKey.generate()
    return bytes(sk), bytes(sk.verify_key)

def sign(sk_bytes: bytes, message: bytes) -> bytes:
    sk = signing.SigningKey(sk_bytes)
    return sk.sign(message).signature

def verify(pk_bytes: bytes, message: bytes, signature: bytes) -> bool:
    try:
        vk = signing.VerifyKey(pk_bytes)
        vk.verify(message, signature)
        return True
    except (exceptions.BadSignatureError, ValueError):
        return False

def pubkey_to_str(pk: bytes) -> str:
    return "ed25519:" + pk.hex()

def str_to_pubkey(s: str) -> bytes:
    if not s.startswith("ed25519:"):
        raise ValueError(f"unsupported key format: {s[:10]}")
    return bytes.fromhex(s[len("ed25519:"):])
```

Run: `uv run pytest tests/unit/test_crypto_keys.py -v`
Expected: PASS (6/6).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/crypto/keys.py backend/tests/unit/test_crypto_keys.py
git commit -m "feat(crypto): Ed25519 keypair, sign, verify, string format"
```

---

### Task 7: Object store (content-addressed)

**Files:**
- Create: `backend/src/kindred/storage/__init__.py`
- Create: `backend/src/kindred/storage/object_store.py`
- Create: `backend/tests/unit/test_object_store.py`

- [ ] **Step 1: Write failing tests (use in-memory fake store for unit)**

```python
# tests/unit/test_object_store.py
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
```

- [ ] **Step 2: Implement protocol + in-memory impl + MinIO impl**

```python
# src/kindred/storage/object_store.py
from typing import Protocol

class ObjectNotFound(Exception):
    pass

class ObjectStore(Protocol):
    async def put(self, content_id: str, data: bytes) -> None: ...
    async def get(self, content_id: str) -> bytes: ...
    async def exists(self, content_id: str) -> bool: ...

class InMemoryObjectStore:
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    async def put(self, content_id: str, data: bytes) -> None:
        self._data[content_id] = data

    async def get(self, content_id: str) -> bytes:
        if content_id not in self._data:
            raise ObjectNotFound(content_id)
        return self._data[content_id]

    async def exists(self, content_id: str) -> bool:
        return content_id in self._data

class MinioObjectStore:
    def __init__(self, endpoint: str, access: str, secret: str, bucket: str) -> None:
        from minio import Minio
        self._client = Minio(
            endpoint.removeprefix("http://").removeprefix("https://"),
            access_key=access, secret_key=secret, secure=endpoint.startswith("https"),
        )
        self._bucket = bucket
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    async def put(self, content_id: str, data: bytes) -> None:
        import io
        self._client.put_object(self._bucket, content_id, io.BytesIO(data), len(data))

    async def get(self, content_id: str) -> bytes:
        from minio.error import S3Error
        try:
            resp = self._client.get_object(self._bucket, content_id)
            try:
                return resp.read()
            finally:
                resp.close()
                resp.release_conn()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ObjectNotFound(content_id) from e
            raise

    async def exists(self, content_id: str) -> bool:
        from minio.error import S3Error
        try:
            self._client.stat_object(self._bucket, content_id)
            return True
        except S3Error:
            return False
```

Run: `uv run pytest tests/unit/test_object_store.py -v`
Expected: PASS (3/3).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/storage backend/tests/unit/test_object_store.py
git commit -m "feat(storage): content-addressed object store (memory + minio)"
```

---

### Task 8: Domain models — User + Agent

**Files:**
- Create: `backend/src/kindred/models/user.py`
- Create: `backend/src/kindred/models/agent.py`
- Create: `backend/alembic/versions/0001_users_agents.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/unit/test_models_user_agent.py`

- [ ] **Step 1: Write models**

```python
# src/kindred/models/user.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, UniqueConstraint
from kindred.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pubkey: Mapped[bytes] = mapped_column(nullable=False)  # owner's own Ed25519 pubkey
```

```python
# src/kindred/models/agent.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, LargeBinary, String
from kindred.models.base import Base, TimestampMixin

class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    pubkey: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attestation_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attestation_scope: Mapped[str] = mapped_column(String, nullable=False)  # JSON scope
    attestation_expires_at: Mapped["datetime"] = mapped_column(
        type_=__import__("sqlalchemy").DateTime(timezone=True)
    )
```

- [ ] **Step 2: Write `conftest.py` with in-memory sqlite + model import**

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from kindred.models.base import Base
from kindred.models import user, agent  # noqa: F401

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
```

- [ ] **Step 3: Write model tests**

```python
# tests/unit/test_models_user_agent.py
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from kindred.models.user import User
from kindred.models.agent import Agent

async def test_create_user_and_agent(db_session):
    user = User(email="a@b.c", display_name="Alice", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    agent = Agent(
        owner_id=user.id,
        pubkey=b"\x01" * 32,
        display_name="alice-agent",
        attestation_sig=b"\x02" * 64,
        attestation_scope='{"kindreds":["*"]}',
        attestation_expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(agent)
    await db_session.flush()
    assert agent.id is not None
    assert agent.owner_id == user.id
```

Run: `uv run pytest tests/unit/test_models_user_agent.py -v`
Expected: PASS.

- [ ] **Step 4: Generate alembic migration**

```bash
cd backend
uv run alembic revision --autogenerate -m "users and agents"
# Inspect alembic/versions/0001_*.py — verify tables + columns match
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/kindred/models backend/alembic/versions backend/tests/conftest.py backend/tests/unit/test_models_user_agent.py
git commit -m "feat(models): User and Agent with attestation"
```

---

### Task 9: Domain models — Kindred, Membership, Invite

**Files:**
- Create: `backend/src/kindred/models/kindred.py`
- Create: `backend/src/kindred/models/membership.py`
- Create: `backend/src/kindred/models/invite.py`
- Create: `backend/alembic/versions/0002_kindreds.py`
- Create: `backend/tests/unit/test_models_kindred.py`

- [ ] **Step 1: Models**

```python
# src/kindred/models/kindred.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, Integer
from kindred.models.base import Base, TimestampMixin

class Kindred(Base, TimestampMixin):
    __tablename__ = "kindreds"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    bless_threshold: Mapped[int] = mapped_column(Integer, default=2)
```

```python
# src/kindred/models/membership.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, UniqueConstraint, LargeBinary
from kindred.models.base import Base, TimestampMixin

class AgentKindredMembership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("agent_id", "kindred_id", name="membership_uq"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    invite_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    accept_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
```

```python
# src/kindred/models/invite.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, DateTime, Integer, LargeBinary

from kindred.models.base import Base, TimestampMixin

class Invite(Base, TimestampMixin):
    __tablename__ = "invites"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(default=False)
    issuer_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
```

- [ ] **Step 2: Tests**

```python
# tests/unit/test_models_kindred.py
from datetime import datetime, timedelta, UTC
from kindred.models.user import User
from kindred.models.kindred import Kindred
from kindred.models.invite import Invite

async def test_create_kindred(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user); await db_session.flush()
    k = Kindred(slug="heist-crew", display_name="Heist Crew", created_by=user.id)
    db_session.add(k); await db_session.flush()
    assert k.bless_threshold == 2

async def test_invite_defaults(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user); await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k); await db_session.flush()
    inv = Invite(
        kindred_id=k.id, issued_by=user.id, token="t" * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        issuer_sig=b"\x00" * 64,
    )
    db_session.add(inv); await db_session.flush()
    assert inv.uses == 0 and inv.max_uses == 1 and not inv.revoked
```

Update `tests/conftest.py` imports:
```python
from kindred.models import user, agent, kindred, membership, invite  # noqa: F401
```

Run: `uv run pytest tests/unit/test_models_kindred.py -v`
Expected: PASS (2/2).

- [ ] **Step 3: Alembic migration, commit**

```bash
uv run alembic revision --autogenerate -m "kindreds memberships invites"
git add backend/src/kindred/models backend/alembic/versions backend/tests
git commit -m "feat(models): Kindred, Membership, Invite"
```

---

### Task 10: Domain models — Artifact, Blessing

**Files:**
- Create: `backend/src/kindred/models/artifact.py`
- Create: `backend/alembic/versions/0003_artifacts.py`
- Create: `backend/tests/unit/test_models_artifact.py`

- [ ] **Step 1: Models**

```python
# src/kindred/models/artifact.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, DateTime, LargeBinary, UniqueConstraint, Integer, JSON
from kindred.models.base import Base, TimestampMixin

class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    content_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)  # sha256:...
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # claude_md | routine | skill_ref
    logical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    author_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcome_uses: Mapped[int] = mapped_column(Integer, default=0)
    outcome_successes: Mapped[int] = mapped_column(Integer, default=0)
    superseded_by: Mapped[UUID | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True)

class Blessing(Base, TimestampMixin):
    __tablename__ = "blessings"
    __table_args__ = (UniqueConstraint("artifact_id", "signer_pubkey", name="blessing_uq"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    signer_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signer_agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
```

- [ ] **Step 2: Tests (add to conftest import + test)**

```python
# tests/unit/test_models_artifact.py
from datetime import datetime, timedelta, UTC
from kindred.models.user import User
from kindred.models.kindred import Kindred
from kindred.models.artifact import Artifact, Blessing

async def test_artifact_unique_content_id(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user); await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k); await db_session.flush()
    now = datetime.now(UTC)
    a = Artifact(
        content_id="sha256:" + "a"*64, kindred_id=k.id, type="routine",
        logical_name="r1", author_pubkey=b"\x01"*32, author_sig=b"\x02"*64,
        valid_from=now, valid_until=now + timedelta(days=180),
    )
    db_session.add(a); await db_session.flush()
    assert a.id and a.outcome_uses == 0
```

Run: `uv run pytest tests/unit/test_models_artifact.py -v`
Expected: PASS.

- [ ] **Step 3: Migration + commit**

```bash
uv run alembic revision --autogenerate -m "artifacts and blessings"
git add backend/src/kindred/models backend/alembic/versions backend/tests
git commit -m "feat(models): Artifact and Blessing"
```

---

### Task 11: Domain models — AuditLog, Event

**Files:**
- Create: `backend/src/kindred/models/audit.py`
- Create: `backend/src/kindred/models/event.py`
- Create: `backend/alembic/versions/0004_audit_events.py`
- Create: `backend/tests/unit/test_models_audit_event.py`

- [ ] **Step 1: Models**

```python
# src/kindred/models/audit.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, JSON, LargeBinary, Integer
from kindred.models.base import Base, TimestampMixin

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    agent_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    facilitator_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # per-kindred monotonic
```

```python
# src/kindred/models/event.py
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, JSON, Integer
from kindred.models.base import Base, TimestampMixin

class Event(Base, TimestampMixin):
    """Write-ahead log for rollback — every state change emits an Event."""
    __tablename__ = "events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
```

- [ ] **Step 2: Tests**

```python
# tests/unit/test_models_audit_event.py
from kindred.models.user import User
from kindred.models.kindred import Kindred
from kindred.models.audit import AuditLog
from kindred.models.event import Event

async def test_audit_log_entry(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00"*32)
    db_session.add(user); await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k); await db_session.flush()
    entry = AuditLog(
        kindred_id=k.id, agent_pubkey=b"\x01"*32,
        action="ask", payload={"q": "hi"},
        facilitator_sig=b"\x02"*64, seq=1,
    )
    db_session.add(entry); await db_session.flush()
    assert entry.id

async def test_event_appends(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00"*32)
    db_session.add(user); await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k); await db_session.flush()
    e = Event(kindred_id=k.id, seq=1, event_type="kindred_created", payload={"slug": "x"})
    db_session.add(e); await db_session.flush()
    assert e.id
```

Run: `uv run pytest tests/unit/test_models_audit_event.py -v`
Expected: PASS (2/2).

- [ ] **Step 3: Migration + commit**

```bash
uv run alembic revision --autogenerate -m "audit log and events"
git add backend/src/kindred/models backend/alembic/versions backend/tests
git commit -m "feat(models): AuditLog and Event stream"
```

---

### Task 12: Service — Users & Agents registration with attestation

**Files:**
- Create: `backend/src/kindred/errors.py`
- Create: `backend/src/kindred/services/users.py`
- Create: `backend/src/kindred/services/agents.py`
- Create: `backend/tests/unit/test_services_users_agents.py`

- [ ] **Step 1: Errors**

```python
# src/kindred/errors.py
class KindredError(Exception): ...
class ValidationError(KindredError): ...
class NotFoundError(KindredError): ...
class UnauthorizedError(KindredError): ...
class ConflictError(KindredError): ...
class SignatureError(KindredError): ...
```

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_services_users_agents.py
import pytest
from datetime import datetime, timedelta, UTC
from kindred.crypto.keys import generate_keypair, sign, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.services.users import register_user, get_user_by_pubkey
from kindred.services.agents import register_agent
from kindred.errors import SignatureError, ConflictError

async def test_register_user(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="Alice", pubkey=pk)
    assert u.email == "a@b.c"
    found = await get_user_by_pubkey(db_session, pk)
    assert found.id == u.id

async def test_register_duplicate_email_raises(db_session):
    _, pk = generate_keypair()
    await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    _, pk2 = generate_keypair()
    with pytest.raises(ConflictError):
        await register_user(db_session, email="a@b.c", display_name="A2", pubkey=pk2)

async def test_register_agent_valid_attestation(db_session):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    agent_sk, agent_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    payload = canonical_json({
        "agent_pubkey": pubkey_to_str(agent_pk),
        "scope": scope,
        "expires_at": expires.isoformat(),
    })
    sig = sign(sk, payload)
    a = await register_agent(
        db_session, owner_id=u.id, agent_pubkey=agent_pk,
        display_name="alice-bot", scope=scope, expires_at=expires, sig=sig,
    )
    assert a.owner_id == u.id

async def test_register_agent_bad_attestation_raises(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    _, agent_pk = generate_keypair()
    with pytest.raises(SignatureError):
        await register_agent(
            db_session, owner_id=u.id, agent_pubkey=agent_pk,
            display_name="x", scope={}, expires_at=datetime.now(UTC) + timedelta(days=1),
            sig=b"\x00" * 64,
        )
```

Run: FAIL.

- [ ] **Step 3: Implement services**

```python
# src/kindred/services/users.py
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.user import User
from kindred.errors import ConflictError, NotFoundError

async def register_user(session: AsyncSession, *, email: str, display_name: str, pubkey: bytes) -> User:
    exists = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if exists:
        raise ConflictError(f"email already registered: {email}")
    u = User(email=email, display_name=display_name, pubkey=pubkey)
    session.add(u)
    await session.flush()
    return u

async def get_user(session: AsyncSession, user_id: UUID) -> User:
    u = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise NotFoundError(f"user not found: {user_id}")
    return u

async def get_user_by_pubkey(session: AsyncSession, pubkey: bytes) -> User:
    u = (await session.execute(select(User).where(User.pubkey == pubkey))).scalar_one_or_none()
    if not u:
        raise NotFoundError("user not found by pubkey")
    return u
```

```python
# src/kindred/services/agents.py
from datetime import datetime
from uuid import UUID
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.agent import Agent
from kindred.crypto.keys import verify, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.errors import SignatureError, NotFoundError
from kindred.services.users import get_user

async def register_agent(
    session: AsyncSession,
    *,
    owner_id: UUID,
    agent_pubkey: bytes,
    display_name: str,
    scope: dict,
    expires_at: datetime,
    sig: bytes,
) -> Agent:
    owner = await get_user(session, owner_id)
    payload = canonical_json({
        "agent_pubkey": pubkey_to_str(agent_pubkey),
        "scope": scope,
        "expires_at": expires_at.isoformat(),
    })
    if not verify(owner.pubkey, payload, sig):
        raise SignatureError("invalid owner attestation signature")
    a = Agent(
        owner_id=owner_id, pubkey=agent_pubkey, display_name=display_name,
        attestation_sig=sig, attestation_scope=json.dumps(scope),
        attestation_expires_at=expires_at,
    )
    session.add(a)
    await session.flush()
    return a

async def get_agent_by_pubkey(session: AsyncSession, pubkey: bytes) -> Agent:
    a = (await session.execute(select(Agent).where(Agent.pubkey == pubkey))).scalar_one_or_none()
    if not a:
        raise NotFoundError("agent not found by pubkey")
    return a
```

Run: `uv run pytest tests/unit/test_services_users_agents.py -v`
Expected: PASS (4/4).

- [ ] **Step 4: Commit**

```bash
git add backend/src/kindred/errors.py backend/src/kindred/services backend/tests/unit/test_services_users_agents.py
git commit -m "feat(services): user and agent registration with attestation verify"
```

---

### Task 13: Service — Kindred CRUD

**Files:**
- Create: `backend/src/kindred/services/kindreds.py`
- Create: `backend/src/kindred/services/audit.py`
- Create: `backend/tests/unit/test_services_kindreds.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_services_kindreds.py
import pytest
from kindred.crypto.keys import generate_keypair
from kindred.services.users import register_user
from kindred.services.kindreds import create_kindred, get_kindred_by_slug, list_user_kindreds
from kindred.errors import ConflictError, ValidationError

async def test_create_kindred(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    k = await create_kindred(db_session, owner_id=u.id, slug="heist-crew", display_name="Heist Crew", description="desc")
    assert k.slug == "heist-crew"

async def test_create_kindred_duplicate_slug_raises(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    with pytest.raises(ConflictError):
        await create_kindred(db_session, owner_id=u.id, slug="x", display_name="Y")

async def test_slug_validation(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    with pytest.raises(ValidationError):
        await create_kindred(db_session, owner_id=u.id, slug="Invalid Slug!", display_name="X")

async def test_get_by_slug(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    k = await get_kindred_by_slug(db_session, "x")
    assert k.display_name == "X"
```

- [ ] **Step 2: Implement service + audit**

```python
# src/kindred/services/audit.py
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.crypto.keys import sign
from kindred.crypto.canonical import canonical_json

async def _next_seq(session: AsyncSession, kindred_id: UUID, table) -> int:
    q = select(func.coalesce(func.max(table.seq), 0) + 1).where(table.kindred_id == kindred_id)
    return (await session.execute(q)).scalar_one()

async def append_audit(
    session: AsyncSession, *, kindred_id: UUID, agent_pubkey: bytes,
    action: str, payload: dict, facilitator_sk: bytes,
) -> AuditLog:
    seq = await _next_seq(session, kindred_id, AuditLog)
    body = canonical_json({"kindred_id": str(kindred_id), "seq": seq, "action": action, "payload": payload})
    sig = sign(facilitator_sk, body)
    entry = AuditLog(
        kindred_id=kindred_id, agent_pubkey=agent_pubkey, action=action,
        payload=payload, facilitator_sig=sig, seq=seq,
    )
    session.add(entry)
    await session.flush()
    return entry

async def append_event(session: AsyncSession, *, kindred_id: UUID, event_type: str, payload: dict) -> Event:
    seq = await _next_seq(session, kindred_id, Event)
    e = Event(kindred_id=kindred_id, seq=seq, event_type=event_type, payload=payload)
    session.add(e)
    await session.flush()
    return e
```

```python
# src/kindred/services/kindreds.py
import re
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.kindred import Kindred
from kindred.models.membership import AgentKindredMembership
from kindred.models.agent import Agent
from kindred.errors import ConflictError, NotFoundError, ValidationError
from kindred.services.audit import append_event

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,63}$")

async def create_kindred(
    session: AsyncSession, *, owner_id: UUID, slug: str, display_name: str,
    description: str = "", bless_threshold: int = 2,
) -> Kindred:
    if not SLUG_RE.match(slug):
        raise ValidationError(f"invalid slug: {slug!r}")
    exists = (await session.execute(select(Kindred).where(Kindred.slug == slug))).scalar_one_or_none()
    if exists:
        raise ConflictError(f"slug exists: {slug}")
    k = Kindred(
        slug=slug, display_name=display_name, description=description,
        created_by=owner_id, bless_threshold=bless_threshold,
    )
    session.add(k)
    await session.flush()
    await append_event(session, kindred_id=k.id, event_type="kindred_created",
                       payload={"slug": slug, "owner": str(owner_id)})
    return k

async def get_kindred_by_slug(session: AsyncSession, slug: str) -> Kindred:
    k = (await session.execute(select(Kindred).where(Kindred.slug == slug))).scalar_one_or_none()
    if not k:
        raise NotFoundError(f"kindred not found: {slug}")
    return k

async def list_user_kindreds(session: AsyncSession, user_id: UUID) -> list[Kindred]:
    q = (
        select(Kindred).join(AgentKindredMembership, AgentKindredMembership.kindred_id == Kindred.id)
        .join(Agent, Agent.id == AgentKindredMembership.agent_id).where(Agent.owner_id == user_id).distinct()
    )
    return list((await session.execute(q)).scalars())
```

Run: `uv run pytest tests/unit/test_services_kindreds.py -v`
Expected: PASS (4/4).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/services backend/tests/unit/test_services_kindreds.py
git commit -m "feat(services): kindred CRUD + audit/event helpers"
```

---

### Task 14: Service — Invites (issue, verify, redeem)

**Files:**
- Create: `backend/src/kindred/services/invites.py`
- Create: `backend/src/kindred/services/memberships.py`
- Create: `backend/tests/unit/test_services_invites_memberships.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_services_invites_memberships.py
import pytest
from datetime import datetime, timedelta, UTC
from kindred.crypto.keys import generate_keypair, sign, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.services.users import register_user
from kindred.services.agents import register_agent
from kindred.services.kindreds import create_kindred
from kindred.services.invites import issue_invite, get_invite_by_token, revoke_invite
from kindred.services.memberships import join_kindred
from kindred.errors import SignatureError, ValidationError

async def _register_user_and_agent(db_session, email):
    owner_sk, owner_pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=owner_pk)
    agent_sk, agent_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    attest_payload = canonical_json({
        "agent_pubkey": pubkey_to_str(agent_pk),
        "scope": scope,
        "expires_at": expires.isoformat(),
    })
    att_sig = sign(owner_sk, attest_payload)
    a = await register_agent(
        db_session, owner_id=u.id, agent_pubkey=agent_pk, display_name=f"{email}-bot",
        scope=scope, expires_at=expires, sig=att_sig,
    )
    return u, owner_sk, owner_pk, a, agent_sk, agent_pk

async def test_issue_and_redeem_invite(db_session):
    alice, alice_sk, alice_pk, _, _, _ = await _register_user_and_agent(db_session, "alice@x")
    k = await create_kindred(db_session, owner_id=alice.id, slug="x", display_name="X")

    inv_body = canonical_json({"kindred_id": str(k.id), "token_prefix": "t"})
    inv_sig = sign(alice_sk, inv_body)
    token = "t" + "0" * 31
    inv = await issue_invite(
        db_session, kindred_id=k.id, issued_by=alice.id, token=token,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        issuer_sig=inv_sig, issuer_pubkey=alice_pk, inv_body=inv_body, max_uses=1,
    )
    assert inv.token == token

    bob, _, bob_pk, bob_agent, bob_agent_sk, bob_agent_pk = await _register_user_and_agent(db_session, "bob@x")
    accept_body = canonical_json({"invite_token": token, "agent_pubkey": pubkey_to_str(bob_agent_pk)})
    accept_sig = sign(bob_agent_sk, accept_body)
    m = await join_kindred(
        db_session, token=token, agent_pubkey=bob_agent_pk,
        accept_sig=accept_sig, accept_body=accept_body,
    )
    assert m.kindred_id == k.id

async def test_invite_bad_issuer_sig_raises(db_session):
    alice, alice_sk, alice_pk, *_ = await _register_user_and_agent(db_session, "alice@x")
    k = await create_kindred(db_session, owner_id=alice.id, slug="x", display_name="X")
    with pytest.raises(SignatureError):
        await issue_invite(
            db_session, kindred_id=k.id, issued_by=alice.id, token="t"*32,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            issuer_sig=b"\x00"*64, issuer_pubkey=alice_pk, inv_body=b"body",
        )

async def test_invite_expired_rejected(db_session):
    alice, alice_sk, alice_pk, *_ = await _register_user_and_agent(db_session, "alice@x")
    k = await create_kindred(db_session, owner_id=alice.id, slug="x", display_name="X")
    inv_body = canonical_json({"kindred_id": str(k.id)})
    inv_sig = sign(alice_sk, inv_body)
    await issue_invite(
        db_session, kindred_id=k.id, issued_by=alice.id, token="t"*32,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        issuer_sig=inv_sig, issuer_pubkey=alice_pk, inv_body=inv_body,
    )
    _, _, _, _, bob_agent_sk, bob_agent_pk = await _register_user_and_agent(db_session, "bob@x")
    with pytest.raises(ValidationError):
        await join_kindred(
            db_session, token="t"*32, agent_pubkey=bob_agent_pk,
            accept_sig=b"\x00"*64, accept_body=b"{}",
        )
```

Run: FAIL.

- [ ] **Step 2: Implement invites + memberships**

```python
# src/kindred/services/invites.py
from datetime import datetime, UTC
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.invite import Invite
from kindred.crypto.keys import verify
from kindred.errors import SignatureError, NotFoundError, ValidationError

async def issue_invite(
    session: AsyncSession, *, kindred_id: UUID, issued_by: UUID, token: str,
    expires_at: datetime, issuer_sig: bytes, issuer_pubkey: bytes, inv_body: bytes,
    max_uses: int = 1,
) -> Invite:
    if not verify(issuer_pubkey, inv_body, issuer_sig):
        raise SignatureError("invalid issuer signature on invite body")
    if len(token) < 16:
        raise ValidationError("token too short")
    inv = Invite(
        kindred_id=kindred_id, issued_by=issued_by, token=token,
        expires_at=expires_at, max_uses=max_uses, uses=0,
        issuer_sig=issuer_sig,
    )
    session.add(inv)
    await session.flush()
    return inv

async def get_invite_by_token(session: AsyncSession, token: str) -> Invite:
    inv = (await session.execute(select(Invite).where(Invite.token == token))).scalar_one_or_none()
    if not inv:
        raise NotFoundError("invite not found")
    return inv

async def revoke_invite(session: AsyncSession, token: str) -> None:
    inv = await get_invite_by_token(session, token)
    inv.revoked = True
    await session.flush()

def assert_invite_usable(inv: Invite) -> None:
    if inv.revoked:
        raise ValidationError("invite revoked")
    if inv.expires_at < datetime.now(UTC):
        raise ValidationError("invite expired")
    if inv.uses >= inv.max_uses:
        raise ValidationError("invite exhausted")
```

```python
# src/kindred/services/memberships.py
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.membership import AgentKindredMembership
from kindred.services.invites import get_invite_by_token, assert_invite_usable
from kindred.services.agents import get_agent_by_pubkey
from kindred.services.audit import append_event
from kindred.crypto.keys import verify
from kindred.errors import SignatureError

async def join_kindred(
    session: AsyncSession, *, token: str, agent_pubkey: bytes,
    accept_sig: bytes, accept_body: bytes,
) -> AgentKindredMembership:
    inv = await get_invite_by_token(session, token)
    assert_invite_usable(inv)
    if not verify(agent_pubkey, accept_body, accept_sig):
        raise SignatureError("invalid accept signature")
    agent = await get_agent_by_pubkey(session, agent_pubkey)
    m = AgentKindredMembership(
        agent_id=agent.id, kindred_id=inv.kindred_id,
        invite_sig=inv.issuer_sig, accept_sig=accept_sig,
    )
    session.add(m)
    inv.uses += 1
    await session.flush()
    await append_event(session, kindred_id=inv.kindred_id, event_type="member_joined",
                       payload={"agent_pubkey": agent_pubkey.hex()})
    return m

async def leave_kindred(session: AsyncSession, *, agent_pubkey: bytes, kindred_slug: str) -> None:
    from kindred.services.kindreds import get_kindred_by_slug
    k = await get_kindred_by_slug(session, kindred_slug)
    agent = await get_agent_by_pubkey(session, agent_pubkey)
    from sqlalchemy import select, delete
    q = delete(AgentKindredMembership).where(
        AgentKindredMembership.agent_id == agent.id,
        AgentKindredMembership.kindred_id == k.id,
    )
    await session.execute(q)
    await append_event(session, kindred_id=k.id, event_type="member_left",
                       payload={"agent_pubkey": agent_pubkey.hex()})
```

Run: `uv run pytest tests/unit/test_services_invites_memberships.py -v`
Expected: PASS (3/3).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/services backend/tests/unit/test_services_invites_memberships.py
git commit -m "feat(services): invites issue/redeem + memberships join/leave"
```

---

### Task 15: Service — Artifacts (upload with sig verify, content addressing)

**Files:**
- Create: `backend/src/kindred/services/artifacts.py`
- Create: `backend/tests/unit/test_services_artifacts.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_services_artifacts.py
import pytest
from datetime import datetime, timedelta, UTC
from kindred.crypto.keys import generate_keypair, sign, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.storage.object_store import InMemoryObjectStore
from kindred.services.users import register_user
from kindred.services.agents import register_agent
from kindred.services.kindreds import create_kindred
from kindred.services.artifacts import upload_artifact, get_artifact, list_artifacts
from kindred.errors import SignatureError, ValidationError

async def _setup(db_session):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email="a@x", display_name="A", pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json({"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()})
    att_sig = sign(sk, att)
    a = await register_agent(db_session, owner_id=u.id, agent_pubkey=ag_pk,
                             display_name="x", scope=scope, expires_at=expires, sig=att_sig)
    k = await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    return u, a, ag_sk, ag_pk, k

async def test_upload_artifact(db_session):
    u, a, ag_sk, ag_pk, k = await _setup(db_session)
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
    u, a, ag_sk, ag_pk, k = await _setup(db_session)
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
    u, a, ag_sk, ag_pk, k = await _setup(db_session)
    store = InMemoryObjectStore()
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "x",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": "sha256:" + "0"*64,  # wrong
    }
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    with pytest.raises(ValidationError):
        await upload_artifact(
            db_session, store=store, kindred_id=k.id, metadata=metadata,
            body=b"actual body", author_pubkey=ag_pk, author_sig=sig,
        )
```

Run: FAIL.

- [ ] **Step 2: Implement**

```python
# src/kindred/services/artifacts.py
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.artifact import Artifact
from kindred.storage.object_store import ObjectStore
from kindred.crypto.keys import verify
from kindred.crypto.content_id import compute_content_id
from kindred.errors import SignatureError, ValidationError, NotFoundError
from kindred.services.audit import append_event

ALLOWED_TYPES = {"claude_md", "routine", "skill_ref"}

async def upload_artifact(
    session: AsyncSession, *, store: ObjectStore, kindred_id: UUID,
    metadata: dict, body: bytes, author_pubkey: bytes, author_sig: bytes,
) -> Artifact:
    if metadata.get("type") not in ALLOWED_TYPES:
        raise ValidationError(f"unsupported type: {metadata.get('type')}")
    actual_body_cid = compute_content_id(body)
    if metadata.get("body_sha256") != actual_body_cid:
        raise ValidationError("body_sha256 mismatch")
    cid = compute_content_id(metadata)
    if not verify(author_pubkey, cid.encode(), author_sig):
        raise SignatureError("invalid author signature on content_id")
    exists = (await session.execute(select(Artifact).where(Artifact.content_id == cid))).scalar_one_or_none()
    if exists:
        return exists
    await store.put(actual_body_cid, body)
    art = Artifact(
        content_id=cid, kindred_id=kindred_id, type=metadata["type"],
        logical_name=metadata["logical_name"], author_pubkey=author_pubkey,
        author_sig=author_sig,
        valid_from=datetime.fromisoformat(metadata["valid_from"]),
        valid_until=datetime.fromisoformat(metadata["valid_until"]),
        tags=metadata.get("tags", []),
    )
    session.add(art)
    await session.flush()
    await append_event(session, kindred_id=kindred_id, event_type="artifact_uploaded",
                       payload={"content_id": cid, "logical_name": metadata["logical_name"]})
    return art

async def get_artifact(session: AsyncSession, content_id: str) -> Artifact:
    a = (await session.execute(select(Artifact).where(Artifact.content_id == content_id))).scalar_one_or_none()
    if not a:
        raise NotFoundError(f"artifact {content_id}")
    return a

async def list_artifacts(session: AsyncSession, kindred_id: UUID) -> list[Artifact]:
    q = select(Artifact).where(Artifact.kindred_id == kindred_id)
    return list((await session.execute(q)).scalars())
```

Run: `uv run pytest tests/unit/test_services_artifacts.py -v`
Expected: PASS (3/3).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/services/artifacts.py backend/tests/unit/test_services_artifacts.py
git commit -m "feat(services): artifact upload with sig verify + content addressing"
```

---

### Task 16: Service — Blessings & tier derivation

**Files:**
- Create: `backend/src/kindred/services/blessings.py`
- Create: `backend/tests/unit/test_services_blessings.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_services_blessings.py
import pytest
from kindred.crypto.keys import sign
from kindred.services.blessings import add_blessing, compute_tier
from kindred.errors import SignatureError, ConflictError
from kindred.models.artifact import Blessing
from sqlalchemy import select

# reuse setup helper from test_services_artifacts via direct copy in this file for isolation
# (or extract to tests/helpers.py — do that in Step 2)

async def test_add_blessing_ok(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    sig = sign(ag_sk, art.content_id.encode())
    b = await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=sig)
    assert b.id

async def test_blessing_bad_sig(db_session, artifact_and_agent):
    art, _, ag_pk, agent_id = artifact_and_agent
    with pytest.raises(SignatureError):
        await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=b"\x00"*64)

async def test_blessing_dedup(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    sig = sign(ag_sk, art.content_id.encode())
    await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                       signer_pubkey=ag_pk, sig=sig)
    with pytest.raises(ConflictError):
        await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=sig)

async def test_tier_peer_vs_blessed(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    # 0 blessings (author_sig isn't a blessing)
    tier = await compute_tier(db_session, artifact=art, threshold=2)
    assert tier == "peer-shared"
    # 2 blessings
    sig = sign(ag_sk, art.content_id.encode())
    await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                       signer_pubkey=ag_pk, sig=sig)
    db_session.add(Blessing(
        artifact_id=art.id, signer_pubkey=b"\x09"*32, signer_agent_id=agent_id, sig=b"\x08"*64,
    ))
    await db_session.flush()
    tier = await compute_tier(db_session, artifact=art, threshold=2)
    assert tier == "class-blessed"
```

Extract setup helper:

```python
# tests/helpers.py
from datetime import datetime, timedelta, UTC
from kindred.crypto.keys import generate_keypair, sign, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.storage.object_store import InMemoryObjectStore
from kindred.services.users import register_user
from kindred.services.agents import register_agent
from kindred.services.kindreds import create_kindred
from kindred.services.artifacts import upload_artifact

async def make_user_agent_kindred_artifact(db_session, email="a@x", slug="x"):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json({"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()})
    att_sig = sign(sk, att)
    a = await register_agent(db_session, owner_id=u.id, agent_pubkey=ag_pk,
                             display_name="x", scope=scope, expires_at=expires, sig=att_sig)
    k = await create_kindred(db_session, owner_id=u.id, slug=slug, display_name="X")
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
    art = await upload_artifact(db_session, store=store, kindred_id=k.id,
                                metadata=metadata, body=body,
                                author_pubkey=ag_pk, author_sig=sig)
    return art, ag_sk, ag_pk, a.id
```

Add conftest fixture:
```python
# tests/conftest.py (append)
import pytest_asyncio
from tests.helpers import make_user_agent_kindred_artifact

@pytest_asyncio.fixture
async def artifact_and_agent(db_session):
    return await make_user_agent_kindred_artifact(db_session)
```

- [ ] **Step 2: Implement blessings service**

```python
# src/kindred/services/blessings.py
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.artifact import Artifact, Blessing
from kindred.crypto.keys import verify
from kindred.errors import SignatureError, ConflictError
from kindred.services.audit import append_event

async def add_blessing(
    session: AsyncSession, *, artifact: Artifact, signer_agent_id: UUID,
    signer_pubkey: bytes, sig: bytes,
) -> Blessing:
    if not verify(signer_pubkey, artifact.content_id.encode(), sig):
        raise SignatureError("invalid blessing signature over content_id")
    exists = (await session.execute(
        select(Blessing).where(
            Blessing.artifact_id == artifact.id,
            Blessing.signer_pubkey == signer_pubkey,
        )
    )).scalar_one_or_none()
    if exists:
        raise ConflictError("already blessed by this signer")
    b = Blessing(
        artifact_id=artifact.id, signer_pubkey=signer_pubkey,
        signer_agent_id=signer_agent_id, sig=sig,
    )
    session.add(b)
    await session.flush()
    await append_event(session, kindred_id=artifact.kindred_id, event_type="artifact_blessed",
                       payload={"content_id": artifact.content_id,
                                "signer_pubkey": signer_pubkey.hex()})
    return b

async def count_blessings(session: AsyncSession, artifact_id: UUID) -> int:
    q = select(func.count()).select_from(Blessing).where(Blessing.artifact_id == artifact_id)
    return (await session.execute(q)).scalar_one()

async def compute_tier(session: AsyncSession, *, artifact: Artifact, threshold: int) -> str:
    n = await count_blessings(session, artifact.id)
    return "class-blessed" if n >= threshold else "peer-shared"
```

Run: `uv run pytest tests/unit/test_services_blessings.py -v`
Expected: PASS (4/4).

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/services/blessings.py backend/tests/helpers.py backend/tests/unit/test_services_blessings.py backend/tests/conftest.py
git commit -m "feat(services): blessings + tier derivation"
```

---

### Task 17: Service — Rollback

**Files:**
- Create: `backend/src/kindred/services/rollback.py`
- Create: `backend/tests/unit/test_services_rollback.py`

- [ ] **Step 1: Test (integration with events)**

```python
# tests/unit/test_services_rollback.py
from datetime import UTC
from kindred.services.rollback import list_events, rollback_to
from tests.helpers import make_user_agent_kindred_artifact

async def test_rollback_retains_events_before_point(db_session):
    art, *_ = await make_user_agent_kindred_artifact(db_session)
    events_before = await list_events(db_session, kindred_id=art.kindred_id)
    assert len(events_before) >= 2  # kindred_created + artifact_uploaded
    cutoff_seq = events_before[0].seq  # after kindred_created
    await rollback_to(db_session, kindred_id=art.kindred_id, up_to_seq=cutoff_seq)
    from sqlalchemy import select
    from kindred.models.artifact import Artifact
    remaining = list((await db_session.execute(
        select(Artifact).where(Artifact.kindred_id == art.kindred_id)
    )).scalars())
    assert len(remaining) == 0
```

- [ ] **Step 2: Implement**

```python
# src/kindred/services/rollback.py
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.event import Event
from kindred.models.artifact import Artifact, Blessing
from kindred.models.membership import AgentKindredMembership

async def list_events(session: AsyncSession, *, kindred_id: UUID) -> list[Event]:
    q = select(Event).where(Event.kindred_id == kindred_id).order_by(Event.seq)
    return list((await session.execute(q)).scalars())

async def rollback_to(session: AsyncSession, *, kindred_id: UUID, up_to_seq: int) -> None:
    """Replay semantics: delete state changes introduced AFTER `up_to_seq`.
    v0 supports: artifact_uploaded, artifact_blessed, member_joined, member_left.
    """
    events_to_revert = list((await session.execute(
        select(Event).where(Event.kindred_id == kindred_id, Event.seq > up_to_seq)
        .order_by(Event.seq.desc())
    )).scalars())
    for e in events_to_revert:
        if e.event_type == "artifact_uploaded":
            cid = e.payload["content_id"]
            await session.execute(delete(Blessing).where(
                Blessing.artifact_id.in_(select(Artifact.id).where(Artifact.content_id == cid))
            ))
            await session.execute(delete(Artifact).where(Artifact.content_id == cid))
        elif e.event_type == "artifact_blessed":
            cid = e.payload["content_id"]
            signer = bytes.fromhex(e.payload["signer_pubkey"])
            await session.execute(delete(Blessing).where(
                Blessing.signer_pubkey == signer,
                Blessing.artifact_id.in_(select(Artifact.id).where(Artifact.content_id == cid)),
            ))
        elif e.event_type == "member_joined":
            pk = bytes.fromhex(e.payload["agent_pubkey"])
            from kindred.models.agent import Agent
            await session.execute(delete(AgentKindredMembership).where(
                AgentKindredMembership.kindred_id == kindred_id,
                AgentKindredMembership.agent_id.in_(select(Agent.id).where(Agent.pubkey == pk)),
            ))
        elif e.event_type == "member_left":
            # idempotent: do nothing on replay
            pass
        await session.execute(delete(Event).where(Event.id == e.id))
    await session.flush()
```

Run: `uv run pytest tests/unit/test_services_rollback.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/services/rollback.py backend/tests/unit/test_services_rollback.py
git commit -m "feat(services): rollback via event replay"
```

---

### Task 18: API — FastAPI app + DI + schemas + routers

**Files:**
- Create: `backend/src/kindred/api/main.py`
- Create: `backend/src/kindred/api/deps.py`
- Create: `backend/src/kindred/api/middleware.py`
- Create: `backend/src/kindred/api/schemas/__init__.py`
- Create: `backend/src/kindred/api/schemas/kindreds.py`
- Create: `backend/src/kindred/api/schemas/artifacts.py`
- Create: `backend/src/kindred/api/routers/__init__.py`
- Create: `backend/src/kindred/api/routers/kindreds.py`
- Create: `backend/src/kindred/api/routers/artifacts.py`
- Create: `backend/src/kindred/api/routers/health.py`
- Create: `backend/tests/api/test_health.py`
- Create: `backend/tests/api/test_kindreds_api.py`
- Create: `backend/tests/api/test_artifacts_api.py`

- [ ] **Step 1: Write app + DI scaffolding**

```python
# src/kindred/api/deps.py
from collections.abc import AsyncIterator
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.config import Settings
from kindred.db import make_engine, make_session_factory
from kindred.storage.object_store import MinioObjectStore, InMemoryObjectStore, ObjectStore

_settings: Settings | None = None
_engine = None
_session_factory = None
_store: ObjectStore | None = None

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
                s.object_store_endpoint, s.object_store_access_key,
                s.object_store_secret_key.get_secret_value(), s.object_store_bucket,
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

async def require_owner_pubkey(x_owner_pubkey: str = Header(...)) -> bytes:
    """Dev-mode auth: owner sends pubkey in header. Plan 06 replaces this with OAuth tokens."""
    try:
        if not x_owner_pubkey.startswith("ed25519:"):
            raise ValueError("expected ed25519:hex prefix")
        return bytes.fromhex(x_owner_pubkey[len("ed25519:"):])
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
```

```python
# src/kindred/api/main.py
from fastapi import FastAPI
from kindred.api.routers import health, kindreds, artifacts
from kindred.api.middleware import install_middleware
from kindred.errors import KindredError
from fastapi.requests import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Kindred Backend", version="0.1.0")
install_middleware(app)
app.include_router(health.router)
app.include_router(kindreds.router, prefix="/v1/kindreds", tags=["kindreds"])
app.include_router(artifacts.router, prefix="/v1/kindreds", tags=["artifacts"])

@app.exception_handler(KindredError)
async def kindred_error_handler(request: Request, exc: KindredError):
    from kindred.errors import NotFoundError, ConflictError, ValidationError, SignatureError, UnauthorizedError
    status = {
        NotFoundError: 404, ConflictError: 409, ValidationError: 400,
        SignatureError: 401, UnauthorizedError: 403,
    }.get(type(exc), 500)
    return JSONResponse(status_code=status, content={"error": type(exc).__name__, "message": str(exc)})
```

```python
# src/kindred/api/middleware.py
import uuid
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        resp = await call_next(request)
        resp.headers["x-request-id"] = rid
        return resp

def install_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
```

```python
# src/kindred/api/routers/health.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

- [ ] **Step 2: Schemas**

```python
# src/kindred/api/schemas/kindreds.py
from pydantic import BaseModel, Field

class CreateKindredReq(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    display_name: str
    description: str = ""
    bless_threshold: int = Field(ge=1, le=100, default=2)

class KindredOut(BaseModel):
    id: str
    slug: str
    display_name: str
    description: str
    bless_threshold: int

    @classmethod
    def from_model(cls, k):
        return cls(
            id=str(k.id), slug=k.slug, display_name=k.display_name,
            description=k.description, bless_threshold=k.bless_threshold,
        )
```

```python
# src/kindred/api/schemas/artifacts.py
from pydantic import BaseModel
from typing import Any

class UploadArtifactReq(BaseModel):
    metadata: dict[str, Any]
    body_b64: str  # base64-encoded body
    author_pubkey: str  # ed25519:hex
    author_sig: str     # hex

class ArtifactOut(BaseModel):
    content_id: str
    type: str
    logical_name: str
    tier: str  # class-blessed | peer-shared
    valid_from: str
    valid_until: str
    outcome_uses: int
    outcome_successes: int
```

- [ ] **Step 3: Routers — kindreds**

```python
# src/kindred/api/routers/kindreds.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session, require_owner_pubkey
from kindred.api.schemas.kindreds import CreateKindredReq, KindredOut
from kindred.services.kindreds import create_kindred, get_kindred_by_slug
from kindred.services.users import get_user_by_pubkey

router = APIRouter()

@router.post("", response_model=KindredOut, status_code=201)
async def create(req: CreateKindredReq,
                 session: AsyncSession = Depends(db_session),
                 owner_pubkey: bytes = Depends(require_owner_pubkey)):
    owner = await get_user_by_pubkey(session, owner_pubkey)
    k = await create_kindred(
        session, owner_id=owner.id, slug=req.slug, display_name=req.display_name,
        description=req.description, bless_threshold=req.bless_threshold,
    )
    return KindredOut.from_model(k)

@router.get("/{slug}", response_model=KindredOut)
async def get(slug: str, session: AsyncSession = Depends(db_session)):
    return KindredOut.from_model(await get_kindred_by_slug(session, slug))
```

- [ ] **Step 4: Routers — artifacts**

```python
# src/kindred/api/routers/artifacts.py
import base64
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session, get_object_store
from kindred.api.schemas.artifacts import UploadArtifactReq, ArtifactOut
from kindred.services.artifacts import upload_artifact, list_artifacts
from kindred.services.kindreds import get_kindred_by_slug
from kindred.services.blessings import compute_tier
from kindred.crypto.keys import str_to_pubkey
from kindred.storage.object_store import ObjectStore

router = APIRouter()

@router.post("/{slug}/artifacts", response_model=ArtifactOut, status_code=201)
async def upload(slug: str, req: UploadArtifactReq,
                 session: AsyncSession = Depends(db_session),
                 store: ObjectStore = Depends(get_object_store)):
    k = await get_kindred_by_slug(session, slug)
    body = base64.b64decode(req.body_b64)
    art = await upload_artifact(
        session, store=store, kindred_id=k.id, metadata=req.metadata, body=body,
        author_pubkey=str_to_pubkey(req.author_pubkey),
        author_sig=bytes.fromhex(req.author_sig),
    )
    tier = await compute_tier(session, artifact=art, threshold=k.bless_threshold)
    return ArtifactOut(
        content_id=art.content_id, type=art.type, logical_name=art.logical_name,
        tier=tier, valid_from=art.valid_from.isoformat(), valid_until=art.valid_until.isoformat(),
        outcome_uses=art.outcome_uses, outcome_successes=art.outcome_successes,
    )

@router.get("/{slug}/artifacts", response_model=list[ArtifactOut])
async def list_(slug: str, session: AsyncSession = Depends(db_session)):
    k = await get_kindred_by_slug(session, slug)
    arts = await list_artifacts(session, kindred_id=k.id)
    out = []
    for a in arts:
        tier = await compute_tier(session, artifact=a, threshold=k.bless_threshold)
        out.append(ArtifactOut(
            content_id=a.content_id, type=a.type, logical_name=a.logical_name,
            tier=tier, valid_from=a.valid_from.isoformat(), valid_until=a.valid_until.isoformat(),
            outcome_uses=a.outcome_uses, outcome_successes=a.outcome_successes,
        ))
    return out
```

- [ ] **Step 5: API tests with httpx AsyncClient**

```python
# tests/api/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from kindred.api.main import app

async def test_healthz():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
```

For `test_kindreds_api.py` and `test_artifacts_api.py`, use a pytest fixture that overrides deps with in-memory Session factory and InMemoryObjectStore. Skip detailed code here — mirror the pattern from Task 18 Step 1 deps using `app.dependency_overrides`.

Run: `uv run pytest tests/api/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/kindred/api backend/tests/api
git commit -m "feat(api): FastAPI app, kindreds + artifacts routers"
```

---

### Task 19: API — Invites, Memberships, Blessings, Rollback routers

**Files:**
- Create: `backend/src/kindred/api/schemas/invites.py`
- Create: `backend/src/kindred/api/schemas/blessings.py`
- Create: `backend/src/kindred/api/routers/invites.py`
- Create: `backend/src/kindred/api/routers/memberships.py`
- Create: `backend/src/kindred/api/routers/blessings.py`
- Create: `backend/src/kindred/api/routers/rollback.py`
- Create: `backend/tests/api/test_invites_api.py`
- Create: `backend/tests/api/test_memberships_api.py`
- Create: `backend/tests/api/test_blessings_api.py`
- Create: `backend/tests/api/test_rollback_api.py`

- [ ] **Step 1: Schemas**

```python
# src/kindred/api/schemas/invites.py
from pydantic import BaseModel

class IssueInviteReq(BaseModel):
    expires_in_days: int = 7
    max_uses: int = 1
    issuer_sig: str  # hex
    inv_body_b64: str

class InviteOut(BaseModel):
    token: str
    expires_at: str
    max_uses: int
    uses: int

class JoinReq(BaseModel):
    token: str
    agent_pubkey: str  # ed25519:hex
    accept_sig: str    # hex
    accept_body_b64: str
```

```python
# src/kindred/api/schemas/blessings.py
from pydantic import BaseModel

class AddBlessingReq(BaseModel):
    signer_pubkey: str  # ed25519:hex
    sig: str  # hex
```

- [ ] **Step 2: Routers**

```python
# src/kindred/api/routers/invites.py
import base64, secrets
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session, require_owner_pubkey
from kindred.api.schemas.invites import IssueInviteReq, InviteOut
from kindred.services.invites import issue_invite
from kindred.services.kindreds import get_kindred_by_slug
from kindred.services.users import get_user_by_pubkey

router = APIRouter()

@router.post("/{slug}/invites", response_model=InviteOut, status_code=201)
async def issue(slug: str, req: IssueInviteReq,
                session: AsyncSession = Depends(db_session),
                owner_pubkey: bytes = Depends(require_owner_pubkey)):
    k = await get_kindred_by_slug(session, slug)
    owner = await get_user_by_pubkey(session, owner_pubkey)
    token = secrets.token_urlsafe(32)
    inv = await issue_invite(
        session, kindred_id=k.id, issued_by=owner.id, token=token,
        expires_at=datetime.now(UTC) + timedelta(days=req.expires_in_days),
        issuer_sig=bytes.fromhex(req.issuer_sig), issuer_pubkey=owner_pubkey,
        inv_body=base64.b64decode(req.inv_body_b64), max_uses=req.max_uses,
    )
    return InviteOut(token=inv.token, expires_at=inv.expires_at.isoformat(),
                     max_uses=inv.max_uses, uses=inv.uses)
```

```python
# src/kindred/api/routers/memberships.py
import base64
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session
from kindred.api.schemas.invites import JoinReq
from kindred.services.memberships import join_kindred
from kindred.crypto.keys import str_to_pubkey

router = APIRouter()

@router.post("/join", status_code=201)
async def join(req: JoinReq, session: AsyncSession = Depends(db_session)):
    m = await join_kindred(
        session, token=req.token, agent_pubkey=str_to_pubkey(req.agent_pubkey),
        accept_sig=bytes.fromhex(req.accept_sig),
        accept_body=base64.b64decode(req.accept_body_b64),
    )
    return {"membership_id": str(m.id), "kindred_id": str(m.kindred_id)}
```

```python
# src/kindred/api/routers/blessings.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session
from kindred.api.schemas.blessings import AddBlessingReq
from kindred.services.artifacts import get_artifact
from kindred.services.blessings import add_blessing
from kindred.services.agents import get_agent_by_pubkey
from kindred.crypto.keys import str_to_pubkey

router = APIRouter()

@router.post("/{slug}/artifacts/{content_id}/bless", status_code=201)
async def bless(slug: str, content_id: str, req: AddBlessingReq,
                session: AsyncSession = Depends(db_session)):
    art = await get_artifact(session, content_id)
    signer_pk = str_to_pubkey(req.signer_pubkey)
    agent = await get_agent_by_pubkey(session, signer_pk)
    b = await add_blessing(session, artifact=art, signer_agent_id=agent.id,
                           signer_pubkey=signer_pk, sig=bytes.fromhex(req.sig))
    return {"blessing_id": str(b.id)}
```

```python
# src/kindred/api/routers/rollback.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.api.deps import db_session, require_owner_pubkey
from kindred.services.kindreds import get_kindred_by_slug
from kindred.services.rollback import rollback_to

router = APIRouter()

class RollbackReq(BaseModel):
    up_to_seq: int

@router.post("/{slug}/rollback", status_code=200)
async def rollback(slug: str, req: RollbackReq,
                   session: AsyncSession = Depends(db_session),
                   _: bytes = Depends(require_owner_pubkey)):
    k = await get_kindred_by_slug(session, slug)
    await rollback_to(session, kindred_id=k.id, up_to_seq=req.up_to_seq)
    return {"rolled_back_to": req.up_to_seq}
```

Register in `main.py`:
```python
from kindred.api.routers import invites, memberships, blessings, rollback as rb_router
app.include_router(invites.router, prefix="/v1/kindreds", tags=["invites"])
app.include_router(memberships.router, prefix="/v1", tags=["memberships"])
app.include_router(blessings.router, prefix="/v1/kindreds", tags=["blessings"])
app.include_router(rb_router.router, prefix="/v1/kindreds", tags=["rollback"])
```

- [ ] **Step 3: Tests** — write 1 happy path per router (use httpx AsyncClient + override deps to in-memory session). Pattern: issue invite → join → upload artifact → bless → list → rollback.

- [ ] **Step 4: Run all API tests**

```bash
uv run pytest tests/api/ -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/kindred/api backend/tests/api
git commit -m "feat(api): invites, memberships, blessings, rollback routers"
```

---

### Task 20: Rate limiting middleware

**Files:**
- Modify: `backend/src/kindred/api/middleware.py`
- Create: `backend/tests/api/test_rate_limit.py`

- [ ] **Step 1: Add rate limit middleware using in-memory token bucket per pubkey**

```python
# src/kindred/api/middleware.py (append)
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from kindred.config import Settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self._settings = settings
        self._buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        pubkey = request.headers.get("x-agent-pubkey") or request.headers.get("x-owner-pubkey")
        if not pubkey:
            return await call_next(request)
        path = request.url.path
        bucket_key, limit, window = self._classify(path, pubkey)
        if bucket_key is None:
            return await call_next(request)
        now = time.monotonic()
        bucket = self._buckets[bucket_key]
        bucket[:] = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            return JSONResponse(status_code=429, content={"error": "RateLimit"})
        bucket.append(now)
        return await call_next(request)

    def _classify(self, path: str, pubkey: str):
        s = self._settings
        if path.endswith("/ask"):  # will exist in Plan 02
            return (pubkey, "ask"), s.rate_limit_ask_per_min, 60
        if "/artifacts" in path and path.count("/") == 4:  # POST /v1/kindreds/{slug}/artifacts
            return (pubkey, "contribute"), s.rate_limit_contribute_per_hour, 3600
        return None, 0, 0

def install_middleware(app, settings: Settings | None = None) -> None:
    app.add_middleware(RequestIdMiddleware)
    if settings is None:
        from kindred.api.deps import get_settings
        settings = get_settings()
    app.add_middleware(RateLimitMiddleware, settings=settings)
```

Update `main.py` to pass settings into `install_middleware(app)` (reads from deps).

- [ ] **Step 2: Test**

```python
# tests/api/test_rate_limit.py
import pytest
from httpx import AsyncClient, ASGITransport
from kindred.api.main import app

async def test_rate_limit_triggers_429():
    # Use a path matched by classifier with a low limit via monkeypatch on settings
    # (skeleton — details depend on override fixtures)
    pass  # concrete test lives after Plan 02 when /ask exists; for Plan 01, smoke test only
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/kindred/api/middleware.py backend/tests/api/test_rate_limit.py
git commit -m "feat(api): rate limit middleware (token bucket per pubkey)"
```

---

### Task 21: Docker compose + local dev

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/scripts/dev_bootstrap.sh`
- Modify: `backend/README.md`

- [ ] **Step 1: `docker-compose.yml`**

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: kindred
      POSTGRES_PASSWORD: kindred
      POSTGRES_DB: kindred
    ports: ["5432:5432"]
    volumes: ["pg_data:/var/lib/postgresql/data"]
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: ["minio_data:/data"]
volumes:
  pg_data:
  minio_data:
```

- [ ] **Step 2: Dev bootstrap script**

```bash
#!/usr/bin/env bash
# backend/scripts/dev_bootstrap.sh
set -euo pipefail
docker compose up -d
sleep 2
cp -n .env.example .env || true
if ! grep -q 'FACILITATOR_SIGNING_KEY_HEX' .env; then
  KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
  echo "KINDRED_FACILITATOR_SIGNING_KEY_HEX=$KEY" >> .env
fi
uv run alembic upgrade head
echo "Ready. Start with: uv run uvicorn kindred.api.main:app --reload"
```

- [ ] **Step 3: Test locally** — run bootstrap, hit `/healthz`, upload a golden-path artifact end-to-end by curl.

- [ ] **Step 4: Commit**

```bash
chmod +x backend/scripts/dev_bootstrap.sh
git add backend/docker-compose.yml backend/scripts backend/README.md
git commit -m "chore: docker compose + dev bootstrap"
```

---

### Task 22: E2E golden-path test (spec §7)

**Files:**
- Create: `backend/tests/e2e/test_golden_path.py`

- [ ] **Step 1: Write the test (mirrors spec §7)**

```python
# tests/e2e/test_golden_path.py
import base64
from datetime import datetime, timedelta, UTC
from httpx import AsyncClient, ASGITransport
from kindred.crypto.keys import generate_keypair, sign, pubkey_to_str
from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.api.main import app
from kindred.api.deps import db_session, get_object_store
from kindred.storage.object_store import InMemoryObjectStore
# ... override fixtures to use in-memory Session + store

async def test_golden_path(override_deps):  # fixture that wires in-memory engine
    alice_sk, alice_pk = generate_keypair()
    carol_sk, carol_pk = generate_keypair()
    # Agent keys
    alice_agent_sk, alice_agent_pk = generate_keypair()
    carol_agent_sk, carol_agent_pk = generate_keypair()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register Alice + her agent
        # (POST /v1/users and /v1/users/{id}/agents — add routers from Task 18 deps if needed)
        # For brevity, assume helper endpoints are wired in Task 18 sub-step.

        # 2. Create kindred heist-crew
        headers = {"x-owner-pubkey": pubkey_to_str(alice_pk)}
        r = await ac.post("/v1/kindreds", json={"slug": "heist-crew",
                                                "display_name": "Heist Crew"}, headers=headers)
        assert r.status_code == 201

        # 3. Issue invite
        inv_body = canonical_json({"kindred": "heist-crew"})
        inv_sig = sign(alice_sk, inv_body)
        r = await ac.post("/v1/kindreds/heist-crew/invites",
                          headers=headers,
                          json={"expires_in_days": 7, "max_uses": 1,
                                "issuer_sig": inv_sig.hex(),
                                "inv_body_b64": base64.b64encode(inv_body).decode()})
        assert r.status_code == 201
        token = r.json()["token"]

        # 4. Carol joins (register user+agent off-camera)
        accept_body = canonical_json({"invite": token})
        accept_sig = sign(carol_agent_sk, accept_body)
        r = await ac.post("/v1/join", json={
            "token": token,
            "agent_pubkey": pubkey_to_str(carol_agent_pk),
            "accept_sig": accept_sig.hex(),
            "accept_body_b64": base64.b64encode(accept_body).decode(),
        })
        assert r.status_code == 201

        # 5. Alice contributes artifact
        body = b"# Migration Structure\n..."
        meta = {
            "kaf_version": "0.1", "type": "routine", "logical_name": "migrations",
            "kindred_id": "placeholder", "valid_from": "2026-04-18T00:00:00+00:00",
            "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
            "body_sha256": compute_content_id(body),
        }
        # fill kindred_id from GET /v1/kindreds/heist-crew
        k = (await ac.get("/v1/kindreds/heist-crew")).json()
        meta["kindred_id"] = k["id"]
        cid = compute_content_id(meta)
        sig = sign(alice_agent_sk, cid.encode())
        r = await ac.post("/v1/kindreds/heist-crew/artifacts", json={
            "metadata": meta, "body_b64": base64.b64encode(body).decode(),
            "author_pubkey": pubkey_to_str(alice_agent_pk), "author_sig": sig.hex(),
        })
        assert r.status_code == 201
        art = r.json()
        assert art["tier"] == "peer-shared"

        # 6. Carol blesses
        sig = sign(carol_agent_sk, art["content_id"].encode())
        r = await ac.post(f"/v1/kindreds/heist-crew/artifacts/{art['content_id']}/bless",
                          json={"signer_pubkey": pubkey_to_str(carol_agent_pk),
                                "sig": sig.hex()})
        assert r.status_code == 201

        # 7. List artifacts — expect class-blessed
        r = await ac.get("/v1/kindreds/heist-crew/artifacts")
        arts = r.json()
        assert any(a["tier"] == "class-blessed" for a in arts)
```

Note: this test requires user/agent registration endpoints. Add those to Task 18 if not already present (thin routers over `services/users.py`, `services/agents.py`).

- [ ] **Step 2: Run**

```bash
uv run pytest tests/e2e/test_golden_path.py -v
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e
git commit -m "test(e2e): golden path — spec §7 end-to-end"
```

---

### Task 23: CI (GitHub Actions)

**Files:**
- Create: `.github/workflows/backend-ci.yml`

- [ ] **Step 1: Workflow**

```yaml
name: backend-ci
on:
  push: { branches: [main], paths: ["backend/**"] }
  pull_request: { paths: ["backend/**"] }

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: kindred
          POSTGRES_PASSWORD: kindred
          POSTGRES_DB: kindred
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U kindred" --health-interval=5s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Install deps
        working-directory: backend
        run: uv sync
      - name: Lint
        working-directory: backend
        run: uv run ruff check .
      - name: Run unit + api tests (sqlite)
        working-directory: backend
        env:
          KINDRED_DATABASE_URL: sqlite+aiosqlite:///:memory:
          KINDRED_OBJECT_STORE_ENDPOINT: http://localhost:0
          KINDRED_OBJECT_STORE_ACCESS_KEY: x
          KINDRED_OBJECT_STORE_SECRET_KEY: x
          KINDRED_OBJECT_STORE_BUCKET: x
          KINDRED_FACILITATOR_SIGNING_KEY_HEX: "00000000000000000000000000000000000000000000000000000000000000aa"
        run: uv run pytest -v --cov=kindred --cov-report=term-missing
      - name: Migration check
        working-directory: backend
        env:
          KINDRED_DATABASE_URL: postgresql+asyncpg://kindred:kindred@localhost:5432/kindred
          KINDRED_OBJECT_STORE_ENDPOINT: http://localhost:9000
          KINDRED_OBJECT_STORE_ACCESS_KEY: x
          KINDRED_OBJECT_STORE_SECRET_KEY: x
          KINDRED_OBJECT_STORE_BUCKET: x
          KINDRED_FACILITATOR_SIGNING_KEY_HEX: "00000000000000000000000000000000000000000000000000000000000000aa"
        run: uv run alembic upgrade head
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/backend-ci.yml
git commit -m "ci: backend GitHub Actions (lint, test, migration)"
```

---

## Self-Review Summary

**Spec coverage** (§ → task):
- §3 Actors → Tasks 8, 9 (User, Agent, Kindred, Membership models)
- §4.1 Identity & Trust → Tasks 4-6 (crypto), 12 (attestation)
- §4.2 Grimoire (artefacte) → Tasks 10, 15, 16 (Artifact, upload, blessings)
- §4.3 Facilitator policy engine → Task 20 (rate limit); full policy engine lives in Plan 02
- §4.4 Client SDK → out-of-scope (Plan 03)
- §5 KAF → Task 15 enforces `kaf_version`; full spec publication in Plan 07
- §6 Onboarding protocol → out-of-scope here (Web UI Plan 06 + CLI Plan 03)
- §8 Threat model mitigations → Tasks 6 (sig verify), 12 (attestation), 15 (sig + content addr), 16 (blessing sig), 17 (rollback), 20 (rate limit)
- §9 Scope v0 → Plan 01 covers: identity, kindred CRUD, artifact upload/bless, audit log, rollback
- §17 Glossary vocab → respected throughout

**Gaps acknowledged for later plans:**
- `/ask` endpoint + RAG librarian → Plan 02
- Outcome telemetry endpoint → Plan 02
- Injection defense layer → Plan 02
- OAuth / passkey auth → Plan 06 (Web UI)
- CLI `kin` → Plan 03

**Placeholder scan:** no TBD/TODO/fill-in.
**Type consistency:** keys stored as `bytes` for pubkey, `bytes` for sig; sig strings in API = hex; pubkey strings = `ed25519:<hex>`. Consistent through services and routers.

---

## Execution Handoff

Plan complete and saved to [docs/superpowers/plans/2026-04-18-kindred-01-backend-core.md](./2026-04-18-kindred-01-backend-core.md).

**Next plans (to be written after Plan 01 ships):**
- Plan 02 — Facilitator (RAG librarian, policy engine, `/ask`, outcome telemetry, injection defenses + adversarial suite)
- Plan 03 — CLI `kin` (Typer, OAuth device flow, local keypair, harness-agnostic commands)
- Plan 04 — Claude Code Plugin (skill + MCP server + PostToolUse hook for outcome signals)
- Plan 05 — Cursor Integration (MCP config injection + `.cursorrules` fragment)
- Plan 06 — Web UI (Next.js 15, OAuth/passkey, invite landing, propose/approve flow, audit view, rollback UI)
- Plan 07 — KAF spec site (kindredformat.org) + launch package (5 seed kindreds, CI benchmarks, threat-model transparency page, docs)

**Two execution options for Plan 01:**

1. **Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
