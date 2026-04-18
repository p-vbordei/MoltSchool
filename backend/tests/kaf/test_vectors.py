# tests/kaf/test_vectors.py
"""Byte-exact KAF test vectors.

`vectors.json` is the contract between KAF implementations (Python, JS, Rust,
...). Any change to canonical_json, compute_content_id, or ed25519 signing
MUST either preserve these outputs or bump the KAF version + regenerate
vectors in lockstep across every implementer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nacl import signing

from kindred.crypto.canonical import canonical_json
from kindred.crypto.content_id import compute_content_id
from kindred.crypto.keys import sign, verify

VECTORS_PATH = Path(__file__).parent / "vectors.json"


def _load_vectors() -> list[dict]:
    with VECTORS_PATH.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["version"] == "0.1"
    return doc["vectors"]


def _decode_input(vec: dict):
    if vec["input_type"] == "bytes":
        raw = vec["input"]
        assert raw.startswith("hex:")
        return bytes.fromhex(raw[len("hex:") :])
    if vec["input_type"] == "dict":
        return vec["input"]
    raise AssertionError(f"unknown input_type: {vec['input_type']}")


VECTORS = _load_vectors()
DICT_VECTORS = [v for v in VECTORS if v.get("input_type") == "dict"]
BYTES_VECTORS = [v for v in VECTORS if v.get("input_type") == "bytes"]
SIG_VECTORS = [v for v in VECTORS if v["id"].startswith("sig_")]


def test_vectors_file_loads():
    assert len(VECTORS) >= 6, "expected at least 6 vectors (5 data + 1 sig)"


@pytest.mark.parametrize("vec", DICT_VECTORS, ids=lambda v: v["id"])
def test_canonical_json_is_byte_exact(vec):
    payload = _decode_input(vec)
    got = canonical_json(payload)
    assert got.hex() == vec["expected_canonical_json_hex"], (
        f"canonical_json drift for {vec['id']}: "
        f"got {got.hex()!r}, expected {vec['expected_canonical_json_hex']!r}"
    )
    assert got.decode("utf-8") == vec["expected_canonical_json_utf8"]


@pytest.mark.parametrize("vec", DICT_VECTORS + BYTES_VECTORS, ids=lambda v: v["id"])
def test_content_id_is_byte_exact(vec):
    payload = _decode_input(vec)
    got = compute_content_id(payload)
    assert got == vec["expected_content_id"], (
        f"content_id drift for {vec['id']}: got {got}, "
        f"expected {vec['expected_content_id']}"
    )


def test_v3_equals_v2_despite_key_order():
    """Sanity: unsorted input must produce same bytes as sorted input."""
    v2 = next(v for v in VECTORS if v["id"] == "v2")
    v3 = next(v for v in VECTORS if v["id"] == "v3")
    assert v2["expected_canonical_json_hex"] == v3["expected_canonical_json_hex"]
    assert v2["expected_content_id"] == v3["expected_content_id"]


@pytest.mark.parametrize("vec", SIG_VECTORS, ids=lambda v: v["id"])
def test_ed25519_signature_is_byte_exact(vec):
    sk_bytes = bytes.fromhex(vec["secret_key_hex"])
    expected_pk = bytes.fromhex(vec["public_key_hex"])
    expected_sig = bytes.fromhex(vec["expected_signature_hex"])
    msg = vec["content_id"].encode("utf-8")

    # Derived public key matches the recorded one.
    derived_pk = bytes(signing.SigningKey(sk_bytes).verify_key)
    assert derived_pk == expected_pk

    # Signing is deterministic (Ed25519) -> exact byte match.
    got_sig = sign(sk_bytes, msg)
    assert got_sig == expected_sig, (
        f"signature drift for {vec['id']}: got {got_sig.hex()}, "
        f"expected {expected_sig.hex()}"
    )

    # And verify() accepts it.
    assert verify(expected_pk, msg, expected_sig)
