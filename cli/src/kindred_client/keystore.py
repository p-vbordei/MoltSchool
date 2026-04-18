"""Local keypair storage under `~/.kin/keys/` with 0600 permissions."""
from __future__ import annotations

import os
from pathlib import Path


def get_kin_dir() -> Path:
    """Return `~/.kin/`, creating it with mode 0700 if missing."""
    d = Path.home() / ".kin"
    d.mkdir(mode=0o700, exist_ok=True)
    # Re-apply mode in case it existed with looser perms (best effort — skip on Windows).
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    keys = d / "keys"
    keys.mkdir(mode=0o700, exist_ok=True)
    try:
        os.chmod(keys, 0o700)
    except OSError:
        pass
    return d


def config_path() -> Path:
    return get_kin_dir() / "config.toml"


def _keys_dir() -> Path:
    return get_kin_dir() / "keys"


def store_keypair(agent_id: str, sk: bytes, pk: bytes) -> Path:
    """Write `<sk_hex>\\n<pk_hex>` to `~/.kin/keys/<agent_id>.key` at mode 0600."""
    path = _keys_dir() / f"{agent_id}.key"
    content = f"{sk.hex()}\n{pk.hex()}\n"
    # Write atomically with 0600 from creation — no window at looser perms.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
    except Exception:
        os.close(fd)
        raise
    # Enforce 0600 even if file pre-existed with different perms.
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_keypair(agent_id: str) -> tuple[bytes, bytes]:
    path = _keys_dir() / f"{agent_id}.key"
    if not path.exists():
        raise FileNotFoundError(f"no keypair for agent_id={agent_id!r}")
    lines = path.read_text().strip().splitlines()
    if len(lines) != 2:
        raise ValueError(f"malformed keypair file: {path}")
    return bytes.fromhex(lines[0]), bytes.fromhex(lines[1])


def list_agents() -> list[str]:
    keys = _keys_dir()
    if not keys.exists():
        return []
    return sorted(p.stem for p in keys.glob("*.key"))
