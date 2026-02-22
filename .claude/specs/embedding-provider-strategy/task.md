# Embedding Provider Strategy — Tasks

## Step 1: Create `shared/embedding.py`

- [x] Define `EmbeddingProvider` ABC with `embed()` and `embed_batch()` abstract methods
  _US-2: Strategy Pattern for Embedding Providers_
- [x] Implement `OpenAICompatibleProvider` — httpx POST, OpenAI response format, optional auth
  _US-2: Strategy Pattern for Embedding Providers_
- [x] Implement `OllamaNativeProvider` — httpx POST, Ollama response format, no auth
  _US-2: Strategy Pattern for Embedding Providers_
- [x] Implement `SentenceTransformersProvider` — lazy model load, `asyncio.to_thread`
  _US-2: Strategy Pattern for Embedding Providers_
- [x] Implement `create_embedding_provider()` factory — reads `EMBEDDING_*` env vars
  _US-1: Provider-Agnostic Embedding Configuration_

## Step 2: Write provider tests

- [x] Test factory: correct provider for each env var value, error on unknown
  _US-5: Test Coverage_
- [x] Test `OpenAICompatibleProvider`: mock HTTP, request format, auth header, batch ordering
  _US-5: Test Coverage_
- [x] Test `OllamaNativeProvider`: mock HTTP, response parsing, batch
  _US-5: Test Coverage_
- [x] Test `SentenceTransformersProvider`: mock import, `to_thread`, lazy init
  _US-5: Test Coverage_

## Step 3: Refactor `mcp_storage/src/embedding.py`

- [x] Replace raw httpx calls with `create_embedding_provider()` delegation
  _US-4: Storage MCP Uses Shared Provider_
- [x] Remove `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` env var reads
  _US-1: Provider-Agnostic Embedding Configuration_
- [x] Update `generate_embedding()` to delegate to `provider.embed()`
  _US-4: Storage MCP Uses Shared Provider_
- [x] Keep `_build_embeddable_text()` and `enrich_with_embedding()` as-is (domain logic)
  _US-4: Storage MCP Uses Shared Provider_

## Step 4: Update `mcp_storage` Docker + config

- [x] Create `mcp_storage/conftest.py` — sys.path for shared/
  _US-4: Storage MCP Uses Shared Provider_
- [x] Update `mcp_storage/Dockerfile` — repo root context, copy `shared/`
  _US-4: Storage MCP Uses Shared Provider_
- [x] Update `mcp_storage/.env.example` — replace `OPENROUTER_*` with `EMBEDDING_*`
  _US-1: Provider-Agnostic Embedding Configuration_

## Step 5: Delete `mcp_embedding/`

- [x] Remove `mcp_embedding/` folder entirely
  _US-3: Eliminate Embedding MCP Service_
- [x] Remove `mcp-embedding` service from `docker-compose.yml`
  _US-3: Eliminate Embedding MCP Service_

## Step 6: Update `docker-compose.yml` for `mcp-storage`

- [x] Change build context to `.` with `dockerfile: mcp_storage/Dockerfile`
  _US-4: Storage MCP Uses Shared Provider_
- [x] Replace `OPENROUTER_*` env vars with `EMBEDDING_*` env vars
  _US-1: Provider-Agnostic Embedding Configuration_

## Step 7: Update `mcp_storage` tests

- [x] Update `disable_embedding` fixture to mock provider instead of `OPENROUTER_API_KEY`
  _US-5: Test Coverage_
- [x] Update `TestEmbeddingOnWrite` tests for provider-based mocking
  _US-5: Test Coverage_
- [x] Verify all existing tests pass with no regression
  _US-5: Test Coverage_

## Step 8: Update documentation

- [x] Update `CLAUDE.md` — remove `mcp_embedding` from MCP services table
  _US-3: Eliminate Embedding MCP Service_
- [x] Update blueprint notes — MCP services also use `shared/`
  _US-4: Storage MCP Uses Shared Provider_
