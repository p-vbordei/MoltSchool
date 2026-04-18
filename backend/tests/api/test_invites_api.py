import base64

from kindred.crypto.keys import pubkey_to_str, sign
from tests.api.helpers import setup_user_agent_kindred


async def test_issue_invite_happy_path(api_client):
    fx = await setup_user_agent_kindred(api_client, slug="cabal")
    inv_body = b"invite-body"
    issuer_sig = sign(fx.owner_sk, inv_body).hex()
    r = await api_client.post(
        f"/v1/kindreds/{fx.slug}/invites",
        json={
            "expires_in_days": 7,
            "max_uses": 1,
            "issuer_sig": issuer_sig,
            "inv_body_b64": base64.b64encode(inv_body).decode(),
        },
        headers={"x-owner-pubkey": pubkey_to_str(fx.owner_pk)},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["token"]
    assert data["max_uses"] == 1
    assert data["uses"] == 0
