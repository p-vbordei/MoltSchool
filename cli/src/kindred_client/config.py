"""Local CLI config stored in `~/.kin/config.toml`."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field

import tomli_w

from kindred_client.keystore import config_path

DEFAULT_BACKEND = "https://kindred.sh"


@dataclass
class KindredEntry:
    slug: str
    backend_url: str
    user_id: str = ""


@dataclass
class Config:
    backend_url: str = DEFAULT_BACKEND
    active_owner_id: str | None = None
    active_agent_id: str | None = None
    kindreds: list[KindredEntry] = field(default_factory=list)

    def find_kindred(self, slug: str) -> KindredEntry | None:
        for k in self.kindreds:
            if k.slug == slug:
                return k
        return None

    def upsert_kindred(self, entry: KindredEntry) -> None:
        for i, k in enumerate(self.kindreds):
            if k.slug == entry.slug:
                self.kindreds[i] = entry
                return
        self.kindreds.append(entry)

    def remove_kindred(self, slug: str) -> bool:
        before = len(self.kindreds)
        self.kindreds = [k for k in self.kindreds if k.slug != slug]
        return len(self.kindreds) < before


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        data = tomllib.load(f)
    kindreds = [
        KindredEntry(
            slug=k["slug"],
            backend_url=k.get("backend_url", data.get("backend_url", DEFAULT_BACKEND)),
            user_id=k.get("user_id", ""),
        )
        for k in data.get("kindreds", [])
    ]
    return Config(
        backend_url=data.get("backend_url", DEFAULT_BACKEND),
        active_owner_id=data.get("active_owner_id"),
        active_agent_id=data.get("active_agent_id"),
        kindreds=kindreds,
    )


def save_config(c: Config) -> None:
    data: dict = {"backend_url": c.backend_url}
    if c.active_owner_id:
        data["active_owner_id"] = c.active_owner_id
    if c.active_agent_id:
        data["active_agent_id"] = c.active_agent_id
    data["kindreds"] = [
        {"slug": k.slug, "backend_url": k.backend_url, "user_id": k.user_id}
        for k in c.kindreds
    ]
    path = config_path()
    with path.open("wb") as f:
        tomli_w.dump(data, f)
