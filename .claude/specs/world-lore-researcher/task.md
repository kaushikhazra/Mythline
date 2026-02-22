# World Lore Researcher — Tasks

## 0. Prerequisites (Infrastructure)

- [x] SurrealDB PoC — validate on Windows: embedded mode, vector search, graph traversal, CRUD, Python SDK stability
  - [x] Install SurrealDB locally and in Docker
  - [x] Create test tables matching World Lore schema (zone, npc, faction, lore, narrative_item)
  - [x] Test RELATE operations for graph edges (CONNECTS_TO, BELONGS_TO, etc.)
  - [x] Test vector search (embedding similarity query)
  - [x] Test basic CRUD operations via Python SDK (`surrealdb`)
  - [x] Document findings — pass/fail decision on SurrealDB vs Qdrant fallback
  _US-3, US-4 (storage dependency)_

- [x] Storage MCP — build the MCP service with SurrealDB backend
  - [x] Scaffold `mcp_storage/` folder with Dockerfile, pyproject.toml, .env
  - [x] Implement FastMCP server with SurrealDB connection
  - [x] Implement World Lore domain tools: create/read/update/query for zone, npc, faction, lore, narrative_item
  - [x] Implement `research_state` collection tools: save_checkpoint, load_checkpoint
  - [x] Implement embedding-on-write (call Embedding MCP when persisting)
  - [x] Docker build and test
  _US-3, US-6, US-7 (all data persistence)_

- [x] Embedding MCP — build the embedding service
  - [x] Scaffold `mcp_embedding/` folder with Dockerfile, pyproject.toml, .env
  - [x] Implement FastMCP server with OpenRouter embedding endpoint
  - [x] Implement tool: `generate_embedding(text) -> vector`
  - [x] Docker build and test
  _US-3 (storage dependency, called by Storage MCP)_

- [x] Web Search MCP — build the search service
  - [x] Scaffold `mcp_web_search/` folder with Dockerfile, pyproject.toml, .env
  - [x] Implement FastMCP server with DuckDuckGo search
  - [x] Implement tool: `search(query, max_results) -> list[SearchResult]`
  - [x] Docker build and test
  _US-4 (multi-source research)_

- [x] Web Crawler MCP — build the crawler service
  - [x] Scaffold `mcp_web_crawler/` folder with Dockerfile, pyproject.toml, .env
  - [x] Implement FastMCP server with URL content extraction
  - [x] Implement tool: `crawl_url(url) -> markdown_content`
  - [x] Docker build and test
  _US-4 (multi-source research)_

- [x] RabbitMQ — setup and configuration
  - [x] Add RabbitMQ service to docker-compose.yml with health check
  - [x] Create `knowledge.topic` exchange (topic type, durable)
  - [x] Create queues: `agent.world_lore_researcher`, `agent.world_lore_validator`, `user.decisions`
  - [x] Test publish/subscribe from Python using aio-pika
  _US-6 (validator communication)_

- [x] Docker Compose — base orchestration
  - [x] Create root docker-compose.yml with infrastructure services (RabbitMQ, SurrealDB)
  - [x] Add MCP services (storage, embedding, web_search, web_crawler)
  - [x] Configure networking, health checks, volume mounts
  - [x] Verify all services start and communicate
  _US-1 (daemon in Docker)_

## 1. Agent Scaffold

- [x] Create `a_world_lore_researcher/` folder structure
  - [x] Dockerfile
  - [x] .env with all config variables (parameterized defaults)
  - [x] pyproject.toml with dependencies (pydantic-ai, aio-pika, tenacity, aiolimiter, httpx, pyyaml, mcp)
  - [x] config/sources.yml with WoW source priority tiers
  - [x] prompts/system_prompt.md
  - [x] src/__init__.py, agent.py, daemon.py, pipeline.py, checkpoint.py, models.py, config.py
  _US-1 (daemon structure)_

## 2. Pydantic Models

- [x] Define message models in `models.py`
  - [x] MessageEnvelope — base message wrapper
  - [x] ResearchPackage — zone data + sources + confidence + conflicts
  - [x] ValidationResult — accepted/rejected with feedback
  - [x] UserDecisionRequired — question + options + context
  - [x] UserDecisionResponse — decision_id + choice
  _US-6 (validator communication), US-2 (fork decisions)_

- [x] Define data models in `models.py`
  - [x] ZoneData, NPCData, FactionData, LoreData, NarrativeItemData
  - [x] SourceReference, Conflict, ValidationFeedback
  - [x] ResearchCheckpoint
  - [x] PhaseState, NPCRelationship, FactionRelation
  _US-3 (depth-first data), US-4 (cross-referencing)_

## 3. Configuration

- [x] Implement `config.py` — load env vars with defaults
  - [x] RESEARCH_CYCLE_DELAY_MINUTES
  - [x] DAILY_TOKEN_BUDGET, PER_CYCLE_TOKEN_BUDGET
  - [x] MAX_RESEARCH_VALIDATE_ITERATIONS
  - [x] RATE_LIMIT_REQUESTS_PER_MINUTE
  - [x] STARTING_ZONE
  - [x] RABBITMQ_URL, MCP service URLs
  - [x] AGENT_ROLE (world_lore_researcher)
  _US-7 (budget controls), US-8 (rate limiting)_

- [x] Implement source priority loader from `config/sources.yml`
  _US-5 (source priority)_

## 4. Checkpoint System

- [x] Implement `checkpoint.py`
  - [x] save_checkpoint(state: ResearchCheckpoint) → Storage MCP
  - [x] load_checkpoint() → ResearchCheckpoint | None
  - [x] Daily budget reset logic (check last_reset_date vs today)
  _US-7 (budget controls), US-1 (self-healing)_

## 5. Research Pipeline

- [x] Implement `pipeline.py` — the 10-step pipeline
  - [x] Step 1: Zone overview search (Web Search MCP)
  - [x] Step 2: Zone overview crawl & extract (Web Crawler MCP)
  - [x] Step 3: NPC search
  - [x] Step 4: NPC crawl & extract
  - [x] Step 5: Faction search & extract
  - [x] Step 6: Lore & cosmology search & extract
  - [x] Step 7: Narrative items search & extract
  - [x] Step 8: Cross-reference (placeholder for LLM integration)
  - [x] Step 9: Discover connected zones
  - [x] Step 10: Package & send (package assembly)
  _US-2 (progression), US-3 (depth-first), US-4 (multi-source)_

- [x] Add checkpoint save after each step completion
  _US-1 (self-healing on crash)_

- [ ] Add pre-flight token budget check before each LLM call
  _US-7 (budget controls)_ _(deferred: requires LLM integration in agent.py)_

- [x] Add rate limiting wrappers on all MCP and LLM calls
  _US-8 (rate limiting)_

## 6. Daemon Loop

- [x] Implement `daemon.py` — main loop and lifecycle
  - [x] Startup: load config, connect RabbitMQ, connect MCP, load checkpoint
  - [x] Main loop: pick zone → run pipeline → delay → check budget → repeat
  - [x] Shutdown: save checkpoint, close connections, exit gracefully
  - [x] Signal handling (SIGTERM/SIGINT for Docker stop)
  _US-1 (autonomous daemon)_

- [ ] Implement validation response handler _(deferred: requires validator agent)_
  - [ ] Listen on researcher's RabbitMQ channel for ValidationResult messages
  - [ ] On accept: clear zone checkpoint, add to completed_zones, move to next zone
  - [ ] On reject: adjust strategy per feedback, re-run relevant pipeline steps
  - [ ] On iteration cap: discard, log, add to failed_zones, move on
  _US-6 (validator communication)_

- [ ] Implement user decision handler _(deferred: requires validator agent)_
  - [ ] Publish UserDecisionRequired to `user.decisions` queue at forks
  - [ ] Wait for UserDecisionResponse on researcher's channel
  - [ ] Reorder progression queue based on user's choice
  _US-2 (fork decisions)_

## 7. Pydantic AI Agent

- [x] Implement `agent.py` — the LLM-powered brain
  - [x] Create Pydantic AI agent with system prompt from `prompts/system_prompt.md`
  - [x] Register MCP tools (Web Search, Web Crawler via MCP Gateway)
  - [x] Implement extraction tool calls (LLM structures raw content into data models)
  - [x] Implement cross-reference tool (LLM consistency check)
  _US-3 (depth-first extraction), US-4 (cross-referencing)_

## 8. Structured Logging

- [x] Implement structured JSON logging across all modules
  - [x] Base fields: agent_id, domain, timestamp, level, event
  - [x] All 18 event types from design spec
  - [x] Hierarchical event support (parent + sub-events via extra fields)
  _US-9 (observability)_

## 9. System Prompt

- [x] Write `prompts/system_prompt.md`
  - [x] Persona: autonomous lore researcher
  - [x] Task: research MMORPG zones depth-first, structure into data model
  - [x] Instructions: search strategy, source preference, cross-referencing, conflict handling
  - [x] Constraints: stay within budget, respect rate limits, never fabricate lore
  - [x] Output: structured data matching Pydantic models
  _US-3, US-4, US-5 (research quality)_

## 10. Testing

- [x] Unit tests (91 passing)
  - [x] models.py — serialization/deserialization (19 tests)
  - [x] config.py — env var loading with defaults (14 tests)
  - [x] checkpoint.py — save/load logic (14 tests)
  - [x] pipeline.py — individual step logic (mocked MCP calls) (16 tests)
  - [x] daemon.py — zone picking, lifecycle, signals (10 tests)
  - [x] agent.py — extraction, cross-reference (10 tests)
  - [x] logging_config.py — formatter, event types (8 tests)
  _All user stories_

- [x] Integration tests (8 tests, skipped without Docker)
  - [x] Agent + Web Search MCP (real search, verify results)
  - [x] Agent + Web Crawler MCP (real crawl, verify extraction)
  - [x] Agent + Storage MCP (checkpoint save/load)
  - [x] Agent + RabbitMQ (publish/consume messages)
  _US-4, US-6, US-7_

- [x] Docker test
  - [x] Add agent to docker-compose.yml
  - [ ] Start all services, verify agent starts and connects _(manual verification needed)_
  - [ ] Verify first research cycle executes _(requires OPENROUTER_API_KEY)_
  - [ ] Verify checkpoint persists across container restart _(requires OPENROUTER_API_KEY)_
  _US-1 (Docker-first)_
