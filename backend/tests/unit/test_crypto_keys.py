import pytest

from kindred.crypto.keys import (
    generate_keypair,
    pubkey_to_str,
    sign,
    str_to_pubkey,
    verify,
)


def test_generate_keypair_returns_sk_and_pk():
    sk, pk = generate_keypair()
    assert len(sk) == 32
    assert len(pk) == 32


def test_sign_verify_roundtrip():
    sk, pk = generate_keypair()
    msg = b"hello kindred"
    sig = sign(sk, msg)
    assert verify(pk, msg, sig) is True


def test_verify_rejects_tampered_message():
    sk, pk = generate_keypair()
    sig = sign(sk, b"msg")
    assert verify(pk, b"tampered", sig) is False


def test_verify_rejects_bad_signature():
    _, pk = generate_keypair()
    assert verify(pk, b"msg", b"\x00" * 64) is False


def test_pubkey_string_roundtrip():
    _, pk = generate_keypair()
    s = pubkey_to_str(pk)
    assert s.startswith("ed25519:")
    assert str_to_pubkey(s) == pk


def test_str_to_pubkey_rejects_bad_prefix():
    with pytest.raises(ValueError):
        str_to_pubkey("rsa:abcd")
