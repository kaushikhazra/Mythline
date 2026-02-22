# CLAUDE.md — Mythline v2

This document is the development guide for Mythline. It captures principles, conventions, and an index to detailed design documents. It is written for Kaushik and Velasari (Claude) — the two builders of this system.

---

## Project Overview

Mythline is a multi-agent AI storytelling system that creates MMORPG narratives. The system researches game lore, builds character profiles, and produces cinematic drama — all through autonomous, collaborating AI agents. World of Warcraft is the first target, but the architecture is MMORPG-generic by design.

---

## Development Philosophy

### Root Cause over Patch

We do not solve problems by patching symptoms. When something breaks or behaves unexpectedly:

1. **Investigate the root cause** — understand why, not just what
2. **Research probable solutions** — don't grab the first fix that compiles
3. **Evaluate and pick the best** — if multiple viable options exist, discuss before implementing
4. **If either of us is confused — stop** — discuss until both understand, then implement

Perfection over speed. Shortcuts create debt. Understanding creates quality.

### SOLID, DRY, KISS

These three principles govern all code decisions:

- **SOLID** — Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **DRY** — Don't repeat yourself. But don't prematurely abstract either — three similar lines are better than a premature abstraction
- **KISS** — The simplest solution that works correctly is the best solution

### Reuse Before Build

Never assume we have to build from scratch. The software ecosystem is vast. Before building any component:

1. Search the web for existing libraries that solve the problem
2. If multiple options exist, present the list with recommendations — we discuss and pick together
3. Only build custom if no suitable library exists (and that's also an opportunity to open-source)

### Incremental Development

We build and validate incrementally. Each component must be tested as it's added — unit tests prove it works in isolation, integration tests prove it fits with existing components, and regression tests prove nothing broke.

### Docker-First

Every component must work in Docker, not just locally. The validation sequence is: prove it works locally first, then prove it works in Docker. If it doesn't run in a container, it's not done.

---

## Architecture Overview

Mythline v2 is composed of two fundamentally different systems sharing a common data layer:

```
KNOWLEDGE ACQUISITION (5 autonomous pipelines)
  Research Agent -> Validator Agent -> MCP Store   (per domain)
  Runs continuously as daemons. No coordination between pipelines.

                    5 Domain MCP Stores
                    (shared data layer)

DRAMA PRODUCTION (8-agent swarm)
  Agents collaborate via RabbitMQ message channels.
  Quality Assessor gates output (score >= 0.8 to pass).
  Done when all scenes across all quests are finalized.
```

### Core Principles

- **MCP = data layer** (stores and serves). **Agents = intelligence layer** (thinks and creates).
- **Every component is a Docker container.** Agents, MCPs, infrastructure — all containerized.
- **Each agent is independent.** Own codebase, own Dockerfile, own .env. No shared harness. This preserves the freedom to diverge — today Pydantic AI, tomorrow maybe Claude SDK for a specific agent.
- **RabbitMQ is the universal communication backbone.** All agent-to-agent communication flows through RabbitMQ channels.
- **Environment variables for configuration.** Layered overrides: Docker -> .env -> default values.

### The Five Knowledge Domains

| Domain | What it stores |
|--------|---------------|
| World Lore | Canonical game world — zones, factions, NPCs, cosmology, history. Era-versioned. |
| Quest Lore | Quest chains — structure, prerequisites, outcomes, NPC involvement. |
| Character | Player identity, capabilities, nature, reputation, journal, growth arc. |
| Dynamics | Computed NPC dispositions, faction politics, phased world state. |
| Narrative History | Scene-level index of previous interactions. NOT prose — queryable metadata. |

### Story Formula

```
Next Story = World Lore + Quest Lore + Character + Dynamics + Narrative History
                                                                  ^
                                                    (each story feeds back in)
```

### Agent Inventory (18 total)

**Knowledge Acquisition (10 agents — 2 per domain):**

| Agent | Role |
|-------|------|
| World Lore Researcher | Researches game world from web sources |
| World Lore Validator | Validates lore accuracy and source quality |
| Quest Lore Researcher | Researches quest chains and structure |
| Quest Lore Validator | Validates quest data integrity |
| Character Researcher | Captures and researches character data |
| Character Validator | Validates character consistency |
| Dynamics Researcher | Computes NPC/faction/world state |
| Dynamics Validator | Validates relational consistency |
| Narrative History Researcher | Reads story output, indexes interactions |
| Narrative History Validator | Validates continuity and threads |

**Drama Production (8 agents):**

| Agent | Role |
|-------|------|
| Story Architect | Plans narrative arc and scene structure |
| Scene Director | Plans per-scene beats and breakdown |
| Character Director | Directs behavior within game gesture constraints |
| Narrator | Writes descriptive narrative |
| Dialogist | Writes character dialogue |
| Shot Composer | Creates cinematic shot list |
| Quality Assessor | Scores output 0-1, provides feedback |
| Continuity Service | Cross-cutting — answers consistency queries from any agent |

### MCP Services (3 total)

| Service | Purpose |
|---------|---------|
| Storage MCP | Single service with 5 domain collections (SurrealDB backend). Embedding on write via shared provider. |
| Web Search MCP | Search the open web (DuckDuckGo) |
| Filesystem MCP | Read/write file operations |

### External Docker Services

| Service | Purpose |
|---------|---------|
| crawl4ai | Headless Chromium web crawler (Playwright + anti-bot). REST API at port 11235. Replaces old mcp_web_crawler. |

### Infrastructure Services

| Service | Purpose |
|---------|---------|
| RabbitMQ | Universal message queue for all agent communication |
| SurrealDB | Backend for Storage MCP (vector + graph + SQL) |

### External Service Libraries

These v1 libraries carry forward into v2:

| Library | Purpose |
|---------|---------|
| YouTube Uploader | Upload videos to YouTube with metadata |
| OBS Controller | Control OBS Studio for screen recording |
| Voice Recognition | Voice command recognition for navigation |

---

## Repository Structure

Flat prefixed layout at the root. Each agent and service is its own deployable unit.

```
mythline/
|
+-- a_world_lore_researcher/       # Agent: own Dockerfile, .env, pyproject.toml, prompts/
+-- a_world_lore_validator/
+-- a_quest_lore_researcher/
+-- a_quest_lore_validator/
+-- a_character_researcher/
+-- a_character_validator/
+-- a_dynamics_researcher/
+-- a_dynamics_validator/
+-- a_narrative_hx_researcher/
+-- a_narrative_hx_validator/
+-- a_story_architect/
+-- a_scene_director/
+-- a_character_director/
+-- a_narrator/
+-- a_dialogist/
+-- a_shot_composer/
+-- a_quality_assessor/
+-- a_continuity_service/
|
+-- mcp_storage/                    # MCP services
+-- mcp_web_search/
+-- mcp_filesystem/
|
+-- s_rabbitmq/                     # Infrastructure services
+-- s_surrealdb/
|
+-- shared/                         # Central utilities (see below)
|
+-- web/                            # UI
|   +-- backend/                    # FastAPI + WebSocket
|   +-- frontend/                   # React + Vite + TypeScript
|
+-- docker-compose.yml              # Orchestrates all containers
+-- .env                            # Root-level defaults
```

### Naming Conventions

- **Root folders**: Prefixed — `a_` (agents), `mcp_` (MCP services), `s_` (infrastructure services)
- **Python files/folders**: `snake_case` (PEP 8)
- **TypeScript components**: `PascalCase` (e.g., `MessageFeed.tsx`, `ChannelList.tsx`)
- **TypeScript utilities/hooks**: `camelCase` (e.g., `useWebSocket.ts`, `formatTimestamp.ts`)

### The `shared/` Folder

Contains central utilities that all agents and services use — things that don't diverge independently:

- Pydantic models for RabbitMQ message schemas
- Structured logging emitter and decorators
- Common type definitions
- Parsing utilities
- MCP client helpers
- File creation utilities

### Per-Agent Structure

Each agent folder is self-contained:

```
a_narrator/
+-- Dockerfile
+-- .env
+-- pyproject.toml
+-- uv.lock
+-- prompts/
|   +-- system_prompt.md
+-- src/
|   +-- agent.py
|   +-- ...
```

---

## Coding Standards

### Python — PEP 8

- Follow PEP 8 for all Python code
- Docstrings for modules, classes, and functions (PEP 257)
- Inline comments for **why**, not **what** — the code explains what, comments explain reasoning
- All imports at the top: standard library, then third-party, then local
- No inline imports
- No emojis in code

### TypeScript — Standard Conventions

- PascalCase for components and types
- camelCase for functions, variables, hooks
- Strict mode enabled
- Functional components with hooks

### Frontend Structure

```
web/frontend/src/
+-- components/        # Reusable UI pieces: Button, MessageEntry, ChannelList
+-- features/          # Feature-grouped: drama/, knowledge/, settings/
+-- hooks/             # Custom hooks: useWebSocket, useChannel
+-- layouts/           # Page shells: DashboardLayout, SidebarLayout
+-- pages/             # Route-level: DramaPage, KnowledgePage
+-- providers/         # React Context: WebSocketProvider, ThemeProvider
```

### Prompt Management

- System prompts stored in `prompts/system_prompt.md` per agent
- Markdown format
- Sections: Persona, Task, Instructions, Constraints, Output

---

## Error Handling

Production-grade error handling through elegant, reusable patterns — not scattered try/catch blocks.

**Philosophy**: Reduce error handling code by breaking concerns into decorators and reusable patterns. Centralize where it makes sense, but don't force a single strategy on everything.

**Patterns to use:**
- **Retry decorators** — exponential backoff with jitter for transient failures
- **Circuit breakers** — prevent cascading failures across services
- **Dead letter queues** — RabbitMQ DLQ for messages that fail processing
- **Iteration caps** — safety nets on loops (research-validate cycles, quality iterations)

**Detailed error handling design**: See `.claude/specs/` (to be designed in Phase 1).

---

## Logging & Observability

All agents emit **structured JSON log events** for real-time observability in the UI.

### Log Structure

Every log event includes correlation metadata for grouping and tracing:

- `agent_id` — which agent emitted the event
- `story_id` — which story production this belongs to (Drama)
- `domain` — which knowledge domain (Knowledge Acquisition)
- `timestamp` — when the event occurred
- `level` — severity (debug, info, warn, error)
- `event` — what happened

### UI Log Viewer

Logs feed into a hierarchical, real-time viewer in the Discord-style dashboard. Entries are expandable and show animated progress for in-flight operations:

```
[narrator] Scene 3 narration started                    12:04:01
|
[narrator] Scene 3 narration complete [v]               12:04:18
    Queried World Lore MCP for Duskwood atmosphere
    |
    Queried Continuity Service - confirmed fog motif
    |
    Generated 450 tokens, 3.2s

[quality] Score: 0.72 - lore inconsistency in NPC...    12:04:20
|
[narrator] Revising Scene 3 narration ...               12:04:21
    Addressing quality feedback ...
```

### Persistence

Log events are stored for post-hoc review — not just ephemeral.

**Detailed logging design**: See `.claude/specs/` (to be designed).

---

## Configuration

### Environment Variables — Layered Overrides

```
Docker (compose env) --overrides--> .env (per-service) --overrides--> default value (in code)
```

Each agent/service has its own `.env` file. `docker-compose.yml` can override any variable. Code provides sensible defaults as the final fallback.

### Key Environment Variables

```
OPENROUTER_API_KEY=<your-api-key>
LLM_MODEL=<provider/model-name>        # OpenRouter format
RABBITMQ_URL=<amqp-connection-string>
SURREALDB_URL=<surrealdb-connection-string>
AGENT_ROLE=<agent-role-identifier>      # Identifies this agent instance
```

---

## Testing

All three layers, built incrementally:

| Layer | Tool | Purpose |
|-------|------|---------|
| Unit | pytest | Individual functions and classes in isolation |
| Integration | pytest | Agent + MCP, Agent + RabbitMQ, Agent + SurrealDB |
| E2E | TBD | Full drama pipeline: trigger to final output |

As each component is added, tests must confirm:
1. The new component works in isolation (unit)
2. The new component fits with existing components (integration)
3. Nothing previously working has broken (regression)

---

## Tooling

| Tool | Purpose |
|------|---------|
| uv | Python package management (per-agent pyproject.toml + uv.lock) |
| Pydantic AI v1.62+ | Agent framework with native MCP support |
| FastMCP | MCP server framework (StreamableHTTP) |
| RabbitMQ | Message broker (aio-pika Python client) |
| SurrealDB | Multi-model database (vector + graph + SQL) |
| Docker + Compose | Containerization and orchestration |
| React + Vite | Frontend framework and build tool |
| TanStack Query | Server state management (data fetching, WebSocket) |
| TanStack Router | Client-side routing |
| TypeScript | Frontend language (strict mode) |
| Custom CSS | Styling — dark theme, Discord aesthetic. No Tailwind. |

---

## UI Architecture

Discord-style agent dashboard with real-time updates.

**Tech stack**: React + Vite + TypeScript + TanStack + Custom CSS (dark theme)

**Layout**: Three panels — channel sidebar (left), message feed (center), context panel (right). Channels map to RabbitMQ queue subscriptions. Messages stream via WebSocket from the FastAPI backend.

**Detailed UI design**: See `.claude/specs/v2-architecture/design.md` (UI Architecture section).

---

## Development Workflow

### Git-flow

| Branch | Purpose |
|--------|---------|
| `main` | Production code |
| `develop` | Active development |
| `feature/*` | New features (one spec = one feature) |
| `bugfix/*` | Bug fixes |
| `release/*` | Releases |
| `hotfix/*` | Emergency fixes |

### Spec-Driven Development

Every feature follows the spec-driven process:

1. **Requirement** — `.claude/specs/{feature}/requirement.md` — user stories, acceptance criteria
2. **Design** — `.claude/specs/{feature}/design.md` — architecture, data models, decisions
3. **Tasks** — `.claude/specs/{feature}/task.md` — checkbox task list, max 2 levels deep

Task status markers: `[ ]` pending, `[-]` in progress, `[x]` done. Each task references its requirement.

### Taskyn Integration

Taskyn is the dashboard. `.claude/specs/` is the substance.

- **Everything is tracked in Taskyn** — no untracked work
- **Time tracking is mandatory** — every work session has a timer running in Taskyn
- Taskyn nodes point to spec files — never duplicate long-form content
- Create stories/tasks only when starting work, directly in "approved" or "in_progress"
- Mark done immediately when work completes — one transition, inline with real work
- Track work as you do it, not before or after

### Functional Slicing

We build vertically by functional unit, not horizontally by tech layer. Infrastructure gets built because a functional unit needs it, not as a separate phase.

**Build order:**
1. Knowledge Acquisition — one researcher-validator pair at a time (World Lore first, then Quest, Character, Dynamics, Narrative History)
2. Drama Production — following the natural flow (Story Architect → Scene Director → Character Director → Narrator → Dialogist → Shot Composer → Quality Assessor → Continuity Service)

The first researcher (World Lore) naturally forces us to build most infrastructure (SurrealDB, Storage MCP, Web Search MCP, Web Crawler MCP, RabbitMQ, Docker). Each subsequent unit is incremental.

---

## Design Documents Index

| Document | Location | Content |
|----------|----------|---------|
| v2 Requirements | `.claude/specs/v2-architecture/requirement.md` | Discovery questions, knowledge domains, architecture requirements |
| v2 Design | `.claude/specs/v2-architecture/design.md` | Full architecture — systems, agents, data model, deployment, UI |
| v2 Tasks | `.claude/specs/v2-architecture/task.md` | Phase-level task checklist |
| Pydantic AI Research | `.claude/research/pydantic-ai-state-of-framework-2026.md` | Framework capabilities and ecosystem |
| WoW Systems Research | `.claude/research/wow-systems-for-roleplay-storytelling.md` | MMORPG data model validation |
| Daemon Processes Research | `.claude/research/autonomous-agent-daemon-processes.md` | Process management and scheduling |
| Docker MCP Research | `.claude/research/docker-mcp-integration.md` | Containerization and MCP Gateway |
| Message Queue Research | `.claude/research/message-queue-for-drama-agents.md` | Broker evaluation and selection |
| Storage Research | `.claude/research/vector-db-knowledge-storage-research.md` | Database evaluation (SurrealDB decision) |

### Custom Skills

| Skill | Location | Purpose |
|-------|----------|---------|
| `/dryrun-design` | `.claude/skills/dryrun-design/SKILL.md` | Dry-run a design doc — 8-pass review for gaps, missing paths, architectural risks |
| `/dryrun-code` | `.claude/skills/dryrun-code/SKILL.md` | Dry-run implemented code — 9-pass review for bugs, missing handling, contract violations |

---

## Quick Start

When working on Mythline:

1. Read this file first
2. Check the design documents index above for deep context
3. Follow SOLID, DRY, KISS
4. PEP 8 for Python, standard conventions for TypeScript
5. Root cause over patch — never shortcut understanding
6. Test incrementally — unit, integration, regression
7. Use git-flow for branches
8. Track work in Taskyn as you do it, link to specs
