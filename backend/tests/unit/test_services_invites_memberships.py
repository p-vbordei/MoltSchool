from datetime import UTC, datetime, timedelta

import pytest

from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.errors import SignatureError, ValidationError
from kindred.services.agents import register_agent
from kindred.services.invites import issue_invite
from kindred.services.kindreds import create_kindred
from kindred.services.memberships import join_kindred
from kindred.services.users import register_user


async def _register_user_and_agent(db_session, email):
    owner_sk, owner_pk = generate_keypair()
    u = await register_user(
        db_session, email=email, display_name=email, pubkey=owner_pk
    )
    agent_sk, agent_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    attest_payload = canonical_json(
        {
            "agent_pubkey": pubkey_to_str(agent_pk),
            "scope": scope,
            "expires_at": expires.isoformat(),
        }
    )
    att_sig = sign(owner_sk, attest_payload)
    a = await register_agent(
        db_session,
        owner_id=u.id,
        agent_pubkey=agent_pk,
        display_name=f"{email}-bot",
        scope=scope,
        expires_at=expires,
        sig=att_sig,
    )
    return u, owner_sk, owner_pk, a, agent_sk, agent_pk


async def test_issue_and_redeem_invite(db_session):
    alice, alice_sk, alice_pk, _, _, _ = await _register_user_and_agent(
        db_session, "alice@x"
    )
    k = await create_kindred(
        db_session, owner_id=alice.id, slug="x", display_name="X"
    )

    inv_body = canonical_json({"kindred_id": str(k.id), "token_prefix": "t"})
    inv_sig = sign(alice_sk, inv_body)
    token = "t" + "0" * 31
    inv = await issue_invite(
        db_session,
        kindred_id=k.id,
        issued_by=alice.id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        issuer_sig=inv_sig,
        issuer_pubkey=alice_pk,
        inv_body=inv_body,
        max_uses=1,
    )
    assert inv.token == token

    _bob, _, _bob_pk, _bob_agent, bob_agent_sk, bob_agent_pk = (
        await _register_user_and_agent(db_session, "bob@x")
    )
    accept_body = canonical_json(
        {"invite_token": token, "agent_pubkey": pubkey_to_str(bob_agent_pk)}
    )
    accept_sig = sign(bob_agent_sk, accept_body)
    m = await join_kindred(
        db_session,
        token=token,
        agent_pubkey=bob_agent_pk,
        accept_sig=accept_sig,
        accept_body=accept_body,
    )
    assert m.kindred_id == k.id


async def test_invite_bad_issuer_sig_raises(db_session):
    alice, _alice_sk, alice_pk, *_ = await _register_user_and_agent(
        db_session, "alice@x"
    )
    k = await create_kindred(
        db_session, owner_id=alice.id, slug="x", display_name="X"
    )
    with pytest.raises(SignatureError):
        await issue_invite(
            db_session,
            kindred_id=k.id,
            issued_by=alice.id,
            token="t" * 32,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            issuer_sig=b"\x00" * 64,
            issuer_pubkey=alice_pk,
            inv_body=b"body",
        )


async def test_invite_expired_rejected(db_session):
    alice, alice_sk, alice_pk, *_ = await _register_user_and_agent(
        db_session, "alice@x"
    )
    k = await create_kindred(
        db_session, owner_id=alice.id, slug="x", display_name="X"
    )
    inv_body = canonical_json({"kindred_id": str(k.id)})
    inv_sig = sign(alice_sk, inv_body)
    await issue_invite(
        db_session,
        kindred_id=k.id,
        issued_by=alice.id,
        token="t" * 32,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        issuer_sig=inv_sig,
        issuer_pubkey=alice_pk,
        inv_body=inv_body,
    )
    _, _, _, _, _bob_agent_sk, bob_agent_pk = await _register_user_and_agent(
        db_session, "bob@x"
    )
    with pytest.raises(ValidationError):
        await join_kindred(
            db_session,
            token="t" * 32,
            agent_pubkey=bob_agent_pk,
            accept_sig=b"\x00" * 64,
            accept_body=b"{}",
        )
