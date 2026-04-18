from kindred.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("KINDRED_DATABASE_URL", "postgresql+asyncpg://x/y")
    monkeypatch.setenv("KINDRED_FACILITATOR_SIGNING_KEY_HEX", "00" * 32)
    monkeypatch.setenv("KINDRED_OBJECT_STORE_ENDPOINT", "http://e")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_ACCESS_KEY", "k")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_SECRET_KEY", "s")
    monkeypatch.setenv("KINDRED_OBJECT_STORE_BUCKET", "b")
    s = Settings()
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert len(s.facilitator_signing_key) == 32
