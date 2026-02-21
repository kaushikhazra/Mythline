# Embedding Provider Strategy — Design

## Strategy Pattern

The embedding system uses the Strategy pattern (GoF) — an abstract interface with interchangeable implementations selected at runtime via configuration.

```
EmbeddingProvider (ABC)
├── OpenAICompatibleProvider   — OpenRouter, OpenAI, Ollama /v1, STAPI, vLLM, LM Studio
├── OllamaNativeProvider       — Ollama native /api/embeddings
└── SentenceTransformersProvider — Local Python, no HTTP
```

### Location

`shared/embedding.py` — importable by any service or agent in the repo.

---

## Abstract Interface

```python
class EmbeddingProvider(ABC):
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
```

Both methods raise on failure (no silent `None` returns). Callers handle exceptions.

`embed_batch` has a default implementation that calls `embed` in a loop — HTTP providers override with a single batched API call.

---

## Provider Implementations

### OpenAICompatibleProvider

Covers any service exposing the OpenAI `/embeddings` endpoint format.

- **Endpoint**: `POST {api_url}`
- **Auth**: `Authorization: Bearer {api_key}` (omitted if key is empty)
- **Request**: `{"model": "...", "input": "text" | ["text1", "text2"]}`
- **Response**: `{"data": [{"embedding": [...], "index": 0}], "usage": {...}}`
- **Constructor args**: `api_url`, `api_key`, `model`
- **HTTP client**: `httpx.AsyncClient` with 30s timeout

### OllamaNativeProvider

Ollama's native embedding endpoint — different response format from OpenAI.

- **Endpoint**: `POST {api_url}`
- **Auth**: None
- **Request**: `{"model": "...", "input": "text" | ["text1", "text2"]}`
- **Response**: `{"embeddings": [[...], [...]], "model": "..."}`
- **Constructor args**: `api_url`, `model`
- **HTTP client**: `httpx.AsyncClient` with 30s timeout

### SentenceTransformersProvider

Local Python embedding via HuggingFace sentence-transformers. No HTTP. Heavy dependency (PyTorch).

- **Import**: `from sentence_transformers import SentenceTransformer`
- **Usage**: `SentenceTransformer(model).encode(texts)` returns numpy arrays
- **Constructor args**: `model`
- **Lazy init**: Model loaded on first call, not at construction time
- **Thread safety**: `encode()` runs in `asyncio.to_thread()` to avoid blocking the event loop

---

## Factory

```python
def create_embedding_provider() -> EmbeddingProvider:
```

Reads environment variables and returns the correct provider:

| Env Var | Default | Purpose |
|---------|---------|---------|
| `EMBEDDING_PROVIDER` | `openai_compatible` | Provider selection key |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Model identifier |
| `EMBEDDING_API_URL` | `https://openrouter.ai/api/v1/embeddings` | HTTP endpoint (ignored for sentence_transformers) |
| `EMBEDDING_API_KEY` | _(empty)_ | API key (empty = no auth) |

Provider selection:
- `openai_compatible` -> `OpenAICompatibleProvider(api_url, api_key, model)`
- `ollama` -> `OllamaNativeProvider(api_url, model)`
- `sentence_transformers` -> `SentenceTransformersProvider(model)`
- Unknown value -> `ValueError` with available options listed

---

## Integration with Storage MCP

### Before (current)

```
mcp_storage/src/embedding.py:
  - Reads OPENROUTER_API_KEY, OPENROUTER_BASE_URL, EMBEDDING_MODEL
  - generate_embedding() makes raw httpx POST to OpenRouter
  - enrich_with_embedding() calls generate_embedding()
```

### After

```
shared/embedding.py:
  - EmbeddingProvider ABC + 3 implementations + factory

mcp_storage/src/embedding.py:
  - Creates provider via create_embedding_provider() at module level
  - generate_embedding() delegates to provider.embed()
  - _build_embeddable_text() unchanged (domain logic)
  - enrich_with_embedding() unchanged (calls generate_embedding())
```

The `generate_embedding()` function changes from returning `None` on missing API key to raising an exception. The caller (`enrich_with_embedding`) catches exceptions and returns data unchanged — preserving the current graceful degradation behavior.

---

## Docker Changes

### mcp_storage

- **Build context**: Changes from `./mcp_storage` to `.` (repo root)
- **Dockerfile path**: `mcp_storage/Dockerfile`
- **New COPY**: `COPY shared/ shared/`
- **conftest.py**: New file at `mcp_storage/conftest.py` — adds repo root to sys.path (same pattern as agents)

### mcp_embedding

- **Deleted entirely** — service, Dockerfile, folder, docker-compose entry, port 8004

---

## Environment Variable Migration

### Removed
- `OPENROUTER_API_KEY` (from mcp_storage and mcp_embedding)
- `OPENROUTER_BASE_URL` (from mcp_storage and mcp_embedding)

### Added
- `EMBEDDING_PROVIDER` — defaults to `openai_compatible`
- `EMBEDDING_API_URL` — defaults to `https://openrouter.ai/api/v1/embeddings`
- `EMBEDDING_API_KEY` — no default (must be set for cloud providers)

### Unchanged
- `EMBEDDING_MODEL` — already exists, keeps its current role

Note: `OPENROUTER_API_KEY` remains in the root `.env` and agent services that use it for LLM calls (via pydantic-ai). It's only removed from embedding-specific config.

---

## Test Strategy

### New: `shared/tests/test_embedding.py`

- Factory tests: correct provider for each `EMBEDDING_PROVIDER` value, error on unknown
- `OpenAICompatibleProvider`: mock httpx response, verify request format, auth header presence/absence
- `OllamaNativeProvider`: mock httpx response, verify different response parsing
- `SentenceTransformersProvider`: mock `sentence_transformers` import, verify `to_thread` usage
- Batch tests: verify index ordering, single-call batching

### Modified: `mcp_storage/tests/test_server.py`

- `disable_embedding` fixture: mock `create_embedding_provider` to return a provider whose `embed()` raises (or returns a fixed vector)
- `TestEmbeddingOnWrite`: mock the provider instance, not `OPENROUTER_API_KEY`
