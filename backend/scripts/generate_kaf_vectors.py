#!/usr/bin/env python3
"""Generate byte-exact KAF test vectors.

Produces `backend/tests/kaf/vectors.json`, a fixed set of inputs and their
expected canonical-JSON / content_id / ed25519-signature outputs. The JSON
is the contract: the corresponding reader test asserts the current
implementation still produces identical bytes.

Run once; commit the output. Re-run only when the spec intentionally changes,
in which case every KAF implementer (Python, JS, Rust, ...) must be updated
in lockstep.
"""

from __future__ import annotations

import json
from pathlib import Path

from nacl import signing

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id

# Fixed Ed25519 keypair: sk = 32 zero bytes → deterministic pk.
FIXED_SK_HEX = "00" * 32


def _enc_input(obj) -> tuple[str, object]:
    """Return (input_type, input_value) for the vector file."""
    if isinstance(obj, (bytes, bytearray)):
        return "bytes", "hex:" + bytes(obj).hex()
    return "dict", obj


def _dict_vector(vid: str, description: str, payload: dict) -> dict:
    cj = canonical_json(payload)
    return {
        "id": vid,
        "description": description,
        "input_type": "dict",
        "input": payload,
        "expected_canonical_json_hex": cj.hex(),
        "expected_canonical_json_utf8": cj.decode("utf-8"),
        "expected_content_id": compute_content_id(payload),
    }


def _bytes_vector(vid: str, description: str, payload: bytes) -> dict:
    return {
        "id": vid,
        "description": description,
        "input_type": "bytes",
        "input": "hex:" + payload.hex(),
        "expected_content_id": compute_content_id(payload),
    }


def build_vectors() -> list[dict]:
    vectors: list[dict] = []

    # v1: empty dict
    vectors.append(_dict_vector("v1", "empty dict -> canonical {}", {}))

    # v2: two keys already sorted
    vectors.append(
        _dict_vector("v2", "two keys, already sorted", {"a": 1, "b": 2})
    )

    # v3: same keys, unsorted input -> must equal v2 output
    vectors.append(
        _dict_vector("v3", "same keys, unsorted input", {"b": 2, "a": 1})
    )

    # v4: nested structure (arrays preserve order; nested dicts sort)
    vectors.append(
        _dict_vector(
            "v4",
            "nested dict with array and sub-dict",
            {"x": [3, 1, 2], "y": {"b": 1, "a": 2}},
        )
    )

    # v5: content_id over raw bytes
    vectors.append(_bytes_vector("v5", "content_id over b'hello world'", b"hello world"))

    # sig_v1: ed25519 signature over v5's content_id, using sk=00*32.
    sk_bytes = bytes.fromhex(FIXED_SK_HEX)
    sk = signing.SigningKey(sk_bytes)
    pk_bytes = bytes(sk.verify_key)
    msg = vectors[-1]["expected_content_id"].encode("utf-8")
    sig = sk.sign(msg).signature
    vectors.append(
        {
            "id": "sig_v1",
            "description": "ed25519 sign of v5 content_id with sk=00*32",
            "secret_key_hex": FIXED_SK_HEX,
            "public_key_hex": pk_bytes.hex(),
            "content_id": vectors[-1]["expected_content_id"],
            "expected_signature_hex": sig.hex(),
        }
    )

    return vectors


def main() -> None:
    vectors = build_vectors()
    out_path = (
        Path(__file__).resolve().parent.parent / "tests" / "kaf" / "vectors.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"version": "0.1", "vectors": vectors}, f, indent=2, sort_keys=False)
        f.write("\n")
    print(f"wrote {len(vectors)} vectors to {out_path}")


if __name__ == "__main__":
    main()
