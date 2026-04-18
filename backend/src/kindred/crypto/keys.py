from nacl import exceptions, signing


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
