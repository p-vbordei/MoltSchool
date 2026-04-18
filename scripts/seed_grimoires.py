"""Seed a running Kindred backend with the 5 flagship grimoires.

Reads artifact source files from `docs/seed-grimoires/<slug>/` and uploads
them via the `kindred_client` library.

Idempotent: if a kindred exists it is re-used; if an artifact with the
same content_id already exists the backend returns the existing row.

Usage
-----
    export KINDRED_BACKEND_URL=http://localhost:8000
    python scripts/seed_grimoires.py

Environment variables
---------------------
    KINDRED_BACKEND_URL   Backend base URL (default: http://localhost:8000)
    KINDRED_SEED_EMAIL    Founder email         (default: founder@kindred.local)
    KINDRED_SEED_NAME     Founder display name  (default: "Kindred Founder")
    KINDRED_SEED_KEYFILE  Path to a file storing the founder seed bytes hex.
                          Generated and written if missing; reused if present.
                          Default: ~/.kin/seed.key
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Make kindred_client importable without installing the cli package.
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "cli" / "src"))

from kindred_client import crypto  # noqa: E402
from kindred_client.api_client import APIError, KindredAPI  # noqa: E402

DEFAULT_BACKEND = os.environ.get("KINDRED_BACKEND_URL", "http://localhost:8000")
DEFAULT_EMAIL = os.environ.get("KINDRED_SEED_EMAIL", "founder@kindred.local")
DEFAULT_NAME = os.environ.get("KINDRED_SEED_NAME", "Kindred Founder")
DEFAULT_KEYFILE = Path(
    os.environ.get("KINDRED_SEED_KEYFILE", str(Path.home() / ".kin" / "seed.key"))
)

GRIMOIRES = [
    {
        "slug": "claude-code-patterns",
        "display_name": "Claude Code Patterns",
        "description": "Team-standard behavioural patterns for Claude Code.",
        "bless_threshold": 1,
        "artifacts": [
            ("claude_md.md", "claude_md", "claude-md-core", ["claude-md", "team-defaults"]),
            ("routine-tdd-per-task.md", "routine", "routine-tdd-per-task", ["tdd", "workflow"]),
            ("routine-git-commits-per-task.md", "routine", "routine-git-commits-per-task", ["git", "commits"]),
            ("skill-ref-superpowers.json", "skill_ref", "skill-ref-superpowers", ["skill", "superpowers"]),
        ],
    },
    {
        "slug": "postgres-ops",
        "display_name": "Postgres Operations",
        "description": "Production Postgres routines: bloat, migrations, backups.",
        "bless_threshold": 1,
        "artifacts": [
            ("routine-handle-bloat.md", "routine", "routine-handle-bloat", ["postgres", "bloat"]),
            ("routine-migration-structure.md", "routine", "routine-migration-structure", ["postgres", "migrations"]),
            ("routine-backup-restore.md", "routine", "routine-backup-restore", ["postgres", "backup"]),
        ],
    },
    {
        "slug": "llm-eval-playbook",
        "display_name": "LLM Eval Playbook",
        "description": "Benchmark harness + cost tracking for LLM agents.",
        "bless_threshold": 1,
        "artifacts": [
            ("routine-benchmark-harness.md", "routine", "routine-benchmark-harness", ["llm", "benchmark"]),
            ("routine-cost-tracking.md", "routine", "routine-cost-tracking", ["llm", "cost"]),
        ],
    },
    {
        "slug": "agent-security",
        "display_name": "Agent Security",
        "description": "Injection defence and sandboxing for agent-produced output.",
        "bless_threshold": 1,
        "artifacts": [
            ("routine-injection-defense.md", "routine", "routine-injection-defense", ["security", "injection"]),
            ("routine-sandboxing.md", "routine", "routine-sandboxing", ["security", "sandbox"]),
        ],
    },
    {
        "slug": "kindred-patterns",
        "display_name": "Kindred Patterns",
        "description": "Meta-grimoire — patterns used to build Kindred itself.",
        "bless_threshold": 1,
        "artifacts": [
            ("claude_md.md", "claude_md", "kindred-claude-md", ["claude-md", "meta"]),
            ("routine-backend-tdd-style.md", "routine", "routine-backend-tdd-style", ["tdd", "backend"]),
        ],
    },
]


def load_or_create_seed() -> tuple[bytes, bytes]:
    """Return (secret_key_bytes, public_key_bytes). Persist seed so reruns
    re-use the same founder identity."""
    DEFAULT_KEYFILE.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_KEYFILE.exists():
        sk = bytes.fromhex(DEFAULT_KEYFILE.read_text().strip())
        # Derive pk from sk seed
        from nacl import signing

        skey = signing.SigningKey(sk)
        return bytes(skey), bytes(skey.verify_key)
    sk, pk = crypto.generate_keypair()
    DEFAULT_KEYFILE.write_text(sk.hex())
    DEFAULT_KEYFILE.chmod(0o600)
    return sk, pk


def build_metadata(
    *, type_: str, logical_name: str, kindred_id: str, body: bytes, tags: list[str]
) -> dict:
    now = datetime.now(UTC)
    return {
        "kaf_version": "0.1",
        "type": type_,
        "logical_name": logical_name,
        "kindred_id": kindred_id,
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=180)).isoformat(),
        "tags": tags,
        "body_sha256": crypto.compute_content_id(body),
    }


async def ensure_user(api: KindredAPI, pubkey: bytes, email: str, name: str) -> dict:
    try:
        return await api.get_user_by_pubkey(pubkey)
    except APIError as e:
        if e.status_code != 404:
            raise
    return await api.create_user(email=email, display_name=name, pubkey=pubkey)


async def ensure_kindred(
    api: KindredAPI,
    *,
    owner_pubkey: bytes,
    slug: str,
    display_name: str,
    description: str,
    bless_threshold: int,
) -> dict:
    try:
        return await api.get_kindred_by_slug(slug)
    except APIError as e:
        if e.status_code != 404:
            raise
    return await api.create_kindred(
        owner_pubkey=owner_pubkey,
        slug=slug,
        display_name=display_name,
        description=description,
        bless_threshold=bless_threshold,
    )


async def upload_one(
    api: KindredAPI,
    *,
    slug: str,
    kindred_id: str,
    body: bytes,
    type_: str,
    logical_name: str,
    tags: list[str],
    author_pubkey: bytes,
    author_sk: bytes,
) -> dict:
    metadata = build_metadata(
        type_=type_,
        logical_name=logical_name,
        kindred_id=kindred_id,
        body=body,
        tags=tags,
    )
    cid = crypto.compute_content_id(metadata)
    author_sig = crypto.sign(author_sk, cid.encode())
    return await api.upload_artifact(
        slug=slug,
        metadata=metadata,
        body=body,
        author_pubkey=author_pubkey,
        author_sig=author_sig,
    )


async def main() -> None:
    print(f"Kindred backend:  {DEFAULT_BACKEND}")
    print(f"Founder keyfile:  {DEFAULT_KEYFILE}")

    sk, pk = load_or_create_seed()
    print(f"Founder pubkey:   {crypto.pubkey_to_str(pk)}")

    api = KindredAPI(DEFAULT_BACKEND)
    await ensure_user(api, pk, DEFAULT_EMAIL, DEFAULT_NAME)

    source_root = _REPO / "docs" / "seed-grimoires"

    for g in GRIMOIRES:
        slug = g["slug"]
        print(f"\n=== grimoire: {slug} ===")
        kindred = await ensure_kindred(
            api,
            owner_pubkey=pk,
            slug=slug,
            display_name=g["display_name"],
            description=g["description"],
            bless_threshold=g["bless_threshold"],
        )
        kid = kindred["id"]
        print(f"  kindred id: {kid}")

        for filename, type_, logical_name, tags in g["artifacts"]:
            path = source_root / slug / filename
            if not path.exists():
                print(f"  [skip] {filename}: not found at {path}")
                continue
            body = path.read_bytes()
            try:
                art = await upload_one(
                    api,
                    slug=slug,
                    kindred_id=kid,
                    body=body,
                    type_=type_,
                    logical_name=logical_name,
                    tags=tags,
                    author_pubkey=pk,
                    author_sk=sk,
                )
                cid = art.get("content_id", "?")
                tier = art.get("tier", "?")
                print(f"  [ok]   {filename:<42} -> {cid[:20]}... tier={tier}")
            except APIError as e:
                print(f"  [fail] {filename}: HTTP {e.status_code} {e.message}")

    print("\nDone.")
    print(f"Save this pubkey in your records:  {crypto.pubkey_to_str(pk)}")


if __name__ == "__main__":
    asyncio.run(main())
