"""Artifact upload/read service.

Validates KAF envelopes, enforces per-type body/metadata rules, and persists
artifacts content-addressed via the object store. See
`kindredformat/content/kaf-spec-0.1.md` for type definitions.
"""
import json
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import verify
from kindred.embeddings.provider import EmbeddingProvider
from kindred.errors import NotFoundError, SignatureError, ValidationError
from kindred.models.artifact import Artifact
from kindred.services.audit import append_event
from kindred.storage.object_store import ObjectStore

ALLOWED_TYPES = {
    "claude_md", "routine", "skill_ref",
    "repo_ref", "conversation_distilled", "benchmark_ref",
}

_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SCRIPT_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SUMMARY_MAX = 4096


def _parse_json_body(body: bytes, type_name: str) -> dict:
    try:
        obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValidationError(f"{type_name}: body must be valid UTF-8 JSON ({e})") from e
    if not isinstance(obj, dict):
        raise ValidationError(f"{type_name}: body must be a JSON object")
    return obj


def _require_keys(obj: dict, required: list[str], type_name: str) -> None:
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValidationError(
            f"{type_name}: missing required body keys: {', '.join(sorted(missing))}"
        )


def _validate_type_specific(metadata: dict, body: bytes) -> None:
    """Per-type validation of body shape + metadata pins.

    Runs after the envelope-level body_sha256 check. Raises ValidationError
    with a user-friendly message naming what's wrong.
    """
    t = metadata.get("type")
    if t == "repo_ref":
        obj = _parse_json_body(body, "repo_ref")
        _require_keys(obj, ["repo_url", "commit_sha", "summary"], "repo_ref")
        if not isinstance(obj["repo_url"], str) or not obj["repo_url"].startswith("https://"):
            raise ValidationError("repo_ref: repo_url must be an https:// URL")
        if not isinstance(obj["commit_sha"], str) or not _COMMIT_SHA_RE.match(obj["commit_sha"]):
            raise ValidationError(
                "repo_ref: commit_sha must be a 40-char lowercase hex string"
            )
        summary = obj["summary"]
        if not isinstance(summary, str) or not summary.strip():
            raise ValidationError("repo_ref: summary must be a non-empty string")
        if len(summary) > _SUMMARY_MAX:
            raise ValidationError(
                f"repo_ref: summary exceeds {_SUMMARY_MAX} chars (got {len(summary)})"
            )
    elif t == "conversation_distilled":
        src = metadata.get("source_audit_id")
        if not isinstance(src, str) or not _UUID_RE.match(src):
            raise ValidationError(
                "conversation_distilled: metadata.source_audit_id must be a UUID string"
            )
        if not body:
            raise ValidationError("conversation_distilled: body must not be empty")
    elif t == "benchmark_ref":
        obj = _parse_json_body(body, "benchmark_ref")
        _require_keys(
            obj,
            ["harness_url", "script_sha256", "last_pass_ts", "runtime_seconds"],
            "benchmark_ref",
        )
        if not isinstance(obj["harness_url"], str) or not obj["harness_url"].startswith("https://"):
            raise ValidationError("benchmark_ref: harness_url must be an https:// URL")
        if (
            not isinstance(obj["script_sha256"], str)
            or not _SCRIPT_SHA_RE.match(obj["script_sha256"])
        ):
            raise ValidationError(
                "benchmark_ref: script_sha256 must match 'sha256:<64-hex>'"
            )
        rt = obj["runtime_seconds"]
        if not isinstance(rt, int) or isinstance(rt, bool) or rt <= 0:
            raise ValidationError(
                "benchmark_ref: runtime_seconds must be a positive integer"
            )


async def upload_artifact(
    session: AsyncSession, *, store: ObjectStore, kindred_id: UUID,
    metadata: dict, body: bytes, author_pubkey: bytes, author_sig: bytes,
    embedding_provider: EmbeddingProvider | None = None,
) -> Artifact:
    if metadata.get("type") not in ALLOWED_TYPES:
        raise ValidationError(f"unsupported type: {metadata.get('type')}")
    actual_body_cid = compute_content_id(body)
    if metadata.get("body_sha256") != actual_body_cid:
        raise ValidationError("body_sha256 mismatch")
    _validate_type_specific(metadata, body)
    cid = compute_content_id(metadata)
    if not verify(author_pubkey, cid.encode(), author_sig):
        raise SignatureError("invalid author signature on content_id")
    exists = (
        await session.execute(select(Artifact).where(Artifact.content_id == cid))
    ).scalar_one_or_none()
    if exists:
        return exists
    await store.put(actual_body_cid, body)
    embedding: list[float] | None = None
    if embedding_provider is not None:
        # Truncate body to 1024 bytes for the embed text — keeps OpenAI input small
        # and stays well under 8k token context. Decoded leniently to avoid failing
        # on non-utf8 body bytes.
        tag_str = " ".join(metadata.get("tags", []))
        body_str = body[:1024].decode("utf-8", errors="replace")
        embed_text = f"{metadata['logical_name']}\n{tag_str}\n{body_str}"
        embedding = await embedding_provider.embed(embed_text)
    art = Artifact(
        content_id=cid, kindred_id=kindred_id, type=metadata["type"],
        logical_name=metadata["logical_name"], author_pubkey=author_pubkey,
        author_sig=author_sig,
        valid_from=datetime.fromisoformat(metadata["valid_from"]),
        valid_until=datetime.fromisoformat(metadata["valid_until"]),
        tags=metadata.get("tags", []),
        embedding=embedding,
    )
    session.add(art)
    await session.flush()
    await append_event(session, kindred_id=kindred_id, event_type="artifact_uploaded",
                       payload={"content_id": cid, "logical_name": metadata["logical_name"]})
    return art


async def get_artifact(session: AsyncSession, content_id: str) -> Artifact:
    a = (
        await session.execute(select(Artifact).where(Artifact.content_id == content_id))
    ).scalar_one_or_none()
    if not a:
        raise NotFoundError(f"artifact {content_id}")
    return a


async def list_artifacts(session: AsyncSession, kindred_id: UUID) -> list[Artifact]:
    q = select(Artifact).where(Artifact.kindred_id == kindred_id)
    return list((await session.execute(q)).scalars())
