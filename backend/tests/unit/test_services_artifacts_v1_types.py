"""Tests for KAF v1 types: repo_ref, conversation_distilled, benchmark_ref."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.errors import ValidationError
from kindred.services.agents import register_agent
from kindred.services.artifacts import upload_artifact
from kindred.services.kindreds import create_kindred
from kindred.services.users import register_user
from kindred.storage.object_store import InMemoryObjectStore


async def _setup(db_session, email="v1@x", slug="v1"):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    await register_agent(
        db_session, owner_id=u.id, agent_pubkey=ag_pk,
        display_name="x", scope=scope, expires_at=expires, sig=att_sig,
    )
    k = await create_kindred(db_session, owner_id=u.id, slug=slug, display_name="X")
    return ag_sk, ag_pk, k


def _envelope(
    type_name: str, body: bytes, kindred_id, logical_name: str,
    extra: dict | None = None,
):
    metadata = {
        "kaf_version": "0.1",
        "type": type_name,
        "logical_name": logical_name,
        "kindred_id": str(kindred_id),
        "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00",
        "tags": [],
        "body_sha256": compute_content_id(body),
    }
    if extra:
        metadata.update(extra)
    return metadata


async def _upload(db_session, ag_sk, ag_pk, k, metadata, body):
    store = InMemoryObjectStore()
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    return await upload_artifact(
        db_session, store=store, kindred_id=k.id, metadata=metadata, body=body,
        author_pubkey=ag_pk, author_sig=sig,
    )


# --- repo_ref -----------------------------------------------------------------

async def test_upload_repo_ref_happy(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="rr1@x", slug="rr1")
    body = json.dumps({
        "repo_url": "https://github.com/kindred/backend",
        "commit_sha": "a" * 40,
        "summary": "Kindred backend — KAF signing + artifact service.",
        "vetted_at": "2026-04-18T00:00:00+00:00",
    }).encode()
    meta = _envelope("repo_ref", body, k.id, "repo-kindred-backend")
    art = await _upload(db_session, ag_sk, ag_pk, k, meta, body)
    assert art.type == "repo_ref"


async def test_upload_repo_ref_rejects_non_https(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="rr2@x", slug="rr2")
    body = json.dumps({
        "repo_url": "http://github.com/x/y",
        "commit_sha": "b" * 40,
        "summary": "ok",
    }).encode()
    meta = _envelope("repo_ref", body, k.id, "bad-scheme")
    with pytest.raises(ValidationError, match="https"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)


async def test_upload_repo_ref_rejects_bad_commit_sha(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="rr3@x", slug="rr3")
    body = json.dumps({
        "repo_url": "https://github.com/x/y",
        "commit_sha": "ZZZ",
        "summary": "ok",
    }).encode()
    meta = _envelope("repo_ref", body, k.id, "bad-sha")
    with pytest.raises(ValidationError, match="commit_sha"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)


async def test_upload_repo_ref_rejects_missing_summary(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="rr4@x", slug="rr4")
    body = json.dumps({
        "repo_url": "https://github.com/x/y",
        "commit_sha": "c" * 40,
    }).encode()
    meta = _envelope("repo_ref", body, k.id, "no-summary")
    with pytest.raises(ValidationError, match="summary"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)


# --- conversation_distilled ---------------------------------------------------

async def test_upload_conversation_distilled_happy(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="cd1@x", slug="cd1")
    body = b"# Q: How do we pin commits?\nA: Record the sha256 at vetting time."
    meta = _envelope(
        "conversation_distilled", body, k.id, "convo-pin-commits",
        extra={"source_audit_id": str(uuid4())},
    )
    art = await _upload(db_session, ag_sk, ag_pk, k, meta, body)
    assert art.type == "conversation_distilled"


async def test_upload_conversation_distilled_rejects_missing_source_audit_id(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="cd2@x", slug="cd2")
    body = b"# Q&A without provenance"
    meta = _envelope("conversation_distilled", body, k.id, "convo-no-src")
    with pytest.raises(ValidationError, match="source_audit_id"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)


# --- benchmark_ref ------------------------------------------------------------

async def test_upload_benchmark_ref_happy(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="bm1@x", slug="bm1")
    body = json.dumps({
        "harness_url": "https://github.com/kindred/bench/tree/main/harnesses/injection",
        "script_sha256": "sha256:" + "d" * 64,
        "last_pass_ts": "2026-04-18T00:00:00+00:00",
        "runtime_seconds": 42,
    }).encode()
    meta = _envelope("benchmark_ref", body, k.id, "bench-injection")
    art = await _upload(db_session, ag_sk, ag_pk, k, meta, body)
    assert art.type == "benchmark_ref"


async def test_upload_benchmark_ref_rejects_bad_script_sha(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="bm2@x", slug="bm2")
    body = json.dumps({
        "harness_url": "https://github.com/x/y",
        "script_sha256": "sha1:deadbeef",
        "last_pass_ts": "2026-04-18T00:00:00+00:00",
        "runtime_seconds": 10,
    }).encode()
    meta = _envelope("benchmark_ref", body, k.id, "bad-script-sha")
    with pytest.raises(ValidationError, match="script_sha256"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)


async def test_upload_benchmark_ref_rejects_zero_runtime(db_session):
    ag_sk, ag_pk, k = await _setup(db_session, email="bm3@x", slug="bm3")
    body = json.dumps({
        "harness_url": "https://github.com/x/y",
        "script_sha256": "sha256:" + "e" * 64,
        "last_pass_ts": "2026-04-18T00:00:00+00:00",
        "runtime_seconds": 0,
    }).encode()
    meta = _envelope("benchmark_ref", body, k.id, "zero-runtime")
    with pytest.raises(ValidationError, match="runtime_seconds"):
        await _upload(db_session, ag_sk, ag_pk, k, meta, body)
