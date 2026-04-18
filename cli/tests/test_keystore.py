"""Tests for keystore + crypto."""
from __future__ import annotations

import os
import stat

import pytest

from kindred_client import crypto
from kindred_client.keystore import (
    config_path,
    get_kin_dir,
    list_agents,
    load_keypair,
    store_keypair,
)


def test_get_kin_dir_creates_directory(fake_home):
    d = get_kin_dir()
    assert d.exists()
    assert d == fake_home / ".kin"
    # 0700 permissions (POSIX only)
    mode = stat.S_IMODE(os.stat(d).st_mode)
    assert mode == 0o700


def test_config_path(fake_home):
    p = config_path()
    assert p == fake_home / ".kin" / "config.toml"


def test_store_and_load_roundtrip(fake_home):
    sk, pk = crypto.generate_keypair()
    path = store_keypair("agent-abc", sk, pk)
    assert path.exists()
    loaded_sk, loaded_pk = load_keypair("agent-abc")
    assert loaded_sk == sk
    assert loaded_pk == pk


def test_store_keypair_has_0600_permissions(fake_home):
    sk, pk = crypto.generate_keypair()
    path = store_keypair("agent-perm", sk, pk)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


def test_store_keypair_overwrites_existing(fake_home):
    sk1, pk1 = crypto.generate_keypair()
    store_keypair("dup", sk1, pk1)
    sk2, pk2 = crypto.generate_keypair()
    store_keypair("dup", sk2, pk2)
    loaded_sk, loaded_pk = load_keypair("dup")
    assert loaded_sk == sk2
    assert loaded_pk == pk2


def test_load_missing_raises(fake_home):
    with pytest.raises(FileNotFoundError):
        load_keypair("nope")


def test_list_agents_empty(fake_home):
    assert list_agents() == []


def test_list_agents_sorted(fake_home):
    for name in ["zeta", "alpha", "mu"]:
        sk, pk = crypto.generate_keypair()
        store_keypair(name, sk, pk)
    assert list_agents() == ["alpha", "mu", "zeta"]


def test_crypto_sign_verify_roundtrip():
    sk, pk = crypto.generate_keypair()
    msg = b"hello kindred"
    sig = crypto.sign(sk, msg)
    assert crypto.verify(pk, msg, sig)
    # Tamper
    assert not crypto.verify(pk, msg + b"!", sig)


def test_crypto_pubkey_str_roundtrip():
    _, pk = crypto.generate_keypair()
    s = crypto.pubkey_to_str(pk)
    assert s.startswith("ed25519:")
    assert crypto.str_to_pubkey(s) == pk


def test_crypto_str_to_pubkey_rejects_unknown_prefix():
    with pytest.raises(ValueError):
        crypto.str_to_pubkey("rsa:deadbeef")


def test_canonical_json_stable_and_sorted():
    a = crypto.canonical_json({"b": 1, "a": 2})
    b = crypto.canonical_json({"a": 2, "b": 1})
    assert a == b
    assert a == b'{"a":2,"b":1}'


def test_compute_content_id_bytes_vs_dict():
    body = b"hello"
    cid = crypto.compute_content_id(body)
    assert cid.startswith("sha256:")
    # same key order → same cid
    cid_a = crypto.compute_content_id({"x": 1, "y": 2})
    cid_b = crypto.compute_content_id({"y": 2, "x": 1})
    assert cid_a == cid_b
