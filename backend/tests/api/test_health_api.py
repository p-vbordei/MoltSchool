"""API-level tests for GET /v1/kindreds/{slug}/health."""
from kindred.crypto.keys import pubkey_to_str
from tests.api.helpers import setup_user_agent_kindred


async def test_health_endpoint_returns_all_four_indicators(api_client):
    fx = await setup_user_agent_kindred(
        api_client, slug="h-ok", bless_threshold=2, join_agent=True,
    )
    r = await api_client.get(
        f"/v1/kindreds/{fx.slug}/health",
        headers={"x-agent-pubkey": pubkey_to_str(fx.ag_pk)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kindred_slug"] == fx.slug
    assert "retrieval_utility" in body
    assert "ttfur" in body
    assert "trust_propagation" in body
    assert "staleness_cost" in body
    assert set(body["retrieval_utility"].keys()) == {
        "total_asks", "total_outcomes", "success_rate",
        "mean_rank_of_chosen", "top1_precision",
    }


async def test_health_endpoint_rejects_non_member(api_client):
    # Create a member for kindred A...
    fx = await setup_user_agent_kindred(
        api_client, slug="h-member", bless_threshold=2, join_agent=True,
    )
    # ...and a different agent who has valid attestation but is NOT in that kindred.
    outsider = await setup_user_agent_kindred(
        api_client, slug="h-outside", email="o@x",
        bless_threshold=2, join_agent=False,
    )
    r = await api_client.get(
        f"/v1/kindreds/{fx.slug}/health",
        headers={"x-agent-pubkey": pubkey_to_str(outsider.ag_pk)},
    )
    assert r.status_code == 403, r.text
