"""Crypto primitives — canonical_json + Ed25519 + content_id.

Mirrors the backend's `kindred.crypto.*` API so the CLI and server agree
byte-for-byte on what gets signed. Reimplemented (not imported) to keep
`kindred_client` decoupled from the backend source tree.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from nacl import exceptions, signing


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8, no ascii escape."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_content_id(payload: Any) -> str:
    """Return `sha256:<hex>` for the payload (bytes hashed as-is, else canonical_json)."""
    if isinstance(payload, (bytes, bytearray)):
        digest = hashlib.sha256(bytes(payload)).hexdigest()
    else:
        digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    return f"sha256:{digest}"


def generate_keypair() -> tuple[bytes, bytes]:
    sk = signing.SigningKey.generate()
    return bytes(sk), bytes(sk.verify_key)


def sign(sk_bytes: bytes, message: bytes) -> bytes:
    sk = signing.SigningKey(sk_bytes)
    return sk.sign(message).signature


def verify(pk_bytes: bytes, message: bytes, signature: bytes) -> bool:
    try:
        vk = signing.VerifyKey(pk_bytes)
        vk.verify(message, signature)
        return True
    except (exceptions.BadSignatureError, ValueError):
        return False


def pubkey_to_str(pk: bytes) -> str:
    return "ed25519:" + pk.hex()


def str_to_pubkey(s: str) -> bytes:
    if not s.startswith("ed25519:"):
        raise ValueError(f"unsupported key format: {s[:10]}")
    return bytes.fromhex(s[len("ed25519:") :])
