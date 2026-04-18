"""End-to-end: kin commands against a live backend via ASGITransport.

Skipped by default; run with `KINDRED_E2E=1 uv sync --group e2e && KINDRED_E2E=1 uv run pytest -m slow`.
"""
from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio

from kindred_client import crypto

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.getenv("KINDRED_E2E") != "1",
        reason="set KINDRED_E2E=1 to run end-to-end tests",
    ),
]

# Guard the backend import so non-e2e runs don't explode collecting this file.
try:
    from httpx import ASGITransport
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from kindred.api.deps import db_session as backend_db_session
    from kindred.api.deps import get_object_store
    from kindred.api.main import app as backend_app
    from kindred.models import (  # noqa: F401 — register tables
        agent, artifact, audit, event, invite, kindred, membership, user,
    )
    from kindred.models.base import Base
    from kindred.storage.object_store import InMemoryObjectStore

    HAS_BACKEND = True
except Exception:  # pragma: no cover — backend group not installed
    HAS_BACKEND = False

if not HAS_BACKEND:
    pytestmark.append(pytest.mark.skip(reason="backend package not installed"))


@pytest_asyncio.fixture
async def backend_transport():
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

    backend_app.dependency_overrides[backend_db_session] = override_db_session
    backend_app.dependency_overrides[get_object_store] = override_get_object_store
    try:
        yield ASGITransport(app=backend_app)
    finally:
        backend_app.dependency_overrides.clear()
        await engine.dispose()


@pytest_asyncio.fixture
def patch_api_client(monkeypatch, backend_transport):
    """Monkeypatch KindredAPI._client to build an AsyncClient on the ASGI transport."""
    from kindred_client import api_client as api_mod

    def _client(self: api_mod.KindredAPI) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=backend_transport, base_url="http://backend.local", timeout=5
        )

    monkeypatch.setattr(api_mod.KindredAPI, "_client", _client)
    return _client


async def test_full_cli_flow_against_live_backend(fake_home, patch_api_client):
    """Register owner+kindred+invite directly via API, then drive kin join → ask → contribute → ask."""
    from kindred_client.api_client import KindredAPI
    from kindred_client.commands.join import _run_join

    backend = "http://backend.local"
    api = KindredAPI(backend)

    # Step 1: set up owner + kindred + invite on the backend (as the "kindred creator").
    owner_sk, owner_pk = crypto.generate_keypair()
    await api.create_user("owner@x", "Owner", owner_pk)
    await api.create_kindred(
        owner_pubkey=owner_pk,
        slug="heist",
        display_name="Heist",
        description="",
        bless_threshold=2,
    )
    # Mint an invite as owner.
    k = await api.get_kindred_by_slug("heist")
    # The backend generates the invite token; we sign a body bound to a
    # placeholder token value (the backend only verifies the sig over our body,
    # not that the token inside matches).
    server_token_placeholder = "tok-e2e-" + owner_pk.hex()[:16]
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    inv_body = crypto.canonical_json(
        {
            "kindred_id": k["id"],
            "token": server_token_placeholder,
            "expires_at": expires,
        }
    )
    issuer_sig = crypto.sign(owner_sk, inv_body)
    async with api._client() as c:  # noqa: SLF001
        r = await c.post(
            "/v1/kindreds/heist/invites",
            json={
                "expires_in_days": 7,
                "max_uses": 1,
                "issuer_sig": issuer_sig.hex(),
                "inv_body_b64": base64.b64encode(inv_body).decode(),
            },
            headers={"x-owner-pubkey": crypto.pubkey_to_str(owner_pk)},
        )
        assert r.status_code == 201, r.text
        real_token = r.json()["token"]

    invite_url = f"{backend}/k/heist?inv={real_token}"

    # Step 2: kin join (different user, different keypair).
    result = await _run_join(invite_url, email="joiner@x", display_name="Joiner")
    assert result["slug"] == "heist"

    # Step 3: kin ask — empty grimoire → 0 artifacts.
    from kindred_client.config import load_config
    from kindred_client.keystore import load_keypair

    cfg = load_config()
    _, ag_pk = load_keypair(cfg.active_agent_id)
    resp = await api.ask(slug="heist", agent_pubkey=ag_pk, query="how do we start?")
    assert resp["artifacts"] == []
    assert resp["audit_id"]

    # Step 4: kin contribute — upload a routine.
    from kindred_client.commands.contribute import build_metadata

    ag_sk, _ = load_keypair(cfg.active_agent_id)
    body = b"# Runbook\n1. review\n2. ship"
    metadata = build_metadata(
        type_="routine", logical_name="runbook", kindred_id=k["id"], body=body
    )
    cid = crypto.compute_content_id(metadata)
    sig = crypto.sign(ag_sk, cid.encode())
    art = await api.upload_artifact(
        slug="heist",
        metadata=metadata,
        body=body,
        author_pubkey=ag_pk,
        author_sig=sig,
    )
    assert art["content_id"] == cid

    # Step 5: ask again — the artifact is unblessed (peer-shared tier), so we opt in.
    resp2 = await api.ask(
        slug="heist",
        agent_pubkey=ag_pk,
        query="how do we ship?",
        include_peer_shared=True,
    )
    assert len(resp2["artifacts"]) >= 1
    cids = [a["content_id"] for a in resp2["artifacts"]]
    assert cid in cids
