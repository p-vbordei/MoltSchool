from kindred.crypto.keys import pubkey_to_str, sign
from tests.api.helpers import setup_user_agent_kindred, upload_artifact_via_api


async def test_bless_artifact_flips_tier(api_client):
    # threshold=1 so a single blessing upgrades the tier
    fx = await setup_user_agent_kindred(api_client, slug="bk", bless_threshold=1)
    cid = await upload_artifact_via_api(api_client, fx)

    # Before blessing: peer-shared
    r = await api_client.get(f"/v1/kindreds/{fx.slug}/artifacts")
    assert r.json()[0]["tier"] == "peer-shared"

    # Agent blesses own artifact (v0 has no self-blessing restriction)
    sig = sign(fx.ag_sk, cid.encode()).hex()
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/artifacts/{cid}/bless",
        json={"signer_pubkey": pubkey_to_str(fx.ag_pk), "sig": sig},
    )
    assert r.status_code == 201, r.text
    assert r.json()["blessing_id"]

    # After blessing: class-blessed
    r = await api_client.get(f"/v1/kindreds/{fx.slug}/artifacts")
    assert r.json()[0]["tier"] == "class-blessed"
