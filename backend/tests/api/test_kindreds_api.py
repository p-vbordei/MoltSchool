from kindred.crypto.keys import generate_keypair, pubkey_to_str


async def test_create_kindred_happy_path(api_client):
    _, pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": "alice@x", "display_name": "Alice", "pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text

    r = await api_client.post(
        "/v1/kindreds",
        json={"slug": "heist-crew", "display_name": "Heist Crew"},
        headers={"x-owner-pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["slug"] == "heist-crew"
    assert data["display_name"] == "Heist Crew"
    assert data["bless_threshold"] == 2

    r = await api_client.get("/v1/kindreds/heist-crew")
    assert r.status_code == 200
    assert r.json()["display_name"] == "Heist Crew"


async def test_create_kindred_missing_header(api_client):
    r = await api_client.post(
        "/v1/kindreds", json={"slug": "x", "display_name": "X"}
    )
    # Missing required header -> FastAPI returns 422
    assert r.status_code == 422


async def test_get_unknown_kindred_404(api_client):
    r = await api_client.get("/v1/kindreds/nonexistent")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "NotFoundError"


async def test_install_public_kindred_mints_invite(api_client):
    _, pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": "pub@x", "display_name": "Pub", "pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text

    r = await api_client.post(
        "/v1/kindreds",
        json={
            "slug": "open-grimoire",
            "display_name": "Open Grimoire",
            "is_public": True,
        },
        headers={"x-owner-pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_public"] is True

    r = await api_client.post("/v1/kindreds/open-grimoire/install")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "/k/open-grimoire?inv=" in body["invite_url"]
    assert body["expires_at"]


async def test_install_private_kindred_forbidden(api_client):
    _, pk = generate_keypair()
    r = await api_client.post(
        "/v1/users",
        json={"email": "priv@x", "display_name": "Priv", "pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text

    # is_public defaults to False.
    r = await api_client.post(
        "/v1/kindreds",
        json={"slug": "closed-crew", "display_name": "Closed Crew"},
        headers={"x-owner-pubkey": pubkey_to_str(pk)},
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_public"] is False

    r = await api_client.post("/v1/kindreds/closed-crew/install")
    assert r.status_code == 403


async def test_install_unknown_kindred_404(api_client):
    r = await api_client.post("/v1/kindreds/does-not-exist/install")
    assert r.status_code == 404


async def test_kindred_bad_owner_header_is_400_or_401(api_client):
    # non-hex after prefix
    r = await api_client.post(
        "/v1/kindreds",
        json={"slug": "x", "display_name": "X"},
        headers={"x-owner-pubkey": "ed25519:not-hex"},
    )
    # require_owner_pubkey returns 401 directly; global ValueError handler would return 400
    assert r.status_code in (400, 401)
