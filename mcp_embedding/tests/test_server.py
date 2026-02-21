"""Tests for the Embedding MCP server."""

import json
import os
from unittest.mock import patch

import httpx
import pytest
import respx

import src.server as server_module
from src.server import generate_embedding, generate_embeddings_batch


MOCK_API_KEY = "test-api-key-12345"
MOCK_BASE_URL = "https://openrouter.ai/api/v1"


def make_embedding_response(embeddings: list[list[float]]) -> dict:
    """Helper to construct a mock OpenRouter embedding response."""
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": emb, "index": i}
            for i, emb in enumerate(embeddings)
        ],
        "model": "openai/text-embedding-3-small",
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }


def make_single_vector(dim: int = 8, seed: float = 0.1) -> list[float]:
    """Generate a deterministic fake embedding vector."""
    return [seed + i * 0.01 for i in range(dim)]


@pytest.fixture(autouse=True)
def set_env_vars():
    """Set required environment variables for all tests."""
    with patch.object(server_module, "OPENROUTER_API_KEY", MOCK_API_KEY), \
         patch.object(server_module, "OPENROUTER_BASE_URL", MOCK_BASE_URL), \
         patch.object(server_module, "EMBEDDING_MODEL", "openai/text-embedding-3-small"):
        yield


class TestGenerateEmbedding:
    """Tests for the generate_embedding tool."""

    @respx.mock
    async def test_returns_embedding_vector(self):
        """Successful embedding generation returns a list of floats."""
        expected_vector = make_single_vector()
        respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(
                200, json=make_embedding_response([expected_vector])
            )
        )

        result = await generate_embedding("Hello world")

        assert result == expected_vector
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    @respx.mock
    async def test_sends_correct_request(self):
        """Verify the request payload and headers are correct."""
        route = respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(
                200, json=make_embedding_response([make_single_vector()])
            )
        )

        await generate_embedding("Test text for embedding")

        assert route.called
        request = route.calls.last.request
        body = json.loads(request.content)
        assert body["model"] == "openai/text-embedding-3-small"
        assert body["input"] == "Test text for embedding"
        assert request.headers["authorization"] == f"Bearer {MOCK_API_KEY}"

    async def test_empty_text_raises_error(self):
        """Empty text should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await generate_embedding("")

    async def test_whitespace_text_raises_error(self):
        """Whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await generate_embedding("   ")

    async def test_missing_api_key_raises_error(self):
        """Missing API key should raise RuntimeError."""
        with patch.object(server_module, "OPENROUTER_API_KEY", ""):
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                await generate_embedding("test")

    @respx.mock
    async def test_api_error_propagates(self):
        """HTTP errors from OpenRouter should propagate."""
        respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(429, json={"error": "rate limited"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await generate_embedding("test")

    @respx.mock
    async def test_handles_large_text(self):
        """Should handle reasonably large text input."""
        large_text = "word " * 1000
        respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(
                200, json=make_embedding_response([make_single_vector(1536)])
            )
        )

        result = await generate_embedding(large_text)

        assert len(result) == 1536


class TestGenerateEmbeddingsBatch:
    """Tests for the generate_embeddings_batch tool."""

    @respx.mock
    async def test_returns_multiple_vectors(self):
        """Batch embedding returns one vector per input text."""
        vectors = [make_single_vector(8, seed=0.1 * i) for i in range(3)]
        respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(
                200, json=make_embedding_response(vectors)
            )
        )

        result = await generate_embeddings_batch(["text1", "text2", "text3"])

        assert len(result) == 3
        assert result == vectors

    @respx.mock
    async def test_preserves_order_from_shuffled_response(self):
        """Results should be sorted by index even if API returns them unordered."""
        vec_0 = make_single_vector(4, seed=0.0)
        vec_1 = make_single_vector(4, seed=1.0)
        vec_2 = make_single_vector(4, seed=2.0)

        shuffled_response = {
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": vec_2, "index": 2},
                {"object": "embedding", "embedding": vec_0, "index": 0},
                {"object": "embedding", "embedding": vec_1, "index": 1},
            ],
            "model": "openai/text-embedding-3-small",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

        respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(200, json=shuffled_response)
        )

        result = await generate_embeddings_batch(["a", "b", "c"])

        assert result[0] == vec_0
        assert result[1] == vec_1
        assert result[2] == vec_2

    @respx.mock
    async def test_sends_list_input(self):
        """Batch should send all texts in a single API call as a list."""
        route = respx.post(f"{MOCK_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(
                200,
                json=make_embedding_response(
                    [make_single_vector(4) for _ in range(2)]
                ),
            )
        )

        await generate_embeddings_batch(["first", "second"])

        assert route.call_count == 1
        body = json.loads(route.calls.last.request.content)
        assert body["input"] == ["first", "second"]

    async def test_empty_list_raises_error(self):
        """Empty texts list should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            await generate_embeddings_batch([])

    async def test_list_with_empty_string_raises_error(self):
        """List containing empty strings should raise ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            await generate_embeddings_batch(["valid", "", "also valid"])

    async def test_missing_api_key_raises_error(self):
        """Missing API key should raise RuntimeError."""
        with patch.object(server_module, "OPENROUTER_API_KEY", ""):
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                await generate_embeddings_batch(["test"])


class TestServerConfiguration:
    """Tests for server configuration and setup."""

    def test_server_name(self):
        """Server should have the correct name."""
        assert server_module.server.name == "Embedding Service"

    def test_default_model(self):
        """Default model should be text-embedding-3-small."""
        assert "text-embedding-3-small" in server_module.EMBEDDING_MODEL

    def test_tools_registered(self):
        """Both tools should be registered on the server."""
        tool_names = [
            tool.name for tool in server_module.server._tool_manager.list_tools()
        ]
        assert "generate_embedding" in tool_names
        assert "generate_embeddings_batch" in tool_names
