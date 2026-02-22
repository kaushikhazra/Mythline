# World Lore Researcher — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | SurrealDB PoC before any feature work | Validate the storage backend before designing around it |
| D2 | Zone progression tree is discovered, not static | Agentic — researcher discovers connected zones from lore research |
| D3 | Package format mirrors storage schema | What we persist is what we send to the validator |
| D4 | User is a node in the system via a shared `user` channel | Natural pattern — any agent can ask the user, UI shows one inbox |
| D5 | Structured 10-step research pipeline with autonomy within each step | Structure guides, autonomy executes |
| D6 | One shared `user` RabbitMQ channel for all agents | Agent ID in message metadata. Simpler UI — one human inbox |
| D7 | Checkpoint research progress after each step | Resume from last checkpoint on crash. Saves tokens. |
| D8 | Storage MCP handles embedding, not the researcher | Separation of concerns — researcher doesn't know about vector internals |
| D9 | Discovered connected zones are internal queue metadata, not validated lore | Validator judges lore accuracy, not research routing decisions |

---

## Daemon Lifecycle

```
Startup:
  1. Load config (env vars + YAML files)
  2. Connect to RabbitMQ (subscribe to own channel, publish to validator + user channels)
  3. Connect to MCP services (Web Search, Web Crawler) via MCP Gateway
  4. Load checkpoint state from Storage MCP (research_state collection)
  5. If checkpoint exists → resume from last step
  6. If no checkpoint → start from STARTING_ZONE env var

Main Loop:
  1. Pick next zone from progression queue (priority-ordered)
  2. Execute 10-step research pipeline (see below)
  3. On completion → configurable delay (RESEARCH_CYCLE_DELAY_MINUTES)
  4. Check daily token budget → if exhausted, sleep until next day
  5. Repeat

Shutdown:
  - Save current checkpoint
  - Close RabbitMQ connection
  - Close MCP connections
  - Exit gracefully
```

---

## Research Pipeline (10 Steps)

Each step is checkpointed. On crash/restart, the daemon resumes from the last completed step.

```
Step 1 — Zone Overview Search
  Query Web Search MCP: "{zone_name} {game_name} lore zone overview"
  Collect top N result URLs (filtered by source priority tiers)

Step 2 — Zone Overview Crawl & Extract
  Crawl top results via Web Crawler MCP
  LLM extracts structured zone data: name, level range, narrative arc,
  political climate, access gating, phase states

Step 3 — NPC Search
  Query Web Search MCP: "{zone_name} NPCs notable characters"
  Collect result URLs

Step 4 — NPC Crawl & Extract
  Crawl results via Web Crawler MCP
  LLM extracts structured NPC data: faction allegiance(s), personality,
  motivations, relationships, quest threads, phased state

Step 5 — Faction Search & Extract
  Query Web Search MCP: "{zone_name} factions organizations"
  Crawl + LLM extract: hierarchy, inter-faction relationships,
  mutual exclusions, ideology/goals

Step 6 — Lore & Cosmology Search & Extract
  Query Web Search MCP: "{zone_name} lore history mythology cosmology"
  Crawl + LLM extract: power sources, world history, mythology,
  cosmic rules and tensions relevant to this zone

Step 7 — Narrative Items Search & Extract
  Query Web Search MCP: "{zone_name} legendary items artifacts"
  Crawl + LLM extract: story arc, wielder lineage, power/significance

Step 8 — Cross-Reference & Conflict Detection
  LLM reviews ALL extracted data from steps 2-7
  Checks consistency across sources
  Flags conflicts with details (source A says X, source B says Y)
  Assigns confidence level per data point

Step 9 — Discover Connected Zones
  Extract connected zones from research content
  ("zones adjacent to {zone_name}", "where does progression go next")
  Add discovered zones to internal progression queue
  At forks (multiple next zones) → post user_decision_required to user channel
  NOT part of the lore package — internal routing metadata only

Step 10 — Package & Send to Validator
  Bundle all extracted data into storage-schema-aligned package
  Include: structured data, source URLs, confidence levels, conflicts
  Send to validator's RabbitMQ channel
  Wait for validation response on own channel
```

### Budget Checks

Before each LLM call (steps 2, 4, 5, 6, 7, 8):
- Pre-flight token estimation via `tokencost`
- If call would exceed `PER_CYCLE_TOKEN_BUDGET` → stop pipeline, checkpoint, move to next cycle
- If call would exceed `DAILY_TOKEN_BUDGET` → pause daemon until next day

### Rate Limiting

Applied at the transport layer, not per-step:
- Web Search MCP calls: `aiolimiter` token bucket at `RATE_LIMIT_REQUESTS_PER_MINUTE`
- Web Crawler MCP calls: same rate limiter (shared bucket)
- LLM calls: separate rate limiter for OpenRouter API limits
- All calls wrapped with `tenacity` retry (exponential backoff + jitter) for transient failures

---

## Checkpoint State

Persisted in Storage MCP under a `research_state` collection.

```
ResearchCheckpoint:
  zone_name: str                    # Current zone being researched
  current_step: int                 # Last completed step (1-10)
  step_data: dict                   # Accumulated data from completed steps
  progression_queue: list[str]      # Ordered list of zones to research next
  priority_queue: list[str]         # User-prioritized zones (from fork decisions)
  completed_zones: list[str]        # Zones fully researched and validated
  failed_zones: list[FailedZone]    # Zones that failed validation after max iterations
  daily_tokens_used: int            # Token counter for current day
  last_reset_date: str              # Date of last daily budget reset
```

---

## RabbitMQ Topology

### Exchanges

One topic exchange for the Knowledge Acquisition system:

```
Exchange: knowledge.topic (type: topic, durable: true)
```

### Queues & Routing Keys

| Queue | Routing Key | Consumer | Purpose |
|-------|-------------|----------|---------|
| `agent.world_lore_researcher` | `agent.world_lore_researcher` | World Lore Researcher | Receives validation feedback |
| `agent.world_lore_validator` | `agent.world_lore_validator` | World Lore Validator | Receives research packages |
| `user.decisions` | `user.decisions` | UI Backend (WebSocket) | User decision requests from any agent |

### Message Schema

All messages are Pydantic models serialized to JSON.

```python
class MessageEnvelope(BaseModel):
    message_id: str                  # UUID
    source_agent: str                # e.g., "world_lore_researcher"
    target_agent: str                # e.g., "world_lore_validator"
    message_type: str                # e.g., "research_package", "validation_result", "user_decision_required"
    timestamp: datetime
    correlation_id: str              # Links related messages (e.g., research + validation response)
    payload: dict                    # Message-type-specific data
```

#### Message Types

**research_package** (researcher → validator):
```python
class ResearchPackage(BaseModel):
    zone_name: str
    zone_data: ZoneData              # Mirrors storage schema
    npcs: list[NPCData]
    factions: list[FactionData]
    lore: list[LoreData]
    narrative_items: list[NarrativeItemData]
    sources: list[SourceReference]   # URL, domain, tier, accessed_at
    confidence: dict[str, float]     # Data point → confidence 0-1
    conflicts: list[Conflict]        # Source A vs Source B details
```

**validation_result** (validator → researcher):
```python
class ValidationResult(BaseModel):
    zone_name: str
    accepted: bool
    feedback: list[ValidationFeedback]  # What's wrong, what's missing
    iteration: int                       # Which attempt this is
```

**user_decision_required** (any agent → user channel):
```python
class UserDecisionRequired(BaseModel):
    question: str                    # "Which zone should we research next?"
    options: list[str]               # ["Westfall", "Loch Modan", "Darkshore"]
    context: str                     # Why we're asking
    decision_id: str                 # UUID for tracking the response
```

**user_decision_response** (UI → agent channel):
```python
class UserDecisionResponse(BaseModel):
    decision_id: str                 # Matches the request
    choice: str                      # User's selection
```

---

## Storage Schema (World Lore Domain)

These are the SurrealDB tables for the World Lore domain within the Storage MCP. The research package mirrors this structure.

### Tables

**zone**
```
id: string (zone name slug)
name: string
game: string (e.g., "wow")
level_range: { min: int, max: int }
narrative_arc: string
political_climate: string
access_gating: list[string]           # Prerequisites to enter
phase_states: list[PhaseState]        # Variants per character progress
connected_zones: list[string]         # Zone IDs this connects to
era: string                           # Expansion/era versioning
sources: list[SourceReference]
confidence: float
updated_at: datetime
```

**npc**
```
id: string (npc name slug)
name: string
zone_id: string -> zone
faction_ids: list[string] -> faction
personality: string
motivations: list[string]
relationships: list[NPCRelationship]  # { npc_id, type, description }
quest_threads: list[string]
phased_state: string
role: string                          # vendor, quest_giver, boss, etc.
sources: list[SourceReference]
confidence: float
updated_at: datetime
```

**faction**
```
id: string (faction name slug)
name: string
parent_faction_id: string -> faction  # Hierarchy
level: string                         # guild, order, major_faction
inter_faction: list[FactionRelation]  # { faction_id, stance: allied/hostile/neutral }
exclusive_with: list[string]          # Mutual exclusions
ideology: string
goals: list[string]
sources: list[SourceReference]
confidence: float
updated_at: datetime
```

**lore**
```
id: string (auto-generated)
zone_id: string -> zone               # Optional — some lore is zone-independent
title: string
category: string                      # history, mythology, cosmology, power_source
content: string                       # Structured lore text
era: string
sources: list[SourceReference]
confidence: float
updated_at: datetime
```

**narrative_item**
```
id: string (item name slug)
name: string
zone_id: string -> zone               # Where it's found/associated
story_arc: string
wielder_lineage: list[string]
power_description: string
significance: string                  # legendary, epic, quest, etc.
sources: list[SourceReference]
confidence: float
updated_at: datetime
```

### Graph Relationships (SurrealDB RELATE)

```
zone -> CONNECTS_TO -> zone           # Zone adjacency / progression
npc -> BELONGS_TO -> faction          # NPC faction membership
npc -> LOCATED_IN -> zone             # NPC zone presence
npc -> RELATES_TO -> npc              # NPC relationships (ally, rival, mentor, etc.)
faction -> CHILD_OF -> faction        # Faction hierarchy
faction -> STANCE_TOWARD -> faction   # Allied/hostile/neutral
narrative_item -> FOUND_IN -> zone    # Item location
lore -> ABOUT -> zone                 # Lore zone association
```

---

## MCP Interactions

```
World Lore Researcher
  ├── Web Search MCP      (tool: search)        → search queries
  ├── Web Crawler MCP     (tool: crawl_url)     → extract page content
  └── Storage MCP         (tool: checkpoint_*)   → save/load research state

World Lore Validator (downstream)
  └── Storage MCP         (tool: world_lore_*)   → persist validated data + embeddings
```

The researcher does NOT write lore data to Storage MCP directly. It only uses Storage MCP for checkpoint state. The validator writes validated data.

---

## Docker Configuration

```dockerfile
# a_world_lore_researcher/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY . .

CMD ["python", "-m", "src.agent"]
```

```yaml
# docker-compose.yml (relevant section)
a_world_lore_researcher:
  build: ./a_world_lore_researcher
  env_file: ./a_world_lore_researcher/.env
  environment:
    - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    - MCP_GATEWAY_URL=http://gateway:8811/mcp
  depends_on:
    rabbitmq:
      condition: service_healthy
    mcp_storage:
      condition: service_healthy
    mcp_web_search:
      condition: service_healthy
    mcp_web_crawler:
      condition: service_healthy
  restart: unless-stopped
```

### Agent Folder Structure

```
a_world_lore_researcher/
├── Dockerfile
├── .env
├── pyproject.toml
├── uv.lock
├── config/
│   ├── sources.yml             # Tiered source priority list
│   └── (no progression.yml — discovered dynamically)
├── prompts/
│   └── system_prompt.md        # Agent persona and instructions
└── src/
    ├── __init__.py
    ├── agent.py                # Pydantic AI agent with tools
    ├── daemon.py               # Main loop, scheduling, lifecycle
    ├── pipeline.py             # 10-step research pipeline
    ├── checkpoint.py           # Checkpoint save/load via Storage MCP
    ├── models.py               # Pydantic models (messages, data schemas)
    └── config.py               # Env var loading with defaults
```

---

## Error Handling

| Scenario | Strategy |
|----------|----------|
| Web Search returns no results | Log warning, skip to next search query, don't fail the pipeline |
| Web Crawler fails on a URL | Retry with backoff (tenacity), skip URL after max retries |
| LLM call fails | Retry with backoff, checkpoint if budget exhausted |
| RabbitMQ connection lost | Reconnect with backoff, resume from checkpoint |
| Validator rejects package | Adjust search strategy per feedback, retry up to MAX_RESEARCH_VALIDATE_ITERATIONS |
| Validator rejects at iteration cap | Discard zone data, log failure, add to failed_zones, move on |
| Token budget exhausted (per-cycle) | Checkpoint, move to next cycle after delay |
| Token budget exhausted (daily) | Checkpoint, sleep until next day |
| User decision timeout | Wait indefinitely — the researcher pauses at forks until user responds |
| Daemon crash | Restart container (Docker restart policy), resume from checkpoint |

---

## Structured Logging Events

All events emitted as structured JSON with base fields: `agent_id`, `domain` (world_lore), `timestamp`, `level`, `event`.

| Event | Level | Additional Fields |
|-------|-------|-------------------|
| `daemon_started` | info | config summary |
| `checkpoint_loaded` | info | zone, step, queue_size |
| `research_cycle_started` | info | zone_name |
| `pipeline_step_started` | info | zone_name, step_number, step_name |
| `pipeline_step_completed` | info | zone_name, step_number, duration_ms, tokens_used |
| `search_executed` | debug | query, result_count |
| `crawl_executed` | debug | url, content_length |
| `conflict_detected` | warn | zone_name, data_point, source_a, source_b |
| `package_sent` | info | zone_name, data_point_count, total_sources |
| `validation_received` | info | zone_name, accepted, iteration |
| `validation_rejected` | warn | zone_name, feedback_summary, iteration |
| `fork_detected` | info | zone_name, options |
| `user_decision_requested` | info | decision_id, options |
| `user_decision_received` | info | decision_id, choice |
| `budget_warning` | warn | budget_type, used, remaining |
| `budget_exhausted` | warn | budget_type, action (pause/sleep) |
| `error` | error | error_type, message, retry_count |
| `daemon_shutdown` | info | reason |
