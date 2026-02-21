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

- [ ] Web Search MCP — build the search service
  - [ ] Scaffold `mcp_web_search/` folder with Dockerfile, pyproject.toml, .env
  - [ ] Implement FastMCP server with DuckDuckGo search
  - [ ] Implement tool: `search(query, max_results) -> list[SearchResult]`
  - [ ] Docker build and test
  _US-4 (multi-source research)_

- [ ] Web Crawler MCP — build the crawler service
  - [ ] Scaffold `mcp_web_crawler/` folder with Dockerfile, pyproject.toml, .env
  - [ ] Implement FastMCP server with URL content extraction
  - [ ] Implement tool: `crawl_url(url) -> markdown_content`
  - [ ] Docker build and test
  _US-4 (multi-source research)_

- [ ] RabbitMQ — setup and configuration
  - [ ] Add RabbitMQ service to docker-compose.yml with health check
  - [ ] Create `knowledge.topic` exchange (topic type, durable)
  - [ ] Create queues: `agent.world_lore_researcher`, `agent.world_lore_validator`, `user.decisions`
  - [ ] Test publish/subscribe from Python using aio-pika
  _US-6 (validator communication)_

- [ ] Docker Compose — base orchestration
  - [ ] Create root docker-compose.yml with infrastructure services (RabbitMQ, SurrealDB)
  - [ ] Add MCP services (storage, embedding, web_search, web_crawler)
  - [ ] Configure networking, health checks, volume mounts
  - [ ] Verify all services start and communicate
  _US-1 (daemon in Docker)_

## 1. Agent Scaffold

- [ ] Create `a_world_lore_researcher/` folder structure
  - [ ] Dockerfile
  - [ ] .env with all config variables (parameterized defaults)
  - [ ] pyproject.toml with dependencies (pydantic-ai, aio-pika, tenacity, aiolimiter, tokencost, apscheduler)
  - [ ] config/sources.yml with WoW source priority tiers
  - [ ] prompts/system_prompt.md
  - [ ] src/__init__.py, agent.py, daemon.py, pipeline.py, checkpoint.py, models.py, config.py
  _US-1 (daemon structure)_

## 2. Pydantic Models

- [ ] Define message models in `models.py`
  - [ ] MessageEnvelope — base message wrapper
  - [ ] ResearchPackage — zone data + sources + confidence + conflicts
  - [ ] ValidationResult — accepted/rejected with feedback
  - [ ] UserDecisionRequired — question + options + context
  - [ ] UserDecisionResponse — decision_id + choice
  _US-6 (validator communication), US-2 (fork decisions)_

- [ ] Define data models in `models.py`
  - [ ] ZoneData, NPCData, FactionData, LoreData, NarrativeItemData
  - [ ] SourceReference, Conflict, ValidationFeedback
  - [ ] ResearchCheckpoint
  - [ ] PhaseState, NPCRelationship, FactionRelation
  _US-3 (depth-first data), US-4 (cross-referencing)_

## 3. Configuration

- [ ] Implement `config.py` — load env vars with defaults
  - [ ] RESEARCH_CYCLE_DELAY_MINUTES
  - [ ] DAILY_TOKEN_BUDGET, PER_CYCLE_TOKEN_BUDGET
  - [ ] MAX_RESEARCH_VALIDATE_ITERATIONS
  - [ ] RATE_LIMIT_REQUESTS_PER_MINUTE
  - [ ] STARTING_ZONE
  - [ ] RABBITMQ_URL, MCP_GATEWAY_URL
  - [ ] AGENT_ROLE (world_lore_researcher)
  _US-7 (budget controls), US-8 (rate limiting)_

- [ ] Implement source priority loader from `config/sources.yml`
  _US-5 (source priority)_

## 4. Checkpoint System

- [ ] Implement `checkpoint.py`
  - [ ] save_checkpoint(state: ResearchCheckpoint) → Storage MCP
  - [ ] load_checkpoint() → ResearchCheckpoint | None
  - [ ] Daily budget reset logic (check last_reset_date vs today)
  _US-7 (budget controls), US-1 (self-healing)_

## 5. Research Pipeline

- [ ] Implement `pipeline.py` — the 10-step pipeline
  - [ ] Step 1: Zone overview search (Web Search MCP)
  - [ ] Step 2: Zone overview crawl & LLM extract (Web Crawler MCP + Pydantic AI)
  - [ ] Step 3: NPC search
  - [ ] Step 4: NPC crawl & extract
  - [ ] Step 5: Faction search & extract
  - [ ] Step 6: Lore & cosmology search & extract
  - [ ] Step 7: Narrative items search & extract
  - [ ] Step 8: Cross-reference & conflict detection (LLM review)
  - [ ] Step 9: Discover connected zones (internal queue update, user fork decision)
  - [ ] Step 10: Package & send to validator (RabbitMQ publish)
  _US-2 (progression), US-3 (depth-first), US-4 (multi-source)_

- [ ] Add checkpoint save after each step completion
  _US-1 (self-healing on crash)_

- [ ] Add pre-flight token budget check before each LLM call
  _US-7 (budget controls)_

- [ ] Add rate limiting wrappers on all MCP and LLM calls
  _US-8 (rate limiting)_

## 6. Daemon Loop

- [ ] Implement `daemon.py` — main loop and lifecycle
  - [ ] Startup: load config, connect RabbitMQ, connect MCP, load checkpoint
  - [ ] Main loop: pick zone → run pipeline → delay → check budget → repeat
  - [ ] Shutdown: save checkpoint, close connections, exit gracefully
  - [ ] Signal handling (SIGTERM/SIGINT for Docker stop)
  _US-1 (autonomous daemon)_

- [ ] Implement validation response handler
  - [ ] Listen on researcher's RabbitMQ channel for ValidationResult messages
  - [ ] On accept: clear zone checkpoint, add to completed_zones, move to next zone
  - [ ] On reject: adjust strategy per feedback, re-run relevant pipeline steps
  - [ ] On iteration cap: discard, log, add to failed_zones, move on
  _US-6 (validator communication)_

- [ ] Implement user decision handler
  - [ ] Publish UserDecisionRequired to `user.decisions` queue at forks
  - [ ] Wait for UserDecisionResponse on researcher's channel
  - [ ] Reorder progression queue based on user's choice
  _US-2 (fork decisions)_

## 7. Pydantic AI Agent

- [ ] Implement `agent.py` — the LLM-powered brain
  - [ ] Create Pydantic AI agent with system prompt from `prompts/system_prompt.md`
  - [ ] Register MCP tools (Web Search, Web Crawler via MCP Gateway)
  - [ ] Implement extraction tool calls (LLM structures raw content into data models)
  - [ ] Implement cross-reference tool (LLM consistency check)
  _US-3 (depth-first extraction), US-4 (cross-referencing)_

## 8. Structured Logging

- [ ] Implement structured JSON logging across all modules
  - [ ] Base fields: agent_id, domain, timestamp, level, event
  - [ ] All 18 event types from design spec
  - [ ] Hierarchical event support (parent + sub-events)
  _US-9 (observability)_

## 9. System Prompt

- [ ] Write `prompts/system_prompt.md`
  - [ ] Persona: autonomous lore researcher
  - [ ] Task: research MMORPG zones depth-first, structure into data model
  - [ ] Instructions: search strategy, source preference, cross-referencing, conflict handling
  - [ ] Constraints: stay within budget, respect rate limits, never fabricate lore
  - [ ] Output: structured data matching Pydantic models
  _US-3, US-4, US-5 (research quality)_

## 10. Testing

- [ ] Unit tests
  - [ ] models.py — serialization/deserialization
  - [ ] config.py — env var loading with defaults
  - [ ] checkpoint.py — save/load logic
  - [ ] pipeline.py — individual step logic (mocked MCP calls)
  _All user stories_

- [ ] Integration tests
  - [ ] Agent + Web Search MCP (real search, verify results)
  - [ ] Agent + Web Crawler MCP (real crawl, verify extraction)
  - [ ] Agent + Storage MCP (checkpoint save/load)
  - [ ] Agent + RabbitMQ (publish/consume messages)
  _US-4, US-6, US-7_

- [ ] Docker test
  - [ ] Add agent to docker-compose.yml
  - [ ] Start all services, verify agent starts and connects
  - [ ] Verify first research cycle executes (at least steps 1-2)
  - [ ] Verify checkpoint persists across container restart
  _US-1 (Docker-first)_
