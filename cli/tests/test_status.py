"""Tests for `kin status`."""
from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from kindred_client.cli import app
from kindred_client.config import Config, KindredEntry, save_config

BACKEND = "http://test.local"
runner = CliRunner()


def test_status_empty(fake_home):
    save_config(Config(backend_url=BACKEND))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No kindreds joined" in result.stdout


@respx.mock
def test_status_renders_table(fake_home):
    save_config(
        Config(
            backend_url=BACKEND,
            active_agent_id="a",
            kindreds=[
                KindredEntry(slug="heist", backend_url=BACKEND, user_id="u"),
                KindredEntry(slug="other", backend_url=BACKEND, user_id="u"),
            ],
        )
    )
    respx.get(f"{BACKEND}/v1/kindreds/heist").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "k1", "slug": "heist", "display_name": "Heist Crew",
                "description": "", "bless_threshold": 2,
            },
        )
    )
    respx.get(f"{BACKEND}/v1/kindreds/heist/artifacts").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "content_id": "sha256:a", "type": "routine", "logical_name": "r1",
                    "tier": "unproven", "valid_from": "x", "valid_until": "x",
                    "outcome_uses": 0, "outcome_successes": 0,
                }
            ],
        )
    )
    respx.get(f"{BACKEND}/v1/kindreds/other").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "k2", "slug": "other", "display_name": "Other",
                "description": "", "bless_threshold": 2,
            },
        )
    )
    respx.get(f"{BACKEND}/v1/kindreds/other/artifacts").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.stdout
    assert "heist" in result.stdout
    assert "Heist Crew" in result.stdout
    assert "other" in result.stdout
    assert "Other" in result.stdout


@respx.mock
def test_status_handles_server_errors_per_row(fake_home):
    save_config(
        Config(
            backend_url=BACKEND,
            kindreds=[KindredEntry(slug="gone", backend_url=BACKEND)],
        )
    )
    respx.get(f"{BACKEND}/v1/kindreds/gone").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "HTTP 404" in result.stdout
