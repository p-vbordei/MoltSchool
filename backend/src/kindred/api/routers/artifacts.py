import base64

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session, get_object_store
from kindred.api.schemas.artifacts import ArtifactOut, UploadArtifactReq
from kindred.crypto.keys import str_to_pubkey
from kindred.services.artifacts import list_artifacts, upload_artifact
from kindred.services.blessings import compute_tier
from kindred.services.kindreds import get_kindred_by_slug
from kindred.storage.object_store import ObjectStore

router = APIRouter()


@router.post("/{slug}/artifacts", response_model=ArtifactOut, status_code=201)
async def upload(
    slug: str,
    req: UploadArtifactReq,
    session: AsyncSession = Depends(db_session),
    store: ObjectStore = Depends(get_object_store),
):
    k = await get_kindred_by_slug(session, slug)
    body = base64.b64decode(req.body_b64)
    art = await upload_artifact(
        session,
        store=store,
        kindred_id=k.id,
        metadata=req.metadata,
        body=body,
        author_pubkey=str_to_pubkey(req.author_pubkey),
        author_sig=bytes.fromhex(req.author_sig),
    )
    tier = await compute_tier(session, artifact=art, threshold=k.bless_threshold)
    return ArtifactOut(
        content_id=art.content_id,
        type=art.type,
        logical_name=art.logical_name,
        tier=tier,
        valid_from=art.valid_from.isoformat(),
        valid_until=art.valid_until.isoformat(),
        outcome_uses=art.outcome_uses,
        outcome_successes=art.outcome_successes,
    )


@router.get("/{slug}/artifacts", response_model=list[ArtifactOut])
async def list_(slug: str, session: AsyncSession = Depends(db_session)):
    k = await get_kindred_by_slug(session, slug)
    arts = await list_artifacts(session, kindred_id=k.id)
    out = []
    for a in arts:
        tier = await compute_tier(session, artifact=a, threshold=k.bless_threshold)
        out.append(
            ArtifactOut(
                content_id=a.content_id,
                type=a.type,
                logical_name=a.logical_name,
                tier=tier,
                valid_from=a.valid_from.isoformat(),
                valid_until=a.valid_until.isoformat(),
                outcome_uses=a.outcome_uses,
                outcome_successes=a.outcome_successes,
            )
        )
    return out
