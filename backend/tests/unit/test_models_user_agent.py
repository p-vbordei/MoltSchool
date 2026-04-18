# tests/unit/test_models_user_agent.py
from datetime import UTC, datetime, timedelta

from kindred.models.agent import Agent
from kindred.models.user import User


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
