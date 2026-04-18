"""Embedding providers — FakeEmbeddingProvider (tests) + OpenAIEmbeddingProvider (prod).

The provider abstraction lets the librarian retrieve artefacts with cosine similarity
regardless of backend. Fake is deterministic hash-based so unit tests never hit the
network. OpenAI is the production path.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol, runtime_checkable

from kindred.config import Settings


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Produces a dense vector for a text. Async so OpenAI can be awaited."""

    async def embed(self, text: str) -> list[float]: ...


class FakeEmbeddingProvider:
    """Deterministic hash-based provider. Test-only.

    Expands sha256(text) into `dim` floats in [-1, 1], L2-normalized. Different
    texts yield different vectors, same text always identical. Distinct from
    OpenAI's 1536-dim space — the default 64-dim keeps unit tests tiny.
    """

    def __init__(self, dim: int = 64) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        needed_bytes = self.dim * 4  # 4 bytes per float32
        buf = b""
        counter = 0
        # sha256 gives 32 bytes; iterate to fill buffer for large dims
        while len(buf) < needed_bytes:
            h = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            buf += h
            counter += 1
        raw = buf[:needed_bytes]
        # Each 4-byte chunk → int32 → scaled into [-1, 1]
        values: list[float] = []
        for i in range(self.dim):
            (as_int,) = struct.unpack(">i", raw[i * 4 : (i + 1) * 4])
            values.append(as_int / 2147483648.0)  # divide by 2^31
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:
            return values
        return [v / norm for v in values]


class OpenAIEmbeddingProvider:
    """Production provider backed by OpenAI's text-embedding-3-small (1536-dim)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(model=self.model, input=text)
        return list(resp.data[0].embedding)


def get_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Factory reading Settings.embedding_provider. Defaults to fake."""
    if settings is None:
        settings = Settings()
    name = getattr(settings, "embedding_provider", "fake")
    if name == "fake":
        return FakeEmbeddingProvider()
    if name == "openai":
        key = settings.openai_api_key
        if key is None:
            raise ValueError("openai provider requires openai_api_key")
        return OpenAIEmbeddingProvider(api_key=key.get_secret_value())
    raise ValueError(f"unknown embedding_provider: {name}")
