# tests/unit/test_audit_race.py
"""Race-condition coverage for append_audit / append_event.

_next_seq uses SELECT max(seq)+1 which races between SELECT and INSERT under
concurrent writers. The (kindred_id, seq) UNIQUE constraint makes collisions
fail with IntegrityError. These tests verify the service retries cleanly.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from kindred.crypto.keys import generate_keypair
from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.models.kindred import Kindred
from kindred.models.user import User
from kindred.services.audit import append_audit, append_event


async def _user_and_kindred(db_session, email="r@x", slug="r"):
    u = User(email=email, display_name=email, pubkey=b"\x00" * 32)
    db_session.add(u)
    await db_session.flush()
    k = Kindred(slug=slug, display_name="R", created_by=u.id)
    db_session.add(k)
    await db_session.flush()
    return u, k


async def test_append_event_retries_on_seq_collision(db_session):
    """Pre-insert an Event with seq=1 so _next_seq returns 1, then a naive
    insert collides. The retry loop should pick up a fresh max and succeed."""
    _u, k = await _user_and_kindred(db_session)
    # Pre-insert so current max is 0 → _next_seq returns 1, but we also add a
    # conflicting row with seq=1 that the first attempt will collide with.
    # To simulate: we write the pre-existing row with seq=1 directly, then
    # call append_event. It will compute seq=max+1=2 on the first try (no
    # collision). To *force* a collision we instead inject a conflicting
    # unflushed row at seq N+1 before the service flushes.
    # Simpler approach: monkeypatch _next_seq to return a stale value on
    # first call so the insert collides.
    from kindred.services import audit as audit_mod

    # Pre-insert seq=1 so a stale return value of 1 will collide.
    db_session.add(Event(kindred_id=k.id, seq=1, event_type="seed", payload={}))
    await db_session.flush()

    real_next_seq = audit_mod._next_seq
    call_count = {"n": 0}

    async def flaky_next_seq(session, kindred_id, table):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Stale read: collides with pre-inserted seq=1
            return 1
        return await real_next_seq(session, kindred_id, table)

    audit_mod._next_seq = flaky_next_seq
    try:
        e = await append_event(
            db_session, kindred_id=k.id, event_type="test", payload={"x": 1}
        )
    finally:
        audit_mod._next_seq = real_next_seq

    assert e.id is not None
    assert e.seq == 2  # retry used fresh max+1
    assert call_count["n"] >= 2  # retried at least once


async def test_append_audit_retries_on_seq_collision(db_session):
    """Same scenario for append_audit."""
    _u, k = await _user_and_kindred(db_session)
    _sk, _pk = generate_keypair()
    facilitator_sk = b"\xaa" * 32

    db_session.add(
        AuditLog(
            kindred_id=k.id,
            agent_pubkey=b"\x01" * 32,
            action="seed",
            payload={},
            facilitator_sig=b"\x02" * 64,
            seq=1,
        )
    )
    await db_session.flush()

    from kindred.services import audit as audit_mod

    real_next_seq = audit_mod._next_seq
    call_count = {"n": 0}

    async def flaky_next_seq(session, kindred_id, table):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return 1  # stale → collision with pre-inserted seq=1
        return await real_next_seq(session, kindred_id, table)

    audit_mod._next_seq = flaky_next_seq
    try:
        entry = await append_audit(
            db_session,
            kindred_id=k.id,
            agent_pubkey=b"\x03" * 32,
            action="ask",
            payload={"q": "hi"},
            facilitator_sk=facilitator_sk,
        )
    finally:
        audit_mod._next_seq = real_next_seq

    assert entry.id is not None
    assert entry.seq == 2
    assert call_count["n"] >= 2


async def test_append_event_gives_up_after_max_attempts(db_session):
    """If the collision keeps recurring (e.g. _next_seq is broken), we must
    eventually raise IntegrityError rather than loop forever."""
    _u, k = await _user_and_kindred(db_session)
    db_session.add(Event(kindred_id=k.id, seq=1, event_type="seed", payload={}))
    await db_session.flush()

    from kindred.services import audit as audit_mod

    real_next_seq = audit_mod._next_seq

    async def always_stale(session, kindred_id, table):
        return 1  # always collides

    audit_mod._next_seq = always_stale
    try:
        with pytest.raises(IntegrityError):
            await append_event(
                db_session, kindred_id=k.id, event_type="x", payload={}
            )
    finally:
        audit_mod._next_seq = real_next_seq
