# Embedding Provider Strategy Research

## Problem

The embedding system is hardcoded to OpenRouter. Two services make raw HTTP calls to `OPENROUTER_BASE_URL/embeddings` with bearer auth:

1. **`mcp_embedding/`** — Standalone MCP service exposing `generate_embedding` and `generate_embeddings_batch` tools
2. **`mcp_storage/src/embedding.py`** — Inline embedding during `create_record()`, `update_record()`, and `semantic_search()`

This has two issues:
- **Provider lock-in**: Switching to Ollama or local models requires code changes, not just config
- **DRY violation**: `mcp_embedding` duplicates what `mcp_storage` already does internally. No agent needs a standalone "generate embedding" tool — they need "store data" and "search semantically", which Storage MCP handles.

## Decision: Eliminate Embedding MCP

The standalone Embedding MCP service should be removed. Embedding is a concern of the data layer (Storage MCP), not a standalone capability. Storage MCP already embeds on write and searches on read. Keeping both violates DRY and adds unnecessary infrastructure.

## Provider API Comparison

### OpenAI-Compatible (OpenRouter, OpenAI, Ollama compat, STAPI, vLLM)

- **Endpoint**: `POST {base_url}/embeddings`
- **Auth**: `Authorization: Bearer {api_key}` (empty/dummy for local)
- **Request**: `{"model": "...", "input": "text" | ["text1", "text2"]}`
- **Response**: `{"data": [{"embedding": [...], "index": 0}], "usage": {...}}`
- **Covers**: OpenRouter, OpenAI direct, Ollama `/v1/embeddings`, STAPI, vLLM, LM Studio

### Ollama Native

- **Endpoint**: `POST {base_url}/api/embeddings`
- **Auth**: None
- **Request**: `{"model": "...", "input": "text" | ["text1", "text2"]}`
- **Response**: `{"embeddings": [[...], [...]], "model": "..."}`
- **Note**: Different response format — `embeddings` array vs `data[].embedding`

### sentence-transformers (Local Python)

- **No HTTP**: Direct Python API
- **Usage**: `SentenceTransformer(model).encode(texts)` → numpy array
- **Auth**: None. Model downloaded from HuggingFace on first use.
- **Note**: Requires PyTorch. Heavy dependency. Optional.

### Anthropic

- **No embeddings API**. Partners with Voyage AI (separate service). Not relevant.

## Strategy Pattern Design

```
EmbeddingProvider (ABC)
├── OpenAICompatibleProvider   — Covers OpenRouter, OpenAI, Ollama compat, STAPI, vLLM
├── OllamaNativeProvider       — Ollama native /api/embeddings
└── SentenceTransformersProvider — Local Python, no HTTP
```

### Provider-Agnostic Config

```
EMBEDDING_PROVIDER=openai_compatible    # or: ollama, sentence_transformers
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_API_URL=https://openrouter.ai/api/v1/embeddings
EMBEDDING_API_KEY=<key>                 # empty = no auth
```

Replaces: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `EMBEDDING_MODEL`

### Where the code lives

`shared/embedding.py` — ABC + implementations + factory. Both Storage MCP and any future consumer import from here.

## Impact

- **Remove**: `mcp_embedding/` service entirely
- **Remove**: `mcp-embedding` from `docker-compose.yml`
- **Refactor**: `mcp_storage/src/embedding.py` to use `shared/embedding.py` provider
- **Update**: Docker, env vars, tests
