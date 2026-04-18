"""Validate `.claude-plugin/plugin.json` shape.

We don't have an official JSON schema for Claude Code plugin manifests, so we
spot-check the fields the plugin system relies on: name, version, skills (paths
exist), mcp_servers (command+args), hooks (event+script path exists).
"""
from __future__ import annotations

import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"


def load_manifest() -> dict:
    with MANIFEST.open() as f:
        return json.load(f)


def test_manifest_is_valid_json():
    assert MANIFEST.exists(), f"missing {MANIFEST}"
    load_manifest()  # raises if invalid


def test_required_fields_present():
    m = load_manifest()
    for field in ("name", "version", "description", "license"):
        assert field in m and m[field], f"missing {field}"
    assert m["name"].startswith("@kindred/")
    # semver-ish
    parts = m["version"].split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_skills_paths_resolve():
    m = load_manifest()
    assert "skills" in m and m["skills"]
    for name, rel in m["skills"].items():
        # Strip leading ./ if present.
        path = PLUGIN_ROOT / rel.lstrip("./")
        assert path.exists(), f"skill {name}: {path} does not exist"
        assert path.suffix == ".md"


def test_mcp_servers_shape():
    m = load_manifest()
    servers = m.get("mcp_servers") or {}
    assert servers, "expected at least one MCP server"
    for name, spec in servers.items():
        assert "command" in spec, f"server {name} missing command"
        assert isinstance(spec.get("args", []), list)
        # Interpolated ${CLAUDE_PLUGIN_ROOT} should appear in args.
        joined = " ".join(spec.get("args", []))
        assert "${CLAUDE_PLUGIN_ROOT}" in joined or "CLAUDE_PLUGIN_ROOT" in joined


def test_hooks_scripts_exist():
    m = load_manifest()
    hooks = m.get("hooks") or []
    assert hooks, "expected at least one hook"
    for hook in hooks:
        assert "event" in hook
        assert "script" in hook
        # Resolve ${CLAUDE_PLUGIN_ROOT} to the plugin root for existence check.
        rel = hook["script"].replace("${CLAUDE_PLUGIN_ROOT}", "").lstrip("/")
        path = PLUGIN_ROOT / rel
        assert path.exists(), f"hook script missing: {path}"


def test_mcp_package_exists():
    """The MCP server command references a module that must be importable."""
    mcp_pkg = PLUGIN_ROOT / "mcp" / "src" / "kindred_mcp" / "server.py"
    assert mcp_pkg.exists()
