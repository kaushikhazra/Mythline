# Embedding Blueprint

How to wire vector embeddings in any project. Provider-agnostic, data-layer owned.

---

## Core Principle

**Embedding is infrastructure of the data layer.** It lives inside whatever service stores and retrieves data. Never create a standalone embedding service.

Think of it like indexing in a database — you don't create a separate "indexing service." The database handles indexing internally when you write data. Embedding is the same: it enables semantic search, transparently, inside the storage layer.

---

## Architecture

```
Consumer (agent, API, etc.)
    │
    ├── store("zone", data)          ← embedding happens inside
    ├── semantic_search("query")     ← uses embedding internally
    │
    ▼
Storage Layer
    ├── _build_embeddable_text()     ← domain logic: what to embed
    ├── generate_embedding()         ← delegates to provider
    │       │
    │       ▼
    │   shared/embedding.py
    │       ├── EmbeddingProvider (ABC)
    │       ├── OpenAICompatibleProvider
    │       ├── OllamaNativeProvider
    │       └── SentenceTransformersProvider
    │
    └── Database (stores vectors alongside data)
```

The consumer never sees or thinks about embeddings.

---

## Provider Strategy

Three implementations cover every mainstream embedding backend:

| Provider | Covers | Auth |
|----------|--------|------|
| `OpenAICompatibleProvider` | OpenRouter, OpenAI, Ollama `/v1`, STAPI, vLLM, LM Studio | Bearer token (optional) |
| `OllamaNativeProvider` | Ollama native `/api/embeddings` | None |
| `SentenceTransformersProvider` | HuggingFace models, local Python, no HTTP | None |

### Why Three, Not One

- Ollama's native endpoint returns `{"embeddings": [[...]]}` not `{"data": [{"embedding": [...]}]}`. Different response shape.
- sentence-transformers is a Python library call — no HTTP. Wrapping it in an HTTP client would be absurd overhead for local inference.
- OpenAI-compatible covers 90% of cases (de facto standard). The other two handle the exceptions.

---

## Configuration

Four env vars. Provider-agnostic naming — no provider names in env var keys:

```
EMBEDDING_PROVIDER=openai_compatible    # or: ollama, sentence_transformers
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_API_URL=https://openrouter.ai/api/v1/embeddings
EMBEDDING_API_KEY=<key>                 # empty = no auth
```

Switching providers is a config change, not a code change.

---

## Implementation

### The shared module (`shared/embedding.py`)

```python
class EmbeddingProvider(ABC):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

def create_embedding_provider() -> EmbeddingProvider:
    # Reads EMBEDDING_* env vars, returns the right implementation
```

- `embed_batch` has a default implementation (loop over `embed`). HTTP providers override with a single batched API call.
- `SentenceTransformersProvider` uses lazy model loading and `asyncio.to_thread()` to avoid blocking.
- Factory raises `ValueError` on unknown provider — fail fast, not silently.

### The consumer (storage layer)

```python
from shared.embedding import create_embedding_provider

_provider = None

def _get_provider():
    global _provider
    if _provider is None:
        _provider = create_embedding_provider()
    return _provider

async def generate_embedding(text: str) -> list[float] | None:
    try:
        return await _get_provider().embed(text)
    except Exception:
        return None   # graceful degradation — data still gets stored
```

- **Lazy singleton** — provider created on first use, not at import time.
- **Graceful degradation** — if embedding fails, the data is still stored without a vector. Semantic search won't find it, but nothing breaks.
- **Domain logic stays in the consumer** — `_build_embeddable_text()` decides which fields to embed per table. The provider knows nothing about the domain.

---

## Testing

- **Provider tests** live in `shared/tests/` — pure unit tests, all HTTP mocked.
- **Consumer tests** mock `_provider` directly on the embedding module.

```python
# Disable embedding in tests
emb_module._provider = _FailingProvider()
yield
emb_module._provider = None

# Enable embedding with mock
mock_provider = MagicMock()
mock_provider.embed = AsyncMock(return_value=[0.1] * 1536)
emb_module._provider = mock_provider
```

---

## Constraints

1. **Embedding lives in the data layer** — never as a standalone service.
2. **Provider-agnostic from day one** — strategy pattern + env var config.
3. **Provider-agnostic env var names** — `EMBEDDING_*` prefix, never provider-specific names.
4. **Graceful degradation** — embedding failure must not prevent data storage.
5. **Provider tests in `shared/`** — they test shared code, not any specific consumer.
