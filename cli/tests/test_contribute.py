"""Tests for `kin contribute` and `kin save`."""
from __future__ import annotations

import base64
import json

import httpx
import respx
from typer.testing import CliRunner

from kindred_client import crypto
from kindred_client.cli import app
from kindred_client.commands.contribute import build_metadata
from kindred_client.config import Config, KindredEntry, save_config
from kindred_client.keystore import store_keypair

BACKEND = "http://test.local"
runner = CliRunner()


def _seed_agent(fake_home) -> tuple[bytes, bytes]:
    ag_sk, ag_pk = crypto.generate_keypair()
    store_keypair("agent-xyz", ag_sk, ag_pk)
    cfg = Config(
        backend_url=BACKEND,
        active_agent_id="agent-xyz",
        kindreds=[KindredEntry(slug="heist", backend_url=BACKEND, user_id="u-1")],
    )
    save_config(cfg)
    return ag_sk, ag_pk


def test_build_metadata_shape():
    body = b"# title\nbody"
    m = build_metadata(
        type_="routine",
        logical_name="r1",
        kindred_id="k-1",
        body=body,
        tags=["a", "b"],
    )
    assert m["kaf_version"] == "0.1"
    assert m["type"] == "routine"
    assert m["logical_name"] == "r1"
    assert m["kindred_id"] == "k-1"
    assert m["tags"] == ["a", "b"]
    assert m["body_sha256"] == crypto.compute_content_id(body)
    assert "valid_from" in m and "valid_until" in m


@respx.mock
def test_contribute_signs_cid_and_sends_base64_body(fake_home, tmp_path):
    ag_sk, ag_pk = _seed_agent(fake_home)

    # Write a small routine file
    file = tmp_path / "runbook.md"
    file.write_text("# How we ship\n1. Review\n2. Deploy")

    respx.get(f"{BACKEND}/v1/kindreds/heist").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "k-1",
                "slug": "heist",
                "display_name": "Heist",
                "description": "",
                "bless_threshold": 2,
            },
        )
    )
    upload_route = respx.post(f"{BACKEND}/v1/kindreds/heist/artifacts").mock(
        return_value=httpx.Response(
            201,
            json={
                "content_id": "sha256:server-cid",
                "type": "routine",
                "logical_name": "runbook",
                "tier": "unproven",
                "valid_from": "2026-04-18T00:00:00+00:00",
                "valid_until": "2026-10-18T00:00:00+00:00",
                "outcome_uses": 0,
                "outcome_successes": 0,
            },
        )
    )

    result = runner.invoke(
        app,
        [
            "contribute",
            "heist",
            "--type", "routine",
            "--file", str(file),
            "--tag", "deploy",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Contributed" in result.stdout
    assert "sha256:server-cid" in result.stdout

    sent = json.loads(upload_route.calls[0].request.content)
    assert sent["author_pubkey"] == crypto.pubkey_to_str(ag_pk)

    # Body round-trips
    assert base64.b64decode(sent["body_b64"]) == file.read_bytes()

    # metadata contains deploy tag + kindred_id from GET
    assert sent["metadata"]["tags"] == ["deploy"]
    assert sent["metadata"]["kindred_id"] == "k-1"
    assert sent["metadata"]["logical_name"] == "runbook"

    # Signature: agent_sk signed cid.encode()
    cid = crypto.compute_content_id(sent["metadata"])
    assert crypto.verify(ag_pk, cid.encode(), bytes.fromhex(sent["author_sig"]))


def test_contribute_rejects_bad_type(fake_home, tmp_path):
    _seed_agent(fake_home)
    f = tmp_path / "x.md"
    f.write_text("x")
    result = runner.invoke(
        app, ["contribute", "heist", "--type", "bogus", "--file", str(f)]
    )
    assert result.exit_code == 2
    assert "Invalid --type" in result.stdout


def test_contribute_no_agent(fake_home, tmp_path):
    f = tmp_path / "x.md"
    f.write_text("x")
    result = runner.invoke(
        app, ["contribute", "heist", "--type", "routine", "--file", str(f)]
    )
    assert result.exit_code == 2
    assert "no active agent" in result.stdout


def test_contribute_unknown_kindred_errors(fake_home, tmp_path):
    _seed_agent(fake_home)
    f = tmp_path / "x.md"
    f.write_text("x")
    # No kindred entry for "other"
    result = runner.invoke(
        app, ["contribute", "other", "--type", "routine", "--file", str(f)]
    )
    assert result.exit_code == 2
    assert "not joined" in result.stdout
