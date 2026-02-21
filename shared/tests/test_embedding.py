"""Tests for shared/embedding.py — provider strategy pattern."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.embedding import (
    EmbeddingProvider,
    OpenAICompatibleProvider,
    OllamaNativeProvider,
    SentenceTransformersProvider,
    create_embedding_provider,
    VALID_PROVIDERS,
)


# --- Factory Tests ---


class TestCreateEmbeddingProvider:
    def test_default_creates_openai_compatible(self, monkeypatch):
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
        provider = create_embedding_provider()
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_openai_compatible_explicit(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
        provider = create_embedding_provider()
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_ollama_provider(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
        monkeypatch.setenv("EMBEDDING_API_URL", "http://localhost:11434/api/embeddings")
        provider = create_embedding_provider()
        assert isinstance(provider, OllamaNativeProvider)

    def test_sentence_transformers_provider(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence_transformers")
        monkeypatch.setenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        provider = create_embedding_provider()
        assert isinstance(provider, SentenceTransformersProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "nonexistent")
        with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
            create_embedding_provider()

    def test_factory_passes_model(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_MODEL", "custom/model-v2")
        monkeypatch.setenv("EMBEDDING_API_KEY", "key")
        provider = create_embedding_provider()
        assert provider._model == "custom/model-v2"

    def test_factory_passes_api_url(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_API_URL", "http://custom:9999/embeddings")
        monkeypatch.setenv("EMBEDDING_API_KEY", "key")
        provider = create_embedding_provider()
        assert provider._api_url == "http://custom:9999/embeddings"

    def test_factory_passes_api_key(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_API_KEY", "sk-secret")
        provider = create_embedding_provider()
        assert provider._api_key == "sk-secret"

    def test_ollama_ignores_api_key(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
        monkeypatch.setenv("EMBEDDING_API_KEY", "should-be-ignored")
        provider = create_embedding_provider()
        assert not hasattr(provider, "_api_key")


# --- OpenAICompatibleProvider Tests ---


class TestOpenAICompatibleProvider:
    async def test_embed_single(self):
        provider = OpenAICompatibleProvider(
            api_url="http://test/embeddings",
            api_key="test-key",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}],
            "usage": {"prompt_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.embed("hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["json"]["model"] == "test-model"
        assert call_kwargs.kwargs["json"]["input"] == "hello world"
        assert "Bearer test-key" in call_kwargs.kwargs["headers"]["Authorization"]

    async def test_embed_no_auth_when_key_empty(self):
        provider = OpenAICompatibleProvider(
            api_url="http://test/embeddings",
            api_key="",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1], "index": 0}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await provider.embed("test")

        call_kwargs = mock_client.post.call_args
        assert "Authorization" not in call_kwargs.kwargs["headers"]

    async def test_embed_batch_sorts_by_index(self):
        provider = OpenAICompatibleProvider(
            api_url="http://test/embeddings",
            api_key="key",
            model="model",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.3], "index": 2},
                {"embedding": [0.1], "index": 0},
                {"embedding": [0.2], "index": 1},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.embed_batch(["a", "b", "c"])

        assert result == [[0.1], [0.2], [0.3]]
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["json"]["input"] == ["a", "b", "c"]

    async def test_embed_raises_on_http_error(self):
        provider = OpenAICompatibleProvider(
            api_url="http://test/embeddings",
            api_key="key",
            model="model",
        )
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(Exception, match="500 Server Error"):
                await provider.embed("test")


# --- OllamaNativeProvider Tests ---


class TestOllamaNativeProvider:
    async def test_embed_single(self):
        provider = OllamaNativeProvider(
            api_url="http://localhost:11434/api/embeddings",
            model="nomic-embed-text",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embeddings": [[0.4, 0.5, 0.6]],
            "model": "nomic-embed-text",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.embed("test text")

        assert result == [0.4, 0.5, 0.6]
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["json"]["model"] == "nomic-embed-text"
        assert "Authorization" not in call_kwargs.kwargs.get("headers", {})

    async def test_embed_batch(self):
        provider = OllamaNativeProvider(
            api_url="http://localhost:11434/api/embeddings",
            model="nomic-embed-text",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("shared.embedding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.embed_batch(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["json"]["input"] == ["text1", "text2"]


# --- SentenceTransformersProvider Tests ---


class TestSentenceTransformersProvider:
    async def test_embed_single(self):
        provider = SentenceTransformersProvider(model="all-MiniLM-L6-v2")

        mock_model = MagicMock()
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.7, 0.8, 0.9]
        mock_model.encode.return_value = [mock_array]

        with patch("shared.embedding.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = [[0.7, 0.8, 0.9]]
            result = await provider.embed("test text")

        assert result == [0.7, 0.8, 0.9]
        mock_to_thread.assert_called_once()

    async def test_embed_batch(self):
        provider = SentenceTransformersProvider(model="all-MiniLM-L6-v2")

        with patch("shared.embedding.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = [[0.1, 0.2], [0.3, 0.4]]
            result = await provider.embed_batch(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_to_thread.assert_called_once()

    def test_lazy_model_loading(self):
        provider = SentenceTransformersProvider(model="all-MiniLM-L6-v2")
        assert provider._model is None

        mock_st_class = MagicMock()
        mock_st_instance = MagicMock()
        mock_st_class.return_value = mock_st_instance

        with patch.dict("sys.modules", {"sentence_transformers": MagicMock(SentenceTransformer=mock_st_class)}):
            model = provider._load_model()

        assert model is mock_st_instance
        assert provider._model is mock_st_instance

    def test_model_loaded_only_once(self):
        provider = SentenceTransformersProvider(model="test-model")
        sentinel = MagicMock()
        provider._model = sentinel

        result = provider._load_model()
        assert result is sentinel


# --- ABC Tests ---


class TestEmbeddingProviderABC:
    async def test_default_embed_batch_calls_embed(self):
        """Default embed_batch loops over embed()."""

        class StubProvider(EmbeddingProvider):
            async def embed(self, text: str) -> list[float]:
                return [float(len(text))]

        provider = StubProvider()
        result = await provider.embed_batch(["hi", "hello"])
        assert result == [[2.0], [5.0]]
