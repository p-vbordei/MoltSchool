from datetime import UTC, datetime, timedelta

import pytest

from kindred.crypto.keys import generate_keypair
from kindred.errors import UnauthorizedError
from kindred.facilitator.policy import (
    filter_by_tier,
    require_agent_authorized,
    require_member,
    require_not_expired,
    require_scope,
)
from tests.helpers import make_full_setup


@pytest.mark.asyncio
async def test_require_member_accepts_joined_agent(db_session):
    setup = await make_full_setup(db_session)
    await require_member(
        db_session, agent_pubkey=setup["ag_pk"], kindred_id=setup["kindred"].id
    )  # no raise


@pytest.mark.asyncio
async def test_require_member_rejects_stranger(db_session):
    setup = await make_full_setup(db_session)
    _, stranger_pk = generate_keypair()
    with pytest.raises(UnauthorizedError):
        await require_member(
            db_session, agent_pubkey=stranger_pk, kindred_id=setup["kindred"].id
        )


def test_require_scope_wildcard_kindred():
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    require_scope(scope, action="read", kindred_slug="anything")


def test_require_scope_specific_kindred():
    scope = {"kindreds": ["x"], "actions": ["read"]}
    require_scope(scope, action="read", kindred_slug="x")
    with pytest.raises(UnauthorizedError):
        require_scope(scope, action="read", kindred_slug="y")


def test_require_scope_rejects_unauthorized_action():
    scope = {"kindreds": ["*"], "actions": ["read"]}
    with pytest.raises(UnauthorizedError):
        require_scope(scope, action="contribute", kindred_slug="x")


def test_require_scope_accepts_json_string():
    import json

    s = json.dumps({"kindreds": ["*"], "actions": ["read"]})
    require_scope(s, action="read", kindred_slug="x")


def test_require_not_expired_future():
    require_not_expired(datetime.now(UTC) + timedelta(days=1))


def test_require_not_expired_past():
    with pytest.raises(UnauthorizedError):
        require_not_expired(datetime.now(UTC) - timedelta(days=1))


def test_require_not_expired_naive_datetime():
    # A naive datetime should be treated as UTC
    require_not_expired(datetime.now() + timedelta(days=1))


@pytest.mark.asyncio
async def test_require_agent_authorized_happy(db_session):
    setup = await make_full_setup(db_session)
    await require_agent_authorized(
        db_session, agent_pubkey=setup["ag_pk"], kindred_id=setup["kindred"].id,
        kindred_slug=setup["kindred"].slug, action="read",
    )


@pytest.mark.asyncio
async def test_require_agent_authorized_non_member(db_session):
    setup = await make_full_setup(db_session)
    _, stranger_pk = generate_keypair()
    with pytest.raises(UnauthorizedError):
        await require_agent_authorized(
            db_session, agent_pubkey=stranger_pk, kindred_id=setup["kindred"].id,
            kindred_slug=setup["kindred"].slug, action="read",
        )


@pytest.mark.asyncio
async def test_require_agent_authorized_bad_action(db_session):
    setup = await make_full_setup(db_session)
    # The test helper gives agents ["contribute", "read"] — so "bless" is out of scope
    with pytest.raises(UnauthorizedError):
        await require_agent_authorized(
            db_session, agent_pubkey=setup["ag_pk"], kindred_id=setup["kindred"].id,
            kindred_slug=setup["kindred"].slug, action="bless",
        )


def test_filter_by_tier_strips_peer_shared_by_default():
    # stand-in artefact objects — the function only needs the tuple shape
    pairs = [("A", "class-blessed"), ("B", "peer-shared"), ("C", "class-blessed")]
    out = filter_by_tier(pairs)
    assert [a for a, _ in out] == ["A", "C"]


def test_filter_by_tier_includes_peer_when_requested():
    pairs = [("A", "class-blessed"), ("B", "peer-shared")]
    out = filter_by_tier(pairs, include_peer_shared=True)
    assert len(out) == 2
