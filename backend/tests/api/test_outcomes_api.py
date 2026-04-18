"""Full ask → outcome → list round-trip."""
from kindred.crypto.keys import pubkey_to_str, sign
from tests.api.helpers import (
    setup_user_agent_kindred,
    upload_artifact_via_api,
)


async def test_outcome_reports_success_flow(api_client):
    fx = await setup_user_agent_kindred(
        api_client, slug="outflow", bless_threshold=1, join_agent=True,
    )
    cid = await upload_artifact_via_api(api_client, fx, logical_name="pg-bloat")
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/artifacts/{cid}/bless",
        json={"signer_pubkey": pubkey_to_str(fx.ag_pk),
              "sig": sign(fx.ag_sk, cid.encode()).hex()},
    )
    assert r.status_code == 201, r.text

    # Ask
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/ask",
        json={"query": "pg-bloat vacuum"},
        headers={"x-agent-pubkey": pubkey_to_str(fx.ag_pk)},
    )
    assert r.status_code == 200, r.text
    audit_id = r.json()["audit_id"]

    # Report outcome=success
    r = await api_client.post(
        "/v1/ask/outcome",
        json={"audit_id": audit_id, "result": "success"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # Re-list → outcome_success_rate is now 1.0
    r = await api_client.get(f"/v1/kindreds/{fx.slug}/artifacts")
    items = r.json()
    target = next(a for a in items if a["content_id"] == cid)
    assert target["outcome_uses"] == 1
    assert target["outcome_successes"] == 1


async def test_outcome_invalid_result_400(api_client):
    fx = await setup_user_agent_kindred(
        api_client, slug="outbad", bless_threshold=1, join_agent=True,
    )
    cid = await upload_artifact_via_api(api_client, fx)
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/artifacts/{cid}/bless",
        json={"signer_pubkey": pubkey_to_str(fx.ag_pk),
              "sig": sign(fx.ag_sk, cid.encode()).hex()},
    )
    assert r.status_code == 201
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/ask",
        json={"query": "r1"},
        headers={"x-agent-pubkey": pubkey_to_str(fx.ag_pk)},
    )
    audit_id = r.json()["audit_id"]
    r = await api_client.post(
        "/v1/ask/outcome",
        json={"audit_id": audit_id, "result": "not-a-real-result"},
    )
    assert r.status_code == 400
