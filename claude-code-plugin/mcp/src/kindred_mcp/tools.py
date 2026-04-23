"""Tool implementations for the Kindred MCP server.

Thin wrappers over kindred_client.api_client.KindredAPI + local config/keystore.
Schemas are returned as MCP `Tool` objects for `list_tools`. Call sites hand
us `**arguments` from the MCP framework.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from mcp.types import Tool

from kindred_client import crypto
from kindred_client.api_client import KindredAPI
from kindred_client.config import load_config
from kindred_client.keystore import load_keypair

ALLOWED_TYPES = ("claude_md", "routine", "skill_ref")


# --- Tool definitions -----------------------------------------------------


def kin_ask_tool() -> Tool:
    return Tool(
        name="kin_ask",
        description=(
            "Query the team's Kindred grimoire for verified patterns. Returns "
            "framed artifacts and provenance chips. Use whenever the user asks "
            "a question that might have a team-specific answer."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "kindred": {
                    "type": "string",
                    "description": "Kindred slug (from ~/.kin/config.toml)",
                },
                "query": {
                    "type": "string",
                    "description": "Natural-language question",
                },
                "k": {
                    "type": "integer",
                    "description": "Max artifacts to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["kindred", "query"],
        },
    )


def kin_contribute_tool() -> Tool:
    return Tool(
        name="kin_contribute",
        description=(
            "Upload a new artifact (pattern, CLAUDE.md snippet, routine) to the "
            "user's kindred. Ask first before calling. Starts as peer-shared "
            "until enough members bless it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "kindred": {"type": "string", "description": "Kindred slug"},
                "type": {
                    "type": "string",
                    "enum": list(ALLOWED_TYPES),
                    "description": "Artifact kind",
                },
                "content": {
                    "type": "string",
                    "description": "Artifact body (markdown / text)",
                },
                "logical_name": {
                    "type": "string",
                    "description": "Short identifier for this artifact",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags",
                    "default": [],
                },
            },
            "required": ["kindred", "type", "content", "logical_name"],
        },
    )


# --- Tool implementations -------------------------------------------------


def _write_last_audit_id(audit_id: str) -> None:
    """Write the latest /ask audit_id to ~/.kin/last_audit_id for the
    PostToolUse hook to consume."""
    p = Path.home() / ".kin" / "last_audit_id"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(audit_id)


async def kin_ask(kindred: str, query: str, k: int = 5) -> str:
    cfg = load_config()
    if not cfg.active_agent_id:
        raise RuntimeError("no active agent — run `kin join <invite_url>` first")
    entry = cfg.find_kindred(kindred)
    backend = entry.backend_url if entry else cfg.backend_url
    _, agent_pk = load_keypair(cfg.active_agent_id)

    api = KindredAPI(backend)
    resp = await api.ask(slug=kindred, agent_pubkey=agent_pk, query=query, k=k)
    audit_id = resp.get("audit_id")
    if audit_id:
        _write_last_audit_id(audit_id)
    return _format_ask_response(resp)


def _format_ask_response(resp: dict) -> str:
    artifacts = resp.get("artifacts") or []
    provenance = resp.get("provenance") or []
    if not artifacts:
        return f"No artifacts matched. audit_id={resp.get('audit_id', '?')}"

    blocks: list[str] = []
    for art, chip in zip(artifacts, provenance, strict=False):
        tier = art.get("tier") or "unproven"
        name = chip.get("logical_name", art.get("content_id", "?"))
        rate = chip.get("outcome_success_rate", 0.0)
        author = chip.get("author_pubkey", "?")
        blocks.append(
            f"--- {name} (tier={tier}, author={author[:20]}…, "
            f"success_rate={rate:.0%}) ---\n{art.get('framed', '')}"
        )
    blocks.append(f"audit_id: {resp.get('audit_id', '?')}")
    return "\n\n".join(blocks)


async def kin_contribute(
    kindred: str,
    type: str,  # noqa: A002 (matches MCP tool schema)
    content: str,
    logical_name: str,
    tags: list[str] | None = None,
) -> str:
    if type not in ALLOWED_TYPES:
        raise ValueError(
            f"invalid type {type!r}; must be one of {', '.join(ALLOWED_TYPES)}"
        )
    cfg = load_config()
    if not cfg.active_agent_id:
        raise RuntimeError("no active agent — run `kin join <invite_url>` first")
    entry = cfg.find_kindred(kindred)
    if not entry:
        raise RuntimeError(f"not joined to kindred {kindred!r}")
    agent_sk, agent_pk = load_keypair(cfg.active_agent_id)

    body = content.encode("utf-8")
    api = KindredAPI(entry.backend_url)
    kindred_info = await api.get_kindred_by_slug(kindred)

    now = datetime.now(UTC)
    metadata = {
        "kaf_version": "0.1",
        "type": type,
        "logical_name": logical_name,
        "kindred_id": kindred_info["id"],
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=180)).isoformat(),
        "tags": tags or [],
        "body_sha256": crypto.compute_content_id(body),
    }
    cid = crypto.compute_content_id(metadata)
    author_sig = crypto.sign(agent_sk, cid.encode())

    art = await api.upload_artifact(
        slug=kindred,
        metadata=metadata,
        body=body,
        author_pubkey=agent_pk,
        author_sig=author_sig,
    )
    return (
        f"Contributed {logical_name!r} to {kindred!r}. "
        f"tier={art.get('tier', '?')}, content_id={art.get('content_id', '?')}"
    )
