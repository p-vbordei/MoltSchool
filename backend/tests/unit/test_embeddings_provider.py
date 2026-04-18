import pytest

from kindred.embeddings.provider import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    get_provider,
)


@pytest.mark.asyncio
async def test_fake_provider_deterministic():
    p = FakeEmbeddingProvider()
    v1 = await p.embed("hello world")
    v2 = await p.embed("hello world")
    assert v1 == v2
    assert len(v1) == 64
    # L2 normalized → norm ~= 1
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_fake_provider_different_texts():
    p = FakeEmbeddingProvider()
    v1 = await p.embed("postgres bloat")
    v2 = await p.embed("react hooks")
    assert v1 != v2


@pytest.mark.asyncio
async def test_fake_provider_custom_dim():
    p = FakeEmbeddingProvider(dim=32)
    v = await p.embed("test")
    assert len(v) == 32


def test_get_provider_returns_fake_by_default(monkeypatch):
    monkeypatch.setenv("KINDRED_EMBEDDING_PROVIDER", "fake")
    # Force re-read of settings
    from kindred import config as config_mod
    s = config_mod.Settings()
    p = get_provider(s)
    assert isinstance(p, FakeEmbeddingProvider)


def test_get_provider_protocol():
    # EmbeddingProvider is a Protocol; FakeEmbeddingProvider satisfies it
    p: EmbeddingProvider = FakeEmbeddingProvider()
    assert hasattr(p, "embed")
