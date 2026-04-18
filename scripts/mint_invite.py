"""Mint an invite token against a running backend using the founder seed
persisted by scripts/seed_grimoires.py.

Prints the invite URL on stdout so shell callers can capture it directly.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "cli" / "src"))

from kindred_client import crypto  # noqa: E402
from kindred_client.api_client import KindredAPI  # noqa: E402

DEFAULT_KEYFILE = Path(
    os.environ.get("KINDRED_SEED_KEYFILE", str(Path.home() / ".kin" / "seed.key"))
)


def load_seed() -> tuple[bytes, bytes]:
    if not DEFAULT_KEYFILE.exists():
        raise SystemExit(
            f"seed keyfile not found at {DEFAULT_KEYFILE}; "
            "run scripts/seed_grimoires.py first"
        )
    sk_hex = DEFAULT_KEYFILE.read_text().strip()
    sk_bytes = bytes.fromhex(sk_hex)
    from nacl import signing

    skey = signing.SigningKey(sk_bytes)
    return bytes(skey), bytes(skey.verify_key)


async def main(slug: str, backend_url: str) -> None:
    sk, pk = load_seed()
    api = KindredAPI(backend_url)
    kindred = await api.get_kindred_by_slug(slug)
    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    invite = await api.issue_invite(
        slug=slug,
        owner_pubkey=pk,
        owner_sk=sk,
        kindred_id=kindred["id"],
        token=token,
        expires_at_iso=expires_at,
        expires_in_days=1,
        max_uses=1,
    )
    url = invite.get("url") or f"{backend_url}/v1/invites/{invite.get('token', token)}"
    print(url)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument(
        "--backend-url",
        default=os.environ.get("KINDRED_BACKEND_URL", "http://localhost:8000"),
    )
    args = p.parse_args()
    asyncio.run(main(args.slug, args.backend_url))
