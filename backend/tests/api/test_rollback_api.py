from kindred.crypto.keys import pubkey_to_str
from tests.api.helpers import setup_user_agent_kindred, upload_artifact_via_api


async def test_rollback_removes_artifact(api_client):
    fx = await setup_user_agent_kindred(api_client, slug="rb")
    await upload_artifact_via_api(api_client, fx)

    # Confirm artifact exists
    r = await api_client.get(f"/v1/kindreds/{fx.slug}/artifacts")
    assert len(r.json()) == 1

    # Rollback to seq 1 (kindred_created is seq 1; artifact_uploaded is seq 2).
    # Reverting events with seq > 1 removes the artifact_uploaded event.
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/rollback",
        json={"up_to_seq": 1},
        headers={"x-owner-pubkey": pubkey_to_str(fx.owner_pk)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rolled_back_to"] == 1

    # Artifact gone
    r = await api_client.get(f"/v1/kindreds/{fx.slug}/artifacts")
    assert r.json() == []
