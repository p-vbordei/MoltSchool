from sqlalchemy import select
from kindred.models.artifact import Artifact
from kindred.services.rollback import list_events, rollback_to
from tests.helpers import make_user_agent_kindred_artifact


async def test_rollback_retains_events_before_point(db_session):
    art, *_ = await make_user_agent_kindred_artifact(db_session)
    events_before = await list_events(db_session, kindred_id=art.kindred_id)
    assert len(events_before) >= 2  # kindred_created + artifact_uploaded
    cutoff_seq = events_before[0].seq  # after kindred_created
    await rollback_to(db_session, kindred_id=art.kindred_id, up_to_seq=cutoff_seq)
    remaining = list((await db_session.execute(
        select(Artifact).where(Artifact.kindred_id == art.kindred_id)
    )).scalars())
    assert len(remaining) == 0
