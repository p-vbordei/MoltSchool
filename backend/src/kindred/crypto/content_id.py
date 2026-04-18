import hashlib
from typing import Any

from kindred.crypto.canonical import canonical_json


def compute_content_id(payload: Any) -> str:
    """Return sha256:<hex> for the given payload.

    Bytes are hashed directly; all other payloads are canonicalized to JSON first.
    """
    if isinstance(payload, (bytes, bytearray)):
        digest = hashlib.sha256(bytes(payload)).hexdigest()
    else:
        digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    return f"sha256:{digest}"
