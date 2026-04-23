"""Unit tests for MCP tool definitions + call routing.

Strategy: we don't spin up a real backend. We mock KindredAPI at the seam, and
verify (a) tool JSON schemas are well-formed and (b) arguments are forwarded.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from kindred_mcp import tools


def test_kin_ask_tool_schema():
    t = tools.kin_ask_tool()
    assert t.name == "kin_ask"
    assert t.description
    schema = t.inputSchema
    assert schema["type"] == "object"
    props = schema["properties"]
    assert "kindred" in props
    assert "query" in props
    assert "k" in props
    assert set(schema["required"]) == {"kindred", "query"}


def test_kin_contribute_tool_schema():
    t = tools.kin_contribute_tool()
    assert t.name == "kin_contribute"
    schema = t.inputSchema
    assert schema["type"] == "object"
    props = schema["properties"]
    for key in ("kindred", "type", "content", "logical_name"):
        assert key in props, f"missing {key}"
    assert "tags" in props
    assert set(schema["required"]) >= {"kindred", "type", "content", "logical_name"}


def test_tool_schemas_serialize_to_json():
    # MCP clients receive these as JSON — must be serializable.
    import json

    for t in (tools.kin_ask_tool(), tools.kin_contribute_tool()):
        json.dumps(t.inputSchema)


async def test_kin_ask_forwards_args(tmp_path: Path, monkeypatch):
    """kin_ask loads config + keystore, then calls KindredAPI.ask with the
    active agent pubkey and returns a formatted string."""
    # Fake config: active agent, one kindred entry.
    from kindred_client import config as kcfg
    from kindred_client import keystore

    monkeypatch.setenv("HOME", str(tmp_path))
    # Create a fake keypair file.
    keystore.get_kin_dir()
    agent_id = "agent-xyz"
    keystore.store_keypair(agent_id, b"\x01" * 32, b"\x02" * 32)
    cfg = kcfg.Config(
        backend_url="http://localhost:8000",
        active_agent_id=agent_id,
        kindreds=[kcfg.KindredEntry(slug="my-team", backend_url="http://localhost:8000")],
    )
    kcfg.save_config(cfg)

    fake_resp = {
        "artifacts": [
            {
                "content_id": "cid-1",
                "framed": "== BEGIN ARTIFACT ==\nuse X\n== END ARTIFACT ==",
                "tier": "blessed",
            }
        ],
        "provenance": [
            {
                "logical_name": "pattern-a",
                "author_pubkey": "aa" * 32,
                "outcome_success_rate": 0.8,
            }
        ],
        "audit_id": "audit-1",
    }

    with patch.object(tools, "KindredAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.ask = AsyncMock(return_value=fake_resp)
        out = await tools.kin_ask(kindred="my-team", query="how do we X?", k=3)

    MockAPI.assert_called_once_with("http://localhost:8000")
    instance.ask.assert_awaited_once()
    call_kwargs = instance.ask.await_args.kwargs
    assert call_kwargs["slug"] == "my-team"
    assert call_kwargs["query"] == "how do we X?"
    assert call_kwargs["k"] == 3
    assert call_kwargs["agent_pubkey"] == b"\x02" * 32
    # Output string includes framed content + provenance chip.
    assert "pattern-a" in out
    assert "BEGIN ARTIFACT" in out
    assert "audit-1" in out
    # The audit_id is persisted for the PostToolUse hook to consume.
    assert (tmp_path / ".kin" / "last_audit_id").read_text() == "audit-1"


async def test_kin_ask_no_active_agent(tmp_path: Path, monkeypatch):
    from kindred_client import config as kcfg

    monkeypatch.setenv("HOME", str(tmp_path))
    kcfg.save_config(kcfg.Config(backend_url="http://x"))

    with pytest.raises(RuntimeError, match="no active agent"):
        await tools.kin_ask(kindred="team", query="q")


async def test_kin_contribute_forwards_args(tmp_path: Path, monkeypatch):
    from kindred_client import config as kcfg
    from kindred_client import keystore

    monkeypatch.setenv("HOME", str(tmp_path))
    keystore.get_kin_dir()
    agent_id = "agent-xyz"
    keystore.store_keypair(agent_id, b"\x01" * 32, b"\x02" * 32)
    cfg = kcfg.Config(
        backend_url="http://localhost:8000",
        active_agent_id=agent_id,
        kindreds=[kcfg.KindredEntry(slug="my-team", backend_url="http://localhost:8000")],
    )
    kcfg.save_config(cfg)

    with patch.object(tools, "KindredAPI") as MockAPI, patch.object(
        tools, "crypto"
    ) as mock_crypto:
        instance = MockAPI.return_value
        instance.get_kindred_by_slug = AsyncMock(return_value={"id": "kid-1"})
        instance.upload_artifact = AsyncMock(
            return_value={"content_id": "cid-1", "tier": "peer-shared"}
        )
        mock_crypto.compute_content_id.return_value = "cid-hash"
        mock_crypto.sign.return_value = b"\x09" * 64

        out = await tools.kin_contribute(
            kindred="my-team",
            type="claude_md",
            content="hello world",
            logical_name="greeting",
            tags=["demo"],
        )

    instance.upload_artifact.assert_awaited_once()
    kwargs = instance.upload_artifact.await_args.kwargs
    assert kwargs["slug"] == "my-team"
    assert kwargs["body"] == b"hello world"
    assert kwargs["metadata"]["logical_name"] == "greeting"
    assert kwargs["metadata"]["type"] == "claude_md"
    assert kwargs["metadata"]["tags"] == ["demo"]
    assert "cid-1" in out
    assert "peer-shared" in out


async def test_kin_contribute_invalid_type(tmp_path: Path, monkeypatch):
    from kindred_client import config as kcfg
    from kindred_client import keystore

    monkeypatch.setenv("HOME", str(tmp_path))
    keystore.get_kin_dir()
    keystore.store_keypair("a", b"\x01" * 32, b"\x02" * 32)
    kcfg.save_config(
        kcfg.Config(
            backend_url="http://x",
            active_agent_id="a",
            kindreds=[kcfg.KindredEntry(slug="t", backend_url="http://x")],
        )
    )
    with pytest.raises(ValueError, match="invalid type"):
        await tools.kin_contribute(
            kindred="t", type="malformed", content="x", logical_name="y"
        )
