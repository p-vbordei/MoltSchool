async def test_healthz(api_client):
    r = await api_client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_request_id_header_echoed(api_client):
    r = await api_client.get("/healthz", headers={"x-request-id": "abc-123"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "abc-123"


async def test_request_id_generated_when_missing(api_client):
    r = await api_client.get("/healthz")
    assert r.status_code == 200
    assert r.headers.get("x-request-id")
