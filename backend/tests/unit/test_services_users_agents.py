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
