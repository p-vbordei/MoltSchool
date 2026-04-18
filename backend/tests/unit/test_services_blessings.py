import pytest

from kindred.crypto.keys import sign
from kindred.errors import ConflictError, SignatureError
from kindred.models.artifact import Blessing
from kindred.services.blessings import add_blessing, compute_tier


async def test_add_blessing_ok(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    sig = sign(ag_sk, art.content_id.encode())
    b = await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=sig)
    assert b.id


async def test_blessing_bad_sig(db_session, artifact_and_agent):
    art, _, ag_pk, agent_id = artifact_and_agent
    with pytest.raises(SignatureError):
        await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=b"\x00"*64)


async def test_blessing_dedup(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    sig = sign(ag_sk, art.content_id.encode())
    await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                       signer_pubkey=ag_pk, sig=sig)
    with pytest.raises(ConflictError):
        await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                           signer_pubkey=ag_pk, sig=sig)


async def test_tier_peer_vs_blessed(db_session, artifact_and_agent):
    art, ag_sk, ag_pk, agent_id = artifact_and_agent
    tier = await compute_tier(db_session, artifact=art, threshold=2)
    assert tier == "peer-shared"
    sig = sign(ag_sk, art.content_id.encode())
    await add_blessing(db_session, artifact=art, signer_agent_id=agent_id,
                       signer_pubkey=ag_pk, sig=sig)
    db_session.add(Blessing(
        artifact_id=art.id, signer_pubkey=b"\x09"*32, signer_agent_id=agent_id, sig=b"\x08"*64,
    ))
    await db_session.flush()
    tier = await compute_tier(db_session, artifact=art, threshold=2)
    assert tier == "class-blessed"
