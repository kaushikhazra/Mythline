# WLR LLM-Driven Orchestrator — Requirements

## Overview

The World Lore Researcher currently uses a Facade pattern (LoreResearcher wraps 9 agents) driven by a hardcoded 9-step pipeline (pipeline.py). The pipeline decides what runs and when — the agent is passive. This spec replaces that architecture with an LLM-driven Orchestrator pattern: a central LLM agent receives a high-level research goal, dynamically decides which worker sub-agents to invoke, adapts based on intermediate results, and returns structured output to the daemon.

The flow changes from `Daemon → Pipeline → Facade → Sub-agents` to `Daemon → Orchestrator → Sub-agents → Collect → Orchestrator → Daemon → Validator`.

**Key constraints from Kaushik:**
- No checkpointing initially — prove the pattern works first, add crash resilience later
- No token caps initially — observe actual cost per zone, then finetune prompts, then cap
- Pipeline.py disappears entirely — the orchestrator IS the workflow
- Packaging and publishing stay in the daemon — not an LLM decision

---

## User Stories

### WO-1: LLM Orchestrator Agent

**As the** WLR system,
**I want** a central LLM orchestrator agent that receives a zone research goal and autonomously decides which worker sub-agents to invoke and in what order,
**so that** the research workflow is adaptive rather than hardcoded.

**Acceptance Criteria:**
- A new orchestrator agent exists in agent.py with its own system prompt defining its role as research coordinator
- The orchestrator receives a single high-level prompt: "Research zone {zone_name} for game {game_name} comprehensively"
- The orchestrator has access to worker tools (see WO-2) and MCP toolsets (web search)
- The orchestrator dynamically decides: what topics to research, when to extract, when to cross-reference, when it has enough data
- The orchestrator returns a structured output containing: ZoneExtraction, sources, confidence scores, and discovered connected zones
- The orchestrator's conversation with the LLM IS the workflow — no step list, no step dispatch table

### WO-2: Worker Sub-Agents as Tools

**As the** orchestrator agent,
**I want** specialized worker sub-agents exposed as callable tools,
**so that** I can delegate domain-specific work without doing it myself.

**Acceptance Criteria:**
- `research_topic(topic, zone_name)` tool — invokes the search+crawl agent for a specific topic (zone overview, NPCs, factions, lore, narrative items), returns raw content + sources
- `extract_category(category, zone_name, content, sources)` tool — invokes the per-category extraction agent, returns structured Pydantic model (ZoneData, NPCExtractionResult, etc.)
- `cross_reference(extraction)` tool — invokes the cross-ref agent, returns CrossReferenceResult with confidence scores
- `discover_zones(zone_name)` tool — invokes the zone discovery agent, returns list of connected zone slugs
- `summarize_content(content, schema_hint)` tool — calls the MCP Summarizer for content compression
- The existing `crawl_webpage` tool remains available for direct URL crawling
- Each worker tool is a thin wrapper that delegates to a pydantic-ai Agent instance — the worker does the LLM work, the tool just wires it
- Worker agents retain their existing system prompts, output types, and retry settings

### WO-3: Pipeline Elimination

**As a** developer,
**I want** pipeline.py deleted and all orchestration logic owned by the LLM orchestrator,
**so that** there is no hardcoded step sequence and the workflow can adapt per zone.

**Acceptance Criteria:**
- `pipeline.py` is deleted from the codebase
- `PIPELINE_STEPS`, `STEP_FUNCTIONS`, `run_pipeline()`, and all `step_*` functions are removed
- The topic configuration (`research_topics.yml`) remains — the orchestrator's prompt references topic categories
- The summarization logic (content budget, MCP summarizer calls) moves into the `summarize_content` worker tool
- The quality warnings logic (`_compute_quality_warnings`) moves into the daemon's packaging step
- The confidence caps logic (`_apply_confidence_caps`) moves into the daemon's packaging step
- `test_pipeline.py` is deleted and replaced by orchestrator tests

### WO-4: Daemon-Orchestrator Integration

**As the** daemon,
**I want to** launch the orchestrator for each zone instead of calling `run_pipeline()`,
**so that** the daemon remains the process lifecycle manager while the orchestrator owns research decisions.

**Acceptance Criteria:**
- Daemon calls `orchestrator.research_zone(zone_name)` (or equivalent) instead of `run_pipeline(checkpoint, researcher)`
- The orchestrator returns a structured result that the daemon can use to assemble the ResearchPackage
- The daemon owns packaging: assembling ResearchPackage from orchestrator output, computing quality warnings, applying confidence caps
- The daemon owns publishing: sending the package to the validator queue via RabbitMQ
- The daemon owns wave-loop logic: using discovered zones from orchestrator output to queue the next wave
- Status updates: daemon publishes ZONE_STARTED before orchestrator call and ZONE_COMPLETED after — fine-grained step progress deferred to later
- Budget tracking: daemon reads `orchestrator.zone_tokens` after each zone (same pattern as today)

### WO-5: Token Observability

**As** Kaushik,
**I want** the orchestrator to log token usage per zone without enforcing caps,
**so that** I can observe actual cost and finetune before setting limits.

**Acceptance Criteria:**
- Total tokens used per zone are logged as a structured log event after each zone completes
- Token breakdown is available: orchestrator tokens + worker tokens (if trackable)
- No `UsageLimits` are set on the orchestrator agent initially — it runs uncapped
- Worker agents may retain their existing per-call limits as safety nets
- The daemon's existing budget tracking (daily token budget, `save_budget`) continues to work

### WO-6: Functional Equivalence (Output)

**As the** system,
**I want** the orchestrator to produce the same output schema as the current pipeline,
**so that** the validator and downstream systems are unaffected.

**Acceptance Criteria:**
- The ResearchPackage published to the validator queue has the same schema (same fields, same types)
- ZoneExtraction contains: zone, npcs, factions, lore, narrative_items (same models)
- Sources are collected and included in the package
- Confidence scores and quality warnings are computed and included
- Discovered zones are returned for wave expansion
- The output quality may differ (hopefully better — adaptive research) but the schema is identical

---

## Infrastructure Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| RabbitMQ | Exists | No changes — same queues, same message schemas |
| MCP Web Search | Exists | Orchestrator uses it via MCP toolsets (same as today) |
| crawl4ai | Exists | Orchestrator uses crawl_webpage tool (same as today) |
| MCP Summarizer | Exists | Called via summarize_content worker tool |
| Storage MCP | Exists | Used by checkpoint.py (kept but unused initially) |

---

## Configuration Summary

### Existing Environment Variables (unchanged)

```
LLM_MODEL=<provider:model>          # Used by orchestrator and all workers
PER_ZONE_TOKEN_BUDGET=<tokens>      # Worker safety nets only, orchestrator uncapped
DAILY_TOKEN_BUDGET=<tokens>         # Daemon-level daily cap (unchanged)
```

### New Prompts

```
prompts/orchestrator_system.md      # Orchestrator persona and instructions
prompts/orchestrator_task.md        # Per-zone task template
```

### No New Environment Variables

The orchestrator uses the same LLM_MODEL and MCP config as existing agents.

---

## Out of Scope

- **Checkpointing** — no crash resilience for the orchestrator in this spec. If it crashes mid-zone, the zone restarts from scratch. Checkpoint-based recovery is a future spec.
- **Token caps on orchestrator** — observe first, optimize later. Worker safety nets stay.
- **Fine-grained step progress** — daemon reports ZONE_STARTED/ZONE_COMPLETED only. Per-step progress reporting deferred.
- **Prompt optimization** — orchestrator and worker prompts will need tuning after observing real runs. That's iterative, not spec'd.
- **Multi-zone parallelism** — zones still process sequentially within a wave. Parallel zone research is a future optimization.
- **Validator changes** — the validator receives the same ResearchPackage schema. No validator changes needed.
- **New MCP services** — no new infrastructure
- **Frontend/UI changes** — no UI impact
