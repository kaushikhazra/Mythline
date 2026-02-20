# Mythline v2 Architecture — Requirements

## Discovery Phase

### Context
Mythline is a multi-agent AI storytelling system built ~6 months ago. The AI/agentic landscape has evolved significantly since then. The current architecture has pain points around rigid orchestration, poor memory management, and tightly coupled agent integrations. A v2 architecture is needed.

### What We're Keeping
- **Pydantic AI** as the agent framework
- **Core domain** — MMORPG narrative generation (generic, not WoW-specific)
- **MCP protocol** — but expanding its role significantly

### What Needs to Change
- [ ] **MCP as microservices** — each capability as a discoverable MCP service
- [ ] **Intelligent orchestration** — agents that reason and decide, not fixed pipelines
- [ ] **Memory & context management** — complete overhaul of how agents remember and share knowledge

---

## Open Questions (Discovery)

### MCP Architecture
- Q1: Should agents themselves become MCP servers, making them discoverable/callable by other agents?
- Q2: What granularity for MCP services? (per-capability vs per-domain)
- Q3: How do agents discover available MCP tools dynamically?

### Orchestration
- Q4: Orchestrator agent that decides which agents/tools to call based on situation vs fixed graph?
- Q5: Should agents be able to loop, backtrack, ask for more info, change strategy mid-task?
- Q6: What role do graphs still play? (guardrails vs full control)

### Memory & Context
- ~~Q7: What specific pain was felt?~~ **ANSWERED** — All of it: cross-session loss, no shared knowledge, context window bloat. Plus the information model itself is wrong — it's not one kind of information.
- ~~Q8: What memory tiers are needed?~~ **ANSWERED** — See five knowledge domains below.
- Q9: How should context be managed to avoid blowing up token windows?

---

## Discovery Findings — Memory & Knowledge Model

### The Story Formula
```
Next Story = World Lore + Quest Lore + Character + Dynamics + Narrative History
```
Each generated story feeds back into Narrative History, creating a cumulative feedback loop.

### Five Knowledge Domains

| Domain | What | Nature | Storage Hint |
|--------|------|--------|-------------|
| World Lore | Canonical game knowledge — zones, factions, cosmology, history | Shared, mostly static, era-versioned | Knowledge graph / vector DB |
| Quest Lore | Specific quest chain narratives and structure | Shared, structured | Structured data |
| Character | Identity, capability, nature, reputation, growth | Per-character, evolving | Persistent structured data |
| Dynamics | NPC reactions, faction politics, phased world state | Computed from character + world | Assembled at scene time |
| Narrative History | Interactions & effects from previous stories | Per-character, cumulative, scene-level | Indexed interactions (not full prose) |

### Generic MMORPG Data Model

#### WORLD LAYER (persistent, shared, era-versioned)
- **Region / Zone** — narrative arc, political climate, access gating, state variants (phased per character progress)
- **NPC** — faction allegiance(s), personality, motivations, relationships to other NPCs, offered quest threads, phased state
- **Faction** — hierarchical (guild < order < major faction), inter-faction relationships (allied/hostile/neutral), mutual exclusions, ideology/goals
- **Quest / Event** — prerequisites (progression/faction/class gating), narrative thread, outcomes (world state mutations, reputation shifts)
- **Lore / Cosmology** — power sources, world history/mythology, cosmic rules and tensions
- **Narrative Items** — own story arc, wielder lineage, power/significance

#### CHARACTER LAYER (persistent, individual, era-layered)
- **Identity** — race/species (cultural background), archetype (class/role), specialization (chosen path), power source, origin/backstory
- **Capability** — active abilities (narrative capabilities), passive traits, mastery level, talent choices (made AND rejected), professions/tradecraft, power dynamic (cost, limits, vulnerabilities)
- **Nature** (evolving) — personality traits, moral alignment, motivations
- **Reputation Graph** — per faction (hierarchy-aware), per NPC (personal), exclusivity effects
- **Journal** — quest completions + choices, events witnessed/participated, relationships formed/broken, capability milestones
- **Growth Arc** — era-specific identity (title, role, allegiance per era), pivotal moments, who they were → who they're becoming
- **Relationships** — party members/companions, mentors/rivals/bonds, shared experiences

#### NARRATIVE HISTORY LAYER (per-character, cumulative)
- **NOT the full story prose** — stored as files separately
- **Indexed interactions**: world/quest/NPC/character interactions per scene
- **Effects**: reputation shifts, character growth moments, emotional state changes
- **Threads**: opened/closed narrative threads, foreshadowing, promises, unresolved tension
- **Continuity**: scene-level context for bridging between stories

#### SCENE LAYER (ephemeral, assembled per moment)
- World state for THIS character at THIS time (phased)
- Party composition + their capabilities
- NPC dispositions (computed from reputation + history + faction politics)
- Active narrative threads
- Available actions (constrained by character capabilities)
- Dramatic tension (computed from all layers)

### WoW Validation
Model validated against WoW systems. Critical gaps found and addressed:
1. World state mutation / phasing — added state variants per character
2. Temporal / era axis — added era-versioning
3. Class as first-class entity — elevated to archetype + specialization + power source
4. Era-scoped character identity — added era-specific growth arc layers
5. Party / group content — added relationships + party in scene layer
6. Character capabilities — added full capability model (abilities, talents, mastery, professions, power dynamics)

Full research: `.claude/research/wow-systems-for-roleplay-storytelling.md`

---

## User Stories (to be filled as discovery progresses)

_Pending — will derive from finalized knowledge domains and architecture decisions_
