from datetime import UTC, datetime, timedelta

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import generate_keypair, pubkey_to_str, sign
from kindred.services.agents import register_agent
from kindred.services.artifacts import upload_artifact
from kindred.services.kindreds import create_kindred
from kindred.services.users import register_user
from kindred.storage.object_store import InMemoryObjectStore


async def make_user_agent_kindred_artifact(db_session, email="a@x", slug="x"):
    sk, pk = generate_keypair()
    u = await register_user(db_session, email=email, display_name=email, pubkey=pk)
    ag_sk, ag_pk = generate_keypair()
    expires = datetime.now(UTC) + timedelta(days=30)
    scope = {"kindreds": ["*"], "actions": ["contribute"]}
    att = canonical_json(
        {"agent_pubkey": pubkey_to_str(ag_pk), "scope": scope, "expires_at": expires.isoformat()}
    )
    att_sig = sign(sk, att)
    a = await register_agent(db_session, owner_id=u.id, agent_pubkey=ag_pk,
                             display_name="x", scope=scope, expires_at=expires, sig=att_sig)
    k = await create_kindred(db_session, owner_id=u.id, slug=slug, display_name="X")
    store = InMemoryObjectStore()
    body = b"# R\n1. step"
    metadata = {
        "kaf_version": "0.1", "type": "routine", "logical_name": "r1",
        "kindred_id": str(k.id), "valid_from": "2026-04-18T00:00:00+00:00",
        "valid_until": "2026-10-18T00:00:00+00:00", "tags": [],
        "body_sha256": compute_content_id(body),
    }
    cid = compute_content_id(metadata)
    sig = sign(ag_sk, cid.encode())
    art = await upload_artifact(db_session, store=store, kindred_id=k.id,
                                metadata=metadata, body=body,
                                author_pubkey=ag_pk, author_sig=sig)
    return art, ag_sk, ag_pk, a.id
