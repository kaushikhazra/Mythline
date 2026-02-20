# Mythline v2 Architecture — Design

## Status: Discovery (Memory & Context domain complete, MCP & Orchestration pending)

---

## Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| D1 | Keep Pydantic AI | Preferred over other frameworks, good DX | 2026-02-20 |
| D2 | Expand MCP usage (microservice pattern) | Decoupled, discoverable capabilities | 2026-02-20 |
| D3 | Replace rigid graph workflows with intelligent orchestration | Current system feels like workflow, not intelligence | 2026-02-20 |
| D4 | Overhaul memory & context management | Current JSON dump approach insufficient | 2026-02-20 |
| D5 | Generic MMORPG model, not WoW-specific | Future-proofing, extensible to any MMORPG | 2026-02-20 |
| D6 | Five knowledge domains identified | World Lore, Quest Lore, Character, Dynamics, Narrative History | 2026-02-20 |
| D7 | Story formula: Next = Lore + Quest + Character + Dynamics + Narrative History | Narrative History creates feedback loop | 2026-02-20 |
| D8 | Narrative History stores interactions & effects, not full prose | Scene-level granularity, queryable, not context-window-heavy | 2026-02-20 |
| D9 | Character capabilities (skills/talents) are first-class | Defines narrative possibilities, identity choices, power progression | 2026-02-20 |

---

## Architecture Concepts (evolving)

### Current (v1)
```
Orchestrator Agent → Fixed Graph → Sub-agents (hardcoded)
                  → MCP Servers (4 services)
                  → JSON file memory (per-agent, isolated)
                  → Flat file output (not queryable)
```

### Target (v2) — Emerging
```
Knowledge Layer:  5 domains (World, Quest, Character, Dynamics, Narrative History)
Service Layer:    MCP microservices (TBD — discovery pending)
Agent Layer:      Intelligent orchestration (TBD — discovery pending)
Scene Assembly:   Context composed from knowledge domains per moment
Story Output:     Feeds back into Narrative History (feedback loop)
```

---

## Knowledge Architecture (from Memory & Context discovery)

### Story Formula
```
Next Story = World Lore + Quest Lore + Character + Dynamics + Narrative History
                                                                    ↑
                                                    (each story feeds back in)
```

### Domain Summary

**World Lore** — The canonical game world. Zones, factions, NPCs, cosmology, history. Shared across all characters. Era-versioned (same zone can exist in multiple time periods). Relatively static but can be expanded.

**Quest Lore** — Specific quest chains and their narrative structure. Prerequisites, branching, outcomes. Gated by faction/class/progression.

**Character** — Full character model: identity, archetype, specialization, capabilities (skills/talents/professions), evolving nature, reputation graph, journal, era-layered growth arc, relationships.

**Dynamics** — Not stored, computed. NPC dispositions, faction politics toward this character, phased world state. Assembled from character reputation + world state + interaction history.

**Narrative History** — Scene-level index of previous story interactions. Tracks: what world/quest/NPC interactions happened, character effects (growth, reputation, emotional state), narrative threads (opened/closed/dangling), continuity bridges. NOT the prose — just the structured interactions.

### Data Model Layers
See requirement.md for full MMORPG-generic data model covering:
- World Layer (era-versioned, character-phased)
- Character Layer (era-layered, capability-rich)
- Narrative History Layer (scene-level interactions & effects)
- Scene Layer (ephemeral, assembled from all above)

### Open Design Questions (for later phases)
- Storage technology per domain (vector DB, graph DB, structured JSON, hybrid?)
- How Dynamics get computed efficiently
- Narrative History indexing strategy
- Context window budget allocation across domains
- Query patterns for scene assembly

---

## Component Design

_To be filled after all discovery phases complete (MCP architecture, orchestration model)_
