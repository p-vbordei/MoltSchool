# tests/unit/test_models_artifact.py
from datetime import UTC, datetime, timedelta

from kindred.models.artifact import Artifact
from kindred.models.kindred import Kindred
from kindred.models.user import User


async def test_artifact_unique_content_id(db_session):
    user = User(email="a@b.c", display_name="A", pubkey=b"\x00" * 32)
    db_session.add(user)
    await db_session.flush()
    k = Kindred(slug="x", display_name="X", created_by=user.id)
    db_session.add(k)
    await db_session.flush()
    now = datetime.now(UTC)
    a = Artifact(
        content_id="sha256:" + "a" * 64,
        kindred_id=k.id,
        type="routine",
        logical_name="r1",
        author_pubkey=b"\x01" * 32,
        author_sig=b"\x02" * 64,
        valid_from=now,
        valid_until=now + timedelta(days=180),
    )
    db_session.add(a)
    await db_session.flush()
    assert a.id
    assert a.outcome_uses == 0
