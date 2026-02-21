"""Provider-agnostic embedding generation.

Strategy pattern with three provider implementations:
- OpenAICompatibleProvider: OpenRouter, OpenAI, Ollama /v1, STAPI, vLLM, LM Studio
- OllamaNativeProvider: Ollama native /api/embeddings endpoint
- SentenceTransformersProvider: Local Python via HuggingFace sentence-transformers

Usage:
    from shared.embedding import create_embedding_provider

    provider = create_embedding_provider()
    vector = await provider.embed("some text")
    vectors = await provider.embed_batch(["text1", "text2"])
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod

import httpx


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Default implementation calls embed() in sequence.
        HTTP providers override with a single batched API call.
        """
        return [await self.embed(t) for t in texts]


class OpenAICompatibleProvider(EmbeddingProvider):
    """Provider for any OpenAI-compatible embedding endpoint.

    Covers: OpenRouter, OpenAI, Ollama /v1/embeddings, STAPI, vLLM, LM Studio.
    """

    def __init__(self, api_url: str, api_key: str, model: str) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                headers=headers,
                json={"model": self._model, "input": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                headers=headers,
                json={"model": self._model, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]


class OllamaNativeProvider(EmbeddingProvider):
    """Provider for Ollama's native /api/embeddings endpoint.

    Different response format from OpenAI: {"embeddings": [[...], [...]]}
    """

    def __init__(self, api_url: str, model: str) -> None:
        self._api_url = api_url
        self._model = model

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                json={"model": self._model, "input": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                json={"model": self._model, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]


class SentenceTransformersProvider(EmbeddingProvider):
    """Provider for local embedding via HuggingFace sentence-transformers.

    No HTTP calls. Model is downloaded on first use.
    Runs encode() in a thread to avoid blocking the event loop.
    """

    def __init__(self, model: str) -> None:
        self._model_name = model
        self._model = None

    def _load_model(self):
        """Lazy-load the sentence-transformers model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        """Synchronous encode — called via asyncio.to_thread."""
        model = self._load_model()
        embeddings = model.encode(texts)
        return [e.tolist() for e in embeddings]

    async def embed(self, text: str) -> list[float]:
        results = await asyncio.to_thread(self._encode, [text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts)


VALID_PROVIDERS = {"openai_compatible", "ollama", "sentence_transformers"}


def create_embedding_provider() -> EmbeddingProvider:
    """Create an embedding provider from environment variables.

    Env vars:
        EMBEDDING_PROVIDER: openai_compatible (default) | ollama | sentence_transformers
        EMBEDDING_MODEL: Model identifier (e.g., openai/text-embedding-3-small)
        EMBEDDING_API_URL: HTTP endpoint for the provider
        EMBEDDING_API_KEY: API key (empty = no auth)
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "openai_compatible")
    model = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    api_url = os.getenv("EMBEDDING_API_URL", "https://openrouter.ai/api/v1/embeddings")
    api_key = os.getenv("EMBEDDING_API_KEY", "")

    if provider == "openai_compatible":
        return OpenAICompatibleProvider(api_url, api_key, model)

    if provider == "ollama":
        return OllamaNativeProvider(api_url, model)

    if provider == "sentence_transformers":
        return SentenceTransformersProvider(model)

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER: '{provider}'. "
        f"Valid options: {', '.join(sorted(VALID_PROVIDERS))}"
    )
