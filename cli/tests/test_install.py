"""Tests for `kin install`."""
from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from kindred_client.cli import app

BACKEND = "http://test.local"
INVITE_URL = f"{BACKEND}/k/claude-code-patterns?inv=mint-xyz"

runner = CliRunner()


def _mock_join_endpoints():
    """Return respx routes matching the happy-path join flow used by install."""
    return {
        "users": respx.post(f"{BACKEND}/v1/users").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "u-1",
                    "email": "a@b",
                    "display_name": "Alice",
                    "pubkey": "ed25519:00",
                },
            )
        ),
        "agents": respx.post(f"{BACKEND}/v1/users/u-1/agents").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "ag-1",
                    "owner_id": "u-1",
                    "pubkey": "ed25519:00",
                    "display_name": "Alice",
                },
            )
        ),
        "join": respx.post(f"{BACKEND}/v1/join").mock(
            return_value=httpx.Response(
                201, json={"membership_id": "m-1", "kindred_id": "k-1"}
            )
        ),
    }


@respx.mock
def test_install_with_invite_url_is_equivalent_to_join(fake_home):
    routes = _mock_join_endpoints()

    result = runner.invoke(
        app, ["install", INVITE_URL, "--email", "a@b", "--name", "Alice"]
    )
    assert result.exit_code == 0, result.stdout
    assert "Installed" in result.stdout
    assert "claude-code-patterns" in result.stdout
    assert routes["users"].called
    assert routes["join"].called


@respx.mock
def test_install_with_slug_fetches_invite_then_joins(fake_home):
    install_route = respx.post(
        f"{BACKEND}/v1/kindreds/claude-code-patterns/install"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"invite_url": INVITE_URL, "expires_at": "2026-04-23T13:00:00Z"},
        )
    )
    routes = _mock_join_endpoints()

    result = runner.invoke(
        app,
        [
            "install",
            "claude-code-patterns",
            "--backend",
            BACKEND,
            "--email",
            "a@b",
            "--name",
            "Alice",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert install_route.called
    assert routes["join"].called


@respx.mock
def test_install_with_slug_surfaces_403_for_private_kindred(fake_home):
    respx.post(f"{BACKEND}/v1/kindreds/closed-crew/install").mock(
        return_value=httpx.Response(
            403, json={"detail": "kindred is not public"}
        )
    )

    result = runner.invoke(
        app, ["install", "closed-crew", "--backend", BACKEND]
    )
    assert result.exit_code == 1
    # Friendly message in the CLI overrides the raw backend detail.
    assert "not public" in result.stdout or "Install failed" in result.stdout


