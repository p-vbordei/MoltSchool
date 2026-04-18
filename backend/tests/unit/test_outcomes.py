from uuid import uuid4

import pytest

from kindred.config import Settings
from kindred.errors import NotFoundError, ValidationError
from kindred.facilitator.outcomes import OutcomeResult, report_outcome
from kindred.services.audit import append_audit
from tests.helpers import make_full_setup


@pytest.mark.asyncio
async def test_report_outcome_success_increments_uses_and_successes(db_session):
    setup = await make_full_setup(db_session)
    art = setup["art"]
    audit = await append_audit(
        db_session, kindred_id=setup["kindred"].id, agent_pubkey=setup["ag_pk"],
        action="ask", payload={"artifact_ids_returned": [art.content_id], "query": "q"},
        facilitator_sk=Settings().facilitator_signing_key,
    )
    await report_outcome(
        db_session, audit_id=audit.id, result=OutcomeResult.SUCCESS, notes="ok",
    )
    await db_session.refresh(art)
    assert art.outcome_uses == 1
    assert art.outcome_successes == 1


@pytest.mark.asyncio
async def test_report_outcome_fail_increments_only_uses(db_session):
    setup = await make_full_setup(db_session)
    art = setup["art"]
    audit = await append_audit(
        db_session, kindred_id=setup["kindred"].id, agent_pubkey=setup["ag_pk"],
        action="ask", payload={"artifact_ids_returned": [art.content_id], "query": "q"},
        facilitator_sk=Settings().facilitator_signing_key,
    )
    await report_outcome(
        db_session, audit_id=audit.id, result=OutcomeResult.FAIL,
    )
    await db_session.refresh(art)
    assert art.outcome_uses == 1
    assert art.outcome_successes == 0


@pytest.mark.asyncio
async def test_report_outcome_partial_counts_as_success(db_session):
    setup = await make_full_setup(db_session)
    art = setup["art"]
    audit = await append_audit(
        db_session, kindred_id=setup["kindred"].id, agent_pubkey=setup["ag_pk"],
        action="ask", payload={"artifact_ids_returned": [art.content_id], "query": "q"},
        facilitator_sk=Settings().facilitator_signing_key,
    )
    await report_outcome(
        db_session, audit_id=audit.id, result=OutcomeResult.PARTIAL,
    )
    await db_session.refresh(art)
    assert art.outcome_successes == 1


@pytest.mark.asyncio
async def test_report_outcome_unknown_audit_raises(db_session):
    await make_full_setup(db_session)
    with pytest.raises(NotFoundError):
        await report_outcome(
            db_session, audit_id=uuid4(), result=OutcomeResult.SUCCESS,
        )


@pytest.mark.asyncio
async def test_report_outcome_invalid_result_raises(db_session):
    setup = await make_full_setup(db_session)
    art = setup["art"]
    audit = await append_audit(
        db_session, kindred_id=setup["kindred"].id, agent_pubkey=setup["ag_pk"],
        action="ask", payload={"artifact_ids_returned": [art.content_id]},
        facilitator_sk=Settings().facilitator_signing_key,
    )
    with pytest.raises(ValidationError):
        await report_outcome(
            db_session, audit_id=audit.id, result="garbage",
        )
