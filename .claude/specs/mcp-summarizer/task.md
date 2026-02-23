# MCP Summarizer Service — Tasks

## 1. Service Scaffold, Config, Tokens, and Logging

- [x] Velasari creates `mcp_summarizer/` folder structure with `pyproject.toml`, `conftest.py`, `src/__init__.py` — _MS-4_
- [x] Velasari creates `.env.example` documenting all env vars with defaults in `mcp_summarizer/` — _MS-4_
- [x] Velasari creates `Dockerfile` for `mcp_summarizer` service with python:3.12-slim, uv, tiktoken pre-download, shared/ copy — _MS-4_
- [x] Velasari implements `src/config.py` loading env vars (port, model, API key, chunk defaults) in `mcp_summarizer` — _MS-4_
- [x] Velasari implements `src/tokens.py` with tiktoken cl100k_base count/encode/decode wrappers in `mcp_summarizer` — _MS-3_
- [x] Velasari implements `src/logging_config.py` with JSON formatter and `service_id: "mcp_summarizer"` in `mcp_summarizer` — _MS-6_
- [x] Velasari creates prompt templates (`summarize_chunk.md`, `summarize_chunk_extraction.md`, `merge_summaries.md`) in `mcp_summarizer/prompts/` — _MS-1, MS-2_
- [x] Velasari writes unit tests for config, tokens, and logging in `mcp_summarizer/tests/` — _MS-3, MS-4, MS-6_

## 2. Chunking Engine

- [x] Velasari implements `src/chunker.py` with `chunk_semantic`, `_split_by_paragraphs`, `chunk_token_based`, `chunk_content` dispatcher in `mcp_summarizer` — _MS-3_
  - [x] Semantic: three-tier split (headers/hrules → paragraphs → token-based fallback)
  - [x] Header context propagation to new chunks
  - [x] Token-based: fixed boundaries with configurable overlap
- [x] Velasari writes unit tests for chunker: split boundaries, header propagation, oversized sections, edge cases in `mcp_summarizer/tests/test_chunker.py` — _MS-3_

## 3. Map-Reduce Summarizer

- [x] Velasari implements `src/summarizer.py` with `_llm_call` (tenacity retry), `_summarize_chunk`, `map_reduce_summarize` (semaphore-bounded, reduce passes) in `mcp_summarizer` — _MS-1, MS-6_
- [x] Velasari writes unit tests for summarizer with mocked LLM: bypass, map phase, reduce phase, concurrency, retry, failure propagation in `mcp_summarizer/tests/test_summarizer.py` — _MS-1, MS-6_

## 4. MCP Server Tool Endpoints

- [x] Velasari implements `src/server.py` with FastMCP `summarize` and `summarize_for_extraction` tools, bypass logic, try/except graceful degradation in `mcp_summarizer` — _MS-1, MS-2, MS-6_
- [x] Velasari writes unit tests for server tools: bypass, template routing, graceful degradation, parameter handling in `mcp_summarizer/tests/test_server.py` — _MS-1, MS-2, MS-6_

## 5. Pipeline Integration and Docker Wiring

- [x] Velasari adds `MCP_SUMMARIZER_URL` env var to `a_world_lore_researcher/src/config.py` — _MS-5_
- [x] Velasari adds `_summarize_research_result()` to `a_world_lore_researcher/src/pipeline.py` — _MS-5_
- [x] Velasari modifies `_make_research_step()` to call `_summarize_research_result()` after `research_zone()` in `a_world_lore_researcher/src/pipeline.py` — _MS-5_
- [x] Velasari updates `a_world_lore_researcher/.env.example` with `MCP_SUMMARIZER_URL` — _MS-5_
- [x] Velasari adds `mcp-summarizer` service block to `docker-compose.yml` with healthcheck and researcher dependency — _MS-5_
- [x] Velasari writes unit tests for `_summarize_research_result()`: graceful degradation, URL empty, success path in `a_world_lore_researcher/tests/test_pipeline.py` — _MS-5_
