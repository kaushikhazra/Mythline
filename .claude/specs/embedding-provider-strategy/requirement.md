# Embedding Provider Strategy — Requirements

## Problem Statement

The embedding system is hardcoded to OpenRouter. Two services duplicate the same raw HTTP calls to `OPENROUTER_BASE_URL/embeddings` with bearer auth:

1. **`mcp_embedding/`** — Standalone MCP service exposing `generate_embedding` and `generate_embeddings_batch` tools.
2. **`mcp_storage/src/embedding.py`** — Inline embedding during `create_record()`, `update_record()`, and `semantic_search()`.

This creates two issues:
- **Provider lock-in**: Switching to Ollama or local models requires code changes, not just config.
- **DRY violation**: `mcp_embedding/` duplicates what `mcp_storage/` already does internally. No agent needs a standalone "generate embedding" tool — they need "store data" and "search semantically", which Storage MCP handles.

---

## User Stories

### US-1: Provider-Agnostic Embedding Configuration

As a developer, I want to configure the embedding provider via environment variables so that I can switch between OpenRouter, Ollama, local models, or any OpenAI-compatible endpoint without changing code.

**Acceptance Criteria:**
- A single set of `EMBEDDING_*` env vars controls the provider, model, URL, and auth key.
- Changing `EMBEDDING_PROVIDER` from `openai_compatible` to `ollama` switches the embedding backend with no code changes.
- The `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` env vars are no longer read by the embedding system.
- An empty `EMBEDDING_API_KEY` disables auth headers (for local providers like Ollama).

### US-2: Strategy Pattern for Embedding Providers

As a developer, I want embedding generation behind an abstract interface with concrete provider implementations so that adding a new provider means adding one class, not modifying existing code.

**Acceptance Criteria:**
- An `EmbeddingProvider` ABC defines `embed(text)` and `embed_batch(texts)`.
- `OpenAICompatibleProvider` covers OpenRouter, OpenAI, Ollama `/v1`, STAPI, vLLM, LM Studio.
- `OllamaNativeProvider` covers Ollama's native `/api/embeddings` endpoint (different response format).
- `SentenceTransformersProvider` covers local Python embedding via HuggingFace models (no HTTP).
- A factory function creates the right provider from env vars.
- The provider code lives in `shared/embedding.py` — usable by any service or agent.

### US-3: Eliminate Embedding MCP Service

As a developer, I want the standalone `mcp_embedding/` service removed so that embedding is only a concern of the data layer (Storage MCP), eliminating the DRY violation.

**Acceptance Criteria:**
- `mcp_embedding/` folder is deleted.
- `mcp-embedding` service is removed from `docker-compose.yml`.
- Port 8004 is freed.
- No agent or service references `mcp_embedding` or port 8004.

### US-4: Storage MCP Uses Shared Provider

As a developer, I want `mcp_storage/src/embedding.py` to delegate to `shared/embedding.py` so that Storage MCP benefits from the provider-agnostic strategy pattern.

**Acceptance Criteria:**
- `mcp_storage/src/embedding.py` no longer makes raw HTTP calls.
- `generate_embedding()` delegates to the shared provider's `embed()` method.
- `_build_embeddable_text()` and `enrich_with_embedding()` remain in Storage MCP (domain logic).
- Storage MCP's Dockerfile copies `shared/` into the container.
- All existing tests pass with the new provider mocking approach.

### US-5: Test Coverage

As a developer, I want unit tests for all three provider implementations and the factory so that provider switching is verified without live API calls.

**Acceptance Criteria:**
- Each provider implementation has tests with mocked HTTP responses (or mocked imports for sentence-transformers).
- Factory tests verify correct provider instantiation based on env vars.
- Existing Storage MCP tests are updated to mock the provider instead of `OPENROUTER_API_KEY`.
- No test regression — all existing tests continue to pass.
