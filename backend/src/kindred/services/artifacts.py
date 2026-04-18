from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.artifact import Artifact
from kindred.storage.object_store import ObjectStore
from kindred.crypto.keys import verify
from kindred.crypto.content_id import compute_content_id
from kindred.errors import SignatureError, ValidationError, NotFoundError
from kindred.services.audit import append_event

ALLOWED_TYPES = {"claude_md", "routine", "skill_ref"}


async def upload_artifact(
    session: AsyncSession, *, store: ObjectStore, kindred_id: UUID,
    metadata: dict, body: bytes, author_pubkey: bytes, author_sig: bytes,
) -> Artifact:
    if metadata.get("type") not in ALLOWED_TYPES:
        raise ValidationError(f"unsupported type: {metadata.get('type')}")
    actual_body_cid = compute_content_id(body)
    if metadata.get("body_sha256") != actual_body_cid:
        raise ValidationError("body_sha256 mismatch")
    cid = compute_content_id(metadata)
    if not verify(author_pubkey, cid.encode(), author_sig):
        raise SignatureError("invalid author signature on content_id")
    exists = (await session.execute(select(Artifact).where(Artifact.content_id == cid))).scalar_one_or_none()
    if exists:
        return exists
    await store.put(actual_body_cid, body)
    art = Artifact(
        content_id=cid, kindred_id=kindred_id, type=metadata["type"],
        logical_name=metadata["logical_name"], author_pubkey=author_pubkey,
        author_sig=author_sig,
        valid_from=datetime.fromisoformat(metadata["valid_from"]),
        valid_until=datetime.fromisoformat(metadata["valid_until"]),
        tags=metadata.get("tags", []),
    )
    session.add(art)
    await session.flush()
    await append_event(session, kindred_id=kindred_id, event_type="artifact_uploaded",
                       payload={"content_id": cid, "logical_name": metadata["logical_name"]})
    return art


async def get_artifact(session: AsyncSession, content_id: str) -> Artifact:
    a = (await session.execute(select(Artifact).where(Artifact.content_id == content_id))).scalar_one_or_none()
    if not a:
        raise NotFoundError(f"artifact {content_id}")
    return a


async def list_artifacts(session: AsyncSession, kindred_id: UUID) -> list[Artifact]:
    q = select(Artifact).where(Artifact.kindred_id == kindred_id)
    return list((await session.execute(q)).scalars())
