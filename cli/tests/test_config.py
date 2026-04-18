"""Tests for config.toml load/save."""
from __future__ import annotations

from kindred_client.config import Config, KindredEntry, load_config, save_config


def test_load_empty_returns_defaults(fake_home):
    c = load_config()
    assert c.backend_url == "https://kindred.sh"
    assert c.active_agent_id is None
    assert c.kindreds == []


def test_save_and_load_roundtrip(fake_home):
    c = Config(
        backend_url="http://localhost:8000",
        active_owner_id="owner",
        active_agent_id="agent-abc",
        kindreds=[
            KindredEntry(
                slug="heist-crew", backend_url="http://localhost:8000", user_id="u-1"
            ),
            KindredEntry(slug="other", backend_url="https://other.sh", user_id="u-2"),
        ],
    )
    save_config(c)
    loaded = load_config()
    assert loaded.backend_url == "http://localhost:8000"
    assert loaded.active_owner_id == "owner"
    assert loaded.active_agent_id == "agent-abc"
    assert len(loaded.kindreds) == 2
    assert loaded.kindreds[0].slug == "heist-crew"
    assert loaded.kindreds[0].user_id == "u-1"


def test_upsert_kindred_replaces(fake_home):
    c = Config()
    c.upsert_kindred(KindredEntry(slug="k", backend_url="a", user_id="1"))
    c.upsert_kindred(KindredEntry(slug="k", backend_url="b", user_id="2"))
    assert len(c.kindreds) == 1
    assert c.kindreds[0].backend_url == "b"


def test_remove_kindred(fake_home):
    c = Config(
        kindreds=[
            KindredEntry(slug="keep", backend_url="x"),
            KindredEntry(slug="drop", backend_url="x"),
        ]
    )
    assert c.remove_kindred("drop") is True
    assert [k.slug for k in c.kindreds] == ["keep"]
    assert c.remove_kindred("not-there") is False
