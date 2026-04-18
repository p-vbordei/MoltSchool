# tests/unit/test_models_kindred.py
from datetime import UTC, datetime, timedelta

from kindred.models.invite import Invite
from kindred.models.kindred import Kindred
from kindred.models.user import User


async def test_create_kindred(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="heist-crew", display_name="Heist Crew", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    assert k.bless_threshold == 2


async def test_invite_defaults(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    inv = Invite(
        kindred_id=k.id,
        issued_by=user.id,
        token="t" * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        issuer_sig=b"\x00" * 64,
    )
    db_session.add(inv)
    await db_session.flush()
    assert inv.uses == 0
    assert inv.max_uses == 1
    assert not inv.revoked
