# tests/unit/test_models_audit_event.py
import pytest
from sqlalchemy.exc import IntegrityError

from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.models.kindred import Kindred
from kindred.models.user import User


async def test_audit_log_entry(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    entry = AuditLog(
        kindred_id=k.id,
        agent_pubkey=b"\x01" * 32,
        action="ask",
        payload={"q": "hi"},
        facilitator_sig=b"\x02" * 64,
        seq=1,
    )
    db_session.add(entry)
    await db_session.flush()
    assert entry.id


async def test_event_appends(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    e = Event(kindred_id=k.id, seq=1, event_type="kindred_created", payload={"slug": "x"})
    db_session.add(e)
    await db_session.flush()
    assert e.id


async def test_event_seq_unique(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    db_session.add(Event(kindred_id=k.id, seq=1, event_type="x", payload={}))
    await db_session.flush()
    db_session.add(Event(kindred_id=k.id, seq=1, event_type="y", payload={}))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_audit_log_seq_unique(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    db_session.add(
        AuditLog(
            kindred_id=k.id,
            agent_pubkey=b"\x01" * 32,
            action="ask",
            payload={},
            facilitator_sig=b"\x02" * 64,
            seq=1,
        )
    )
    await db_session.flush()
    db_session.add(
        AuditLog(
            kindred_id=k.id,
            agent_pubkey=b"\x03" * 32,
            action="contribute",
            payload={},
            facilitator_sig=b"\x04" * 64,
            seq=1,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
