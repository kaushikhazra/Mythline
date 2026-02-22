# World Lore Researcher — Requirements

## Overview

Autonomous daemon agent that researches MMORPG game world data from open web sources. It follows the game's zone progression tree as a research map, going depth-first per zone, and builds a comprehensive knowledge base of the game world. The data it produces is shared across all characters — it is world research, not character research.

WoW is the first target, but the agent is MMORPG-generic by design.

---

## User Stories

### US-1: Autonomous Research Daemon

As the system, I want the World Lore Researcher to run continuously as an autonomous daemon, so that the knowledge base grows without manual intervention.

**Acceptance Criteria:**
- Runs as a long-lived daemon process inside a Docker container
- Starts research cycles automatically based on configurable schedule
- Configurable delay between research cycles (env var: `RESEARCH_CYCLE_DELAY_MINUTES`)
- Self-healing — transient failures (network, API) trigger retry with backoff, never crash the daemon
- Logs all activity as structured JSON events for UI observability

### US-2: Progression-Based Research Map

As the system, I want the researcher to follow the game's zone progression tree to decide what to research next, so that research happens in a natural, game-relevant order.

**Acceptance Criteria:**
- Uses the game's zone progression tree as the research map
- Starts from a configurable starting zone
- After completing one zone (depth-first), follows the progression tree to the next zone
- At forks (multiple next zones), asks the user which branch to prioritize
- The non-prioritized branch is queued — it gets researched later, not skipped
- Eventually all reachable zones get researched, but in user-preferred order

### US-3: Depth-First Zone Research

As the system, I want the researcher to fully flesh out each zone before moving to the next, so that the knowledge base has complete, usable data for any zone it has visited.

**Acceptance Criteria:**
- For each zone, researches ALL of the following:
  - Zone metadata: name, level range, narrative arc, political climate, access gating, phase states
  - NPCs present: faction allegiance(s), personality, motivations, relationships to other NPCs, offered quest threads, phased state
  - Factions active in the zone: hierarchy, inter-faction relationships, mutual exclusions, ideology/goals
  - Lore and cosmology relevant to the zone: power sources, history, mythology, cosmic tensions
  - Narrative items associated with the zone: story arc, wielder lineage, significance
- Does not move to the next zone until the current zone passes validation

### US-4: Multi-Source Cross-Referenced Research

As the system, I want the researcher to use multiple independent sources and cross-reference them, so that the data is reliable and conflicts are surfaced.

**Acceptance Criteria:**
- Searches a minimum of N independent sources per claim (N configurable)
- Cross-references data across sources within its own work
- Packages research output with:
  - Structured data (per the World Lore data model)
  - Source URLs and attribution
  - Confidence level per data point
  - Any conflicts found between sources (with details)
- Uses the configured source priority list to prefer authoritative sources

### US-5: Source Priority Configuration

As the operator, I want to configure a prioritized list of trusted sources per game, so that the researcher prefers authoritative sources and the validator can assess source quality.

**Acceptance Criteria:**
- Source list defined in a YAML config file (`config/sources.yml`)
- Each source has: domain, tier (official, primary, secondary)
- Researcher prefers higher-tier sources when searching
- Validator uses the same config to assess source quality in packages
- Swappable per game — changing the YAML file adapts the researcher to a different MMORPG

### US-6: Validator Communication via RabbitMQ

As the system, I want the researcher to communicate with the World Lore Validator via RabbitMQ, so that research packages are validated before storage.

**Acceptance Criteria:**
- Sends research packages to the validator's RabbitMQ channel
- Receives validation feedback (accept/reject with specific reasons) on its own channel
- On rejection: adjusts research strategy based on feedback, retries
- Iteration cap on research-validate loop (env var: `MAX_RESEARCH_VALIDATE_ITERATIONS`)
- If iteration cap is hit: discard the data point, log the failure, move on
- Daemon picks up the failed data point on a future research cycle

### US-7: Token and Cost Budget Controls

As the operator, I want configurable token and cost budgets, so that the researcher doesn't blow through API credits unchecked.

**Acceptance Criteria:**
- Per-cycle token budget (env var: `PER_CYCLE_TOKEN_BUDGET`) — hard stop per zone
- Daily token budget (env var: `DAILY_TOKEN_BUDGET`) — hard stop per day
- Pre-flight cost estimation before each LLM call — skip if it would exceed budget
- When budget is exhausted: pause gracefully, log the reason, resume on next cycle/day
- Token usage tracked and logged for observability

### US-8: Rate Limiting and Backoff

As the system, I want rate limiting and backoff strategies, so that the researcher respects API and web source limits without crashing.

**Acceptance Criteria:**
- Exponential backoff with jitter for transient failures (using `tenacity`)
- Token bucket rate limiting for sustained request control (using `aiolimiter`)
- Configurable requests per minute (env var: `RATE_LIMIT_REQUESTS_PER_MINUTE`)
- Respects web source rate limits (crawl politely)
- Separate rate limits for: web search API, web crawler, LLM API

### US-9: Structured Logging for Observability

As the operator, I want all research activity logged as structured JSON events, so that I can monitor the researcher in the UI log viewer.

**Acceptance Criteria:**
- Every log event includes: `agent_id`, `domain` (world_lore), `timestamp`, `level`, `event`
- Key events logged: research cycle start/end, zone research start/end, source queried, data point found, conflict detected, package sent to validator, validation result received, budget warnings, errors
- Supports hierarchical expansion in the UI (parent event with sub-events)
- In-progress events emit animated state (for UI "in progress..." indicators)

---

## Infrastructure Dependencies

This is the first agent to be built. It requires:

| Dependency | Status | Notes |
|-----------|--------|-------|
| Web Search MCP | To be built | DuckDuckGo search |
| Web Crawler MCP | To be built | URL content extraction |
| Embedding MCP | To be built | Vector embedding generation |
| Storage MCP | To be built | SurrealDB backend — requires SurrealDB PoC |
| SurrealDB | To be built | PoC needed to validate on Windows |
| RabbitMQ | To be built | For researcher ↔ validator communication |
| Docker | To be built | Container for the agent |

---

## Configuration Summary

### Environment Variables

```
RESEARCH_CYCLE_DELAY_MINUTES=<delay-between-zones>
DAILY_TOKEN_BUDGET=<max-tokens-per-day>
PER_CYCLE_TOKEN_BUDGET=<max-tokens-per-zone>
MAX_RESEARCH_VALIDATE_ITERATIONS=<max-retries-with-validator>
RATE_LIMIT_REQUESTS_PER_MINUTE=<throttle-web-requests>
STARTING_ZONE=<first-zone-to-research>
```

### Config Files

```
config/sources.yml          # Tiered source priority list per game
config/progression.yml      # Zone progression tree (or discovered dynamically)
```
