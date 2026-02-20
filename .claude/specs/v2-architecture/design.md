# Mythline v2 Architecture — Design

## Status: Discovery (Memory complete, MCP complete, Orchestration complete, Drama Production complete)

---

## Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| D1 | Keep Pydantic AI | Preferred over other frameworks, good DX | 2026-02-20 |
| D2 | MCP as data microservice layer | MCP stores and serves, agents think. Clean separation. | 2026-02-20 |
| D3 | No orchestrator, no graphs | Fully agentic. Knowledge agents are autonomous daemons. Drama agents collaborate via message queue. | 2026-02-21 |
| D4 | Overhaul memory into 5 knowledge domains | Current JSON dump is insufficient. Five distinct domains with different storage needs. | 2026-02-20 |
| D5 | Generic MMORPG model, not WoW-specific | Future-proofing, extensible to any MMORPG | 2026-02-20 |
| D6 | Five knowledge domains | World Lore, Quest Lore, Character, Dynamics, Narrative History | 2026-02-20 |
| D7 | Story formula with feedback loop | Next Story = Lore + Quest + Character + Dynamics + Narrative History | 2026-02-20 |
| D8 | Narrative History stores interactions, not prose | Scene-level granularity, queryable, not context-window-heavy | 2026-02-20 |
| D9 | Character capabilities are first-class | Skills, talents, professions define narrative possibilities and identity | 2026-02-20 |
| D10 | Knowledge Acquisition = Research Agent → Validator Agent → MCP Store | Each domain has 3 components: researcher, validator, storage service | 2026-02-21 |
| D11 | Drama Production = agent swarm with message queue | Agents collaborate via channels, no pipeline, no boss | 2026-02-21 |
| D12 | Quality-gated convergence | Quality Assessor scores 0-1, >= 0.8 passes, iteration cap as safety net | 2026-02-21 |
| D13 | Continuity is a cross-cutting service, not a phase | Any agent can query continuity at any time during creation | 2026-02-21 |
| D14 | Graphs eliminated entirely | Well-structured prompts + agentic autonomy replace rigid workflows | 2026-02-21 |
| D15 | Each agent = separate Docker container | Small, scalable, independently deployable microservices | 2026-02-21 |
| D16 | Shared agent harness, differing only in prompt + config | One codebase, factory pattern. Same as v1 approach but containerized. | 2026-02-21 |
| D17 | All MCP services deployed in Docker with MCP registry | Docker's MCP catalog for service discovery and management | 2026-02-21 |
| D18 | RabbitMQ for message queue (replaces custom MCP queue) | Enterprise-grade, scalable, dead letter queues, proven at scale | 2026-02-21 |
| D19 | Adopt Pydantic AI v1.62 (the real framework) | v1 was custom-built. v2 uses the actual framework with native MCP support. | 2026-02-21 |
| D20 | SurrealDB for Storage MCP (Qdrant fallback) | Vector + graph + SQL in one engine. PoC required to validate. | 2026-02-21 |

---

## System Architecture Overview

### Core Principles
- **MCP = data layer (stores and serves). Agents = intelligence layer (thinks and creates).**
- **Every component is a Docker container.** Agents, MCPs, RabbitMQ — all containerized.
- **One agent harness, many configurations.** Agents differ only in system prompt and model config.
- **RabbitMQ is the universal communication backbone.** All agent-to-agent communication flows through RabbitMQ channels.

### The Two Systems

The system is divided into two fundamentally different systems that share a common data layer (MCP):

```
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE ACQUISITION                       │
│                   (5 autonomous pipelines)                       │
│                                                                 │
│  Research Agent → Validator Agent → MCP Store   (per domain)    │
│                                                                 │
│  - Runs continuously, autonomously                              │
│  - Self-validating (open web data needs verification)           │
│  - Configurable delay/backoff for rate limiting                 │
│  - No orchestrator, no coordination between pipelines           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    5 MCP Data Stores
                    (shared data layer)
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                      DRAMA PRODUCTION                           │
│                  (agent swarm + message queue)                   │
│                                                                 │
│  Trigger: User → "quests [A,B,C,D,E] + character X"            │
│                                                                 │
│  Agents collaborate via message channels                        │
│  Quality Assessor gates output (score >= 0.8 to pass)           │
│  Iteration cap prevents infinite loops                          │
│  Done when: all scenes across all quests finalized              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Acquisition — Detailed Design

### Pattern (same for all 5 domains)

```
Research Agent → Validator Agent → MCP Store
   (finds)         (verifies)      (persists)
```

Three components per domain:
- **Research Agent** (the investigator) — autonomous daemon. Searches, crawls, gathers raw data from open web. Runs continuously with configurable delay and backoff to throttle token/rate limits.
- **Validator Agent** (the editor/auditor) — audits the researcher's package. Does NOT re-research. Checks completeness, consistency, source quality. Accepts or rejects with specific feedback.
- **MCP Store** (the library) — persists validated data. Serves it to any agent that queries. Pure data service, no intelligence.

### Research → Validate → Store Flow

```
Researcher Agent:
  1. Searches multiple sources (minimum N independent sources per claim)
  2. Cross-references across sources within its own work
  3. Packages: data + sources + confidence level + any conflicts found
  4. Passes package to Validator

Validator Agent:
  1. Audits package for completeness (all required fields present?)
  2. Audits for consistency (do sources agree? are conflicts resolved?)
  3. Audits source quality (authoritative sources? or random forums?)
  4. Does NOT do its own web research (separation of concern)
  5. Decision:
     → Valid: writes to MCP Store
     → Invalid: rejects with SPECIFIC feedback (what's wrong, what's missing)

On rejection:
  Researcher receives feedback → adjusts search strategy → retries
  Max N iterations per data point → if still invalid, discard + log, move on
  Daemon picks up fresh data on next scheduled cycle
```

Key principle: **Researcher investigates. Validator audits. Nobody does someone else's job.**

### The 5 Pipelines

| Domain | Research Agent | Validator Agent | MCP Store |
|--------|---------------|-----------------|-----------|
| World Lore | Researches game world: zones, factions, NPCs, cosmology, history. Multi-source, cross-referenced. | Audits lore accuracy, source quality, completeness | World Lore MCP |
| Quest Lore | Researches quest chains: structure, prerequisites, outcomes, NPCs. Multi-source. | Audits quest data integrity, chain completeness | Quest Lore MCP |
| Character | Captures player input: identity, backstory, nature, capabilities | Audits consistency, class/race compatibility | Character MCP |
| Dynamics | Computes NPC dispositions, faction politics, phased world state | Audits relational consistency | Dynamics MCP |
| Narrative History | Reads existing story output files, indexes interactions per scene | Audits continuity, thread consistency | Narrative History MCP |

### Autonomy Model
- Each pipeline runs independently as a daemon process
- No inter-pipeline coordination needed
- Configurable delay between research cycles
- Backoff strategy for rate limits (token + API)
- Self-healing: if research fails, retry with backoff, don't crash
- Iteration cap on research→validate loop prevents infinite cycling

---

## Drama Production — Detailed Design

### Trigger
User provides: quest list + character identity
```
"Create drama for quests [A, B, C, D, E] with character X"
```

### Agents (8 total)

Each agent has its own **message channel** (inbox). Other agents post to each other's channels to collaborate.

| Agent | Responsibility | Reads from MCP | Posts to channels |
|-------|---------------|----------------|-------------------|
| **Story Architect** | Plans narrative arc from quest chain + character. Decides what scenes are needed, their purpose, emotional beats. | All 5 stores | Scene Director |
| **Scene Director** | For one scene: plans beat-by-beat breakdown, emotional progression, conflicts, who's present | All 5 stores | Character Director, Narrator, Dialogist |
| **Character Director** | Directs character behavior within game's finite gesture/emote constraints. Maps emotion to available game expressions. | Character, Dynamics | Scene Director, Narrator, Dialogist |
| **Narrator** | Writes descriptive narrative ONLY: atmosphere, setting, action descriptions | World Lore, Quest Lore, Narrative Hx | Scene Director |
| **Dialogist** | Writes character dialogue ONLY: voices, conversation, NPC speech | Character, Dynamics, Quest Lore | Scene Director, Character Director |
| **Shot Composer** | Translates completed scene into cinematic shots: camera, framing, transitions, pacing | World Lore (for visual setting) | Scene Director |
| **Quality Assessor** | Scores scene output 0-1. Independent scorer, doesn't create content. | All 5 stores | All agents (feedback) |
| **Continuity Service** | Cross-cutting service. Any agent can query: "is this consistent with what came before?" | Narrative History, Character | Responds to queries |

### Message Queue Model

```
Each agent has a channel (inbox):
┌──────────────────┐
│ Story Architect   │ ← receives: user trigger, Quality Assessor feedback
├──────────────────┤
│ Scene Director    │ ← receives: scene plan, feedback from all scene agents
├──────────────────┤
│ Character Director│ ← receives: scene breakdown, dialogist feedback
├──────────────────┤
│ Narrator          │ ← receives: scene breakdown, character direction
├──────────────────┤
│ Dialogist         │ ← receives: scene breakdown, character direction
├──────────────────┤
│ Shot Composer     │ ← receives: completed scene (narration + dialogue + direction)
├──────────────────┤
│ Quality Assessor  │ ← receives: finalized scene for scoring
├──────────────────┤
│ Continuity Service│ ← receives: queries from any agent
└──────────────────┘
```

Key properties:
- **Any agent can post to any other agent's channel** — enables push-back, iteration, feedback
- **Decoupled** — agents don't import each other, they just know channel names
- **Async** — agents work at their own pace
- **Audit trail** — message history IS the creative process record

### Collaboration Flow (per scene)

```
1. Story Architect posts scene plan → Scene Director channel
2. Scene Director posts breakdown → Character Director, Narrator, Dialogist channels
3. Character Director posts direction → Narrator, Dialogist channels
   (mapped to game's available emotes/gestures)
4. Narrator writes narration, posts → Scene Director channel
5. Dialogist writes dialogue, posts → Scene Director channel
6. Scene Director assembles scene, posts → Shot Composer channel
7. Shot Composer creates shots, posts → Quality Assessor channel
8. Quality Assessor scores:
   >= 0.8 → FINALIZE, move to next scene
   < 0.8  → posts feedback to relevant agent channels, iterate
9. Max N iterations → best scoring version wins
```

### Push-back examples
- Shot Composer → Scene Director: "Too many location changes for visual coherence"
- Dialogist → Character Director: "This NPC wouldn't use this tone given reputation"
- Narrator → Scene Director: "Setting doesn't match the emotional beat planned"
- Quality Assessor → any agent: "Lore inconsistency in paragraph X"

### Convergence Model
- **Quality score**: 0-1 scale, scored by dedicated Quality Assessor
- **Threshold**: >= 0.8 passes
- **Iteration cap**: Max N iterations per scene (prevents infinite ping-pong)
- **Best version wins**: If cap is hit, highest-scoring version is used
- **Drama complete**: When all scenes across all quests are finalized

---

## Knowledge Architecture — Data Model

### Story Formula
```
Next Story = World Lore + Quest Lore + Character + Dynamics + Narrative History
                                                                    ↑
                                                    (each story feeds back in)
```

### Five Knowledge Domains

**World Lore** — The canonical game world. Zones, factions, NPCs, cosmology, history. Shared across all characters. Era-versioned (same zone can exist in multiple time periods). Relatively static but expandable.

**Quest Lore** — Specific quest chains and their narrative structure. Prerequisites, branching, outcomes. Gated by faction/class/progression.

**Character** — Full character model: identity (race, archetype, specialization, power source, origin), capability (active abilities, passive traits, mastery level, talent choices made AND rejected, professions, power dynamic with cost/limits/vulnerabilities), evolving nature (personality, moral alignment, motivations), reputation graph (per faction hierarchy-aware, per NPC personal, exclusivity effects), journal (quests, events witnessed, relationships, milestones), growth arc (era-specific identity, pivotal moments), relationships (party, mentors, rivals, bonds, shared experiences).

**Dynamics** — Computed, not stored directly. NPC dispositions, faction politics toward this character, phased world state. Assembled from character reputation + world state + interaction history.

**Narrative History** — Scene-level index of previous story interactions. NOT the prose itself. Tracks: world/quest/NPC interactions per scene, character effects (growth, reputation shifts, emotional state), narrative threads (opened/closed/dangling), continuity bridges between stories.

### MMORPG-Generic Data Model

#### WORLD LAYER (persistent, shared, era-versioned)
- **Region / Zone** — narrative arc, political climate, access gating, state variants (phased per character progress)
- **NPC** — faction allegiance(s), personality, motivations, relationships to other NPCs, offered quest threads, phased state
- **Faction** — hierarchical (guild < order < major faction), inter-faction relationships (allied/hostile/neutral), mutual exclusions, ideology/goals
- **Quest / Event** — prerequisites (progression/faction/class gating), narrative thread, outcomes (world state mutations, reputation shifts)
- **Lore / Cosmology** — power sources, world history/mythology, cosmic rules and tensions
- **Narrative Items** — own story arc, wielder lineage, power/significance

#### CHARACTER LAYER (persistent, individual, era-layered)
- **Identity** — race/species, archetype (class/role), specialization, power source, origin/backstory
- **Capability** — active abilities, passive traits, mastery level, talent choices (made + rejected), professions/tradecraft, power dynamic (cost, limits, vulnerabilities)
- **Nature** (evolving) — personality traits, moral alignment, motivations
- **Reputation Graph** — per faction (hierarchy-aware), per NPC (personal), exclusivity effects
- **Journal** — quest completions + choices, events witnessed/participated, relationships, capability milestones
- **Growth Arc** — era-specific identity (title, role, allegiance per era), pivotal moments, trajectory
- **Relationships** — party members/companions, mentors/rivals/bonds, shared experiences

#### NARRATIVE HISTORY LAYER (per-character, cumulative)
- Indexed interactions per scene (not full prose)
- Effects: reputation shifts, character growth, emotional state changes
- Threads: opened/closed, foreshadowing, promises, unresolved tension
- Continuity: scene-level context for bridging between stories

#### SCENE LAYER (ephemeral, assembled per moment)
- World state for THIS character at THIS time (phased)
- Party composition + their capabilities
- NPC dispositions (computed from reputation + history + faction politics)
- Active narrative threads
- Available actions (constrained by character capabilities)
- Dramatic tension (computed from all layers)

---

## Full System Inventory

### Agents (18 total)

| # | Agent | System | Type | Role |
|---|-------|--------|------|------|
| 1 | World Lore Researcher | Knowledge Acquisition | Autonomous daemon | Researches game world from web sources |
| 2 | World Lore Validator | Knowledge Acquisition | Autonomous daemon | Validates world lore accuracy |
| 3 | Quest Lore Researcher | Knowledge Acquisition | Autonomous daemon | Researches quest chains and structure |
| 4 | Quest Lore Validator | Knowledge Acquisition | Autonomous daemon | Validates quest data integrity |
| 5 | Character Researcher | Knowledge Acquisition | Autonomous daemon | Captures and researches character data |
| 6 | Character Validator | Knowledge Acquisition | Autonomous daemon | Validates character consistency |
| 7 | Dynamics Researcher | Knowledge Acquisition | Autonomous daemon | Computes NPC/faction/world state |
| 8 | Dynamics Validator | Knowledge Acquisition | Autonomous daemon | Validates relational consistency |
| 9 | Narrative History Researcher | Knowledge Acquisition | Autonomous daemon | Reads story output, indexes interactions |
| 10 | Narrative History Validator | Knowledge Acquisition | Autonomous daemon | Validates continuity and threads |
| 11 | Story Architect | Drama Production | Swarm agent | Plans narrative arc and scene structure |
| 12 | Scene Director | Drama Production | Swarm agent | Plans per-scene beats and breakdown |
| 13 | Character Director | Drama Production | Swarm agent | Directs behavior within game gesture constraints |
| 14 | Narrator | Drama Production | Swarm agent | Writes descriptive narrative |
| 15 | Dialogist | Drama Production | Swarm agent | Writes character dialogue |
| 16 | Shot Composer | Drama Production | Swarm agent | Creates cinematic shot list |
| 17 | Quality Assessor | Drama Production | Swarm agent | Scores output 0-1, provides feedback |
| 18 | Continuity Service | Drama Production | Cross-cutting service | Answers consistency queries from any agent |

### MCP Services (5 total — Message Queue replaced by RabbitMQ)

| # | MCP Service | Purpose | Docker Image | Used by |
|---|-------------|---------|-------------|---------|
| 1 | **Storage MCP** | Single service with 5 domain collections | Custom (FastMCP + SurrealDB) | All agents |
| 2 | **Web Search MCP** | Search the open web | Custom (FastMCP + DuckDuckGo) | Research agents |
| 3 | **Web Crawler MCP** | Extract content from URLs | Custom (FastMCP + crawler) | Research agents |
| 4 | **Filesystem MCP** | Read/write files | Custom (FastMCP) | Narrative Hx researcher, Drama output |
| 5 | **Embedding MCP** | Vector embedding generation | Custom (FastMCP + OpenAI) | Storage MCP, Research agents |

### Infrastructure Services (Docker)

| # | Service | Purpose | Docker Image |
|---|---------|---------|-------------|
| 1 | **RabbitMQ** | Universal message queue for all agent communication | `rabbitmq:management` (official) |
| 2 | **SurrealDB** | Backend for Storage MCP (vector + graph + SQL) | `surrealdb/surrealdb` (official) |

### MCP Design Principles
- **MCP = infrastructure, not intelligence.** MCP services store, serve, transport, embed. They don't reason.
- **One Storage MCP, 5 collections.** Domain-scoped collections within a single service.
- **Search ≠ Crawl.** Search discovers URLs. Crawl extracts content. Different MCPs.
- **Embedding as service.** No agent carries its own embedding logic.
- **All MCPs containerized.** Deployed via Docker, discoverable via Docker MCP registry.
- **RabbitMQ replaces Message Queue MCP.** Enterprise-grade broker with persistence, dead letter queues, and scaling. All agent-to-agent communication (both Knowledge and Drama) flows through RabbitMQ.

---

## Deployment Architecture

### Container Topology

```
Docker Compose
│
├── Infrastructure
│   ├── rabbitmq          (official image, management UI on :15672)
│   └── surrealdb         (official image, backend for Storage MCP)
│
├── MCP Services (5 containers)
│   ├── mcp-storage       (FastMCP + SurrealDB client)
│   ├── mcp-web-search    (FastMCP + DuckDuckGo)
│   ├── mcp-web-crawler   (FastMCP + crawler)
│   ├── mcp-filesystem    (FastMCP + volume mounts)
│   └── mcp-embedding     (FastMCP + OpenAI/OpenRouter)
│
├── Knowledge Agents (10 containers, same base image)
│   ├── agent-world-lore-researcher
│   ├── agent-world-lore-validator
│   ├── agent-quest-lore-researcher
│   ├── agent-quest-lore-validator
│   ├── agent-character-researcher
│   ├── agent-character-validator
│   ├── agent-dynamics-researcher
│   ├── agent-dynamics-validator
│   ├── agent-narrative-hx-researcher
│   └── agent-narrative-hx-validator
│
├── Drama Agents (8 containers, same base image)
│   ├── agent-story-architect
│   ├── agent-scene-director
│   ├── agent-character-director
│   ├── agent-narrator
│   ├── agent-dialogist
│   ├── agent-shot-composer
│   ├── agent-quality-assessor
│   └── agent-continuity-service
│
└── UI (2 containers)
    ├── ui-backend         (FastAPI + WebSocket bridge)
    └── ui-frontend        (React + Vite, custom CSS)
```

**Total: ~27 containers** (2 infra + 5 MCP + 18 agents + 2 UI)

### UI Architecture — Discord-Style Agent Dashboard

**Design Language:**
- Dark theme, Discord aesthetic
- Custom CSS (no Tailwind)
- Lineart icons + emojis for agent identity and message types
- Real-time updates via WebSocket

**Layout:**
```
┌──────────┬────────────────────────────────┬──────────────┐
│ Channels │       Message Feed             │   Context    │
│          │                                │              │
│ KNOWLEDGE│ [narrator] Scene 3 narration   │ Character    │
│  #world  │ complete. Atmosphere: foggy... │ ─────────    │
│  #quest  │                                │ Name: ...    │
│  #char   │ [quality] Score: 0.72 — lore   │ Class: ...   │
│  #dynamics│ inconsistency in NPC dialogue │ Spec: ...    │
│  #history│                                │              │
│          │ [dialogist] Revised dialogue   │ Scene Info   │
│ DRAMA    │ for NPC Theron, addressing...  │ ─────────    │
│  #architect│                              │ Quest: ...   │
│  #director│ [quality] Score: 0.84 — pass  │ Zone: ...    │
│  #narrator│                               │ NPCs: ...    │
│  #dialog │                                │              │
│  #char-dir│                               │ Knowledge    │
│  #shots  │                                │ ─────────    │
│  #quality│                                │ [browse]     │
│          │                                │              │
│ SYSTEM   │                                │ Token Usage  │
│  #health │                                │ ─────────    │
│  #tokens │                                │ $12.34 today │
└──────────┴────────────────────────────────┴──────────────┘
```

**Left Sidebar — Channels:**
- Knowledge agent channels (5 domains, status indicators)
- Drama production channels (per agent, activity indicators)
- System channels (health, token usage)
- Channel = RabbitMQ queue subscription

**Main Panel — Message Feed:**
- Real-time agent messages from selected channel(s)
- Formatted output: narration blocks, dialogue blocks, scene plans, quality scores
- Agent identity via lineart icon + emoji + name
- Feedback/iteration messages visually distinct (indented, different color)

**Right Panel — Context:**
- Character profile (identity, capabilities, nature)
- Current scene info (quest, zone, NPCs present)
- Knowledge store browser (search/browse any domain)
- Token usage / cost dashboard

**Tech Stack:**
- `ui-backend`: FastAPI + WebSocket. Subscribes to RabbitMQ queues, pushes to frontend via WS. Also serves REST API for knowledge browsing, drama triggers, agent config.
- `ui-frontend`: React + Vite. Custom CSS (dark theme). WebSocket client for real-time. No Tailwind.

**UI Features:**
- Trigger drama creation (quest list + character input)
- Watch agent collaboration in real-time
- Browse/search knowledge stores
- View character profiles
- Monitor agent health and status
- Track token usage and costs
- Review quality scores and iteration history
- View final drama output (formatted scenes + shots)

### Agent Container Pattern

All 18 agent containers use the **same Docker image** with different configuration:

```
mythline-agent (base image)
├── Pydantic AI harness code (shared)
├── RabbitMQ client (shared)
├── MCP client toolsets (shared)
├── Config injection:
│   ├── AGENT_TYPE (researcher | validator | drama)
│   ├── AGENT_ROLE (world-lore-researcher, narrator, etc.)
│   ├── SYSTEM_PROMPT (mounted or env-injected)
│   ├── MODEL_CONFIG (which LLM, temperature, etc.)
│   ├── MCP_TOOLSETS (which MCP services this agent uses)
│   ├── RABBITMQ_CHANNELS (which channels to subscribe/publish)
│   └── SCHEDULE_CONFIG (cycle delay/backoff — knowledge agents only)
└── Agent behavior is entirely determined by config + prompt
```

### Communication Flow

```
All agent communication flows through RabbitMQ:

Knowledge Acquisition:
  Researcher → [RabbitMQ] → Validator → [MCP Store]
  Validator → [RabbitMQ] → Researcher (feedback on rejection)

Drama Production:
  Story Architect → [RabbitMQ] → Scene Director
  Scene Director → [RabbitMQ] → Narrator, Dialogist, Character Director
  Quality Assessor → [RabbitMQ] → any agent (feedback)
  Any agent → [RabbitMQ] → any agent (push-back)

MCP Access (via Docker MCP Gateway):
  Agents → [MCP Gateway :8811] → routes to correct MCP container
  Single endpoint, gateway handles routing, security, lifecycle
  Pydantic AI connects via MCPServerStreamableHTTP('http://gateway:8811/mcp')

UI Real-time:
  RabbitMQ → [ui-backend WebSocket] → ui-frontend
  (all agent messages visible in Discord-style channel feed)
```

### Docker MCP Gateway

All MCP access is routed through **Docker MCP Gateway** — a single endpoint that routes tool calls to the correct MCP container:
- Agents connect to ONE URL: `http://gateway:8811/mcp`
- Gateway routes to the right MCP container automatically
- Handles security (no-new-privileges, CPU/memory limits on MCP containers)
- Supports live config reload
- Pydantic AI connects via `MCPServerStreamableHTTP`

---

## Technology Stack

### Core Framework
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Agent Framework | Pydantic AI | v1.62+ | Agent harness, MCP client, tool management |
| Data Store | SurrealDB | latest | Vector + graph + SQL (PoC required, Qdrant fallback) |
| Message Broker | RabbitMQ | latest | Universal agent-to-agent communication |
| Containerization | Docker + Docker Compose | latest | Deployment, scaling, MCP registry |

### Agent Libraries (inside agent containers)
| Library | Purpose |
|---------|---------|
| pydantic-ai | Agent framework with native MCP support |
| aio-pika | Async RabbitMQ client for Python |
| tenacity | Retry with exponential backoff + jitter |
| aiolimiter | Token bucket rate limiting |
| tokenator | LLM token usage tracking (SQLite per agent) |
| tokencost | Pre-flight cost estimation |
| apscheduler | Cycle timing for knowledge agents |

### MCP Libraries (inside MCP containers)
| Library | Purpose |
|---------|---------|
| fastmcp | MCP server framework (StreamableHTTP) |
| surrealdb | SurrealDB Python client (for Storage MCP) |
| httpx / aiohttp | Web requests (for Search + Crawler MCPs) |

---

## Open Design Questions (for later phases)

### Storage MCP + SurrealDB
- SurrealDB PoC: model one zone with NPCs/factions, test vector + graph + CRUD on Windows
- Collection schemas per domain
- How Dynamics collection computes state efficiently
- Narrative History indexing strategy
- Fallback plan: Qdrant + NetworkX if SurrealDB PoC fails

### RabbitMQ
- Exchange topology (direct, topic, fanout?)
- Queue naming conventions per agent
- Message schema (Pydantic models for message payloads)
- Dead letter queue strategy for failed messages
- Message TTL and retention for audit trail

### Docker + MCP Registry
- How Docker MCP registry integrates with Pydantic AI (research pending)
- Dockerfile for shared agent base image
- Docker Compose configuration
- Volume strategy for persistent data (SurrealDB, file output)
- Environment variable injection for agent config
- Health check patterns for all containers

### Agent Implementation
- Prompt structure for autonomous knowledge agents
- Prompt structure for drama collaboration agents
- Agent factory pattern: config → agent instance
- Configuration format (YAML? JSON? env vars?)
- How game gesture/emote constraints are provided to Character Director

### Convergence
- Exact quality scoring rubric (what dimensions? what weights?)
- Iteration cap value (3? 5? 10?)
- How "best version" is selected when cap is hit
- Feedback message format from Quality Assessor to agents
