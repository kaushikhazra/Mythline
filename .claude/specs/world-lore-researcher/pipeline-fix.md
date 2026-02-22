# Pipeline Fix — Wire Agent into Pipeline

## What's Wrong

`pipeline.py` calls `mcp_client.web_search()` and `mcp_client.crawl_url()` directly. The Pydantic AI agent (`agent.py`) is never called. Raw crawled content sits in `checkpoint.step_data` as strings — no LLM extraction, no structured output.

Additionally:
- Step 8 (`cross_reference`) is a no-op.
- Step 9 (`discover_connected_zones`) searches but never parses zone names into `checkpoint.progression_queue`.
- Step 10 (`package_and_send`) builds an empty `ResearchPackage` shell and never publishes to RabbitMQ.

## The 10 Pipeline Steps (reference: `design.md` → Research Pipeline)

| Step | Name | Purpose |
|------|------|---------|
| 1 | `zone_overview_search` | Search for zone overview information |
| 2 | `zone_overview_extract` | Crawl + extract structured zone data |
| 3 | `npc_search` | Search for NPCs and notable characters |
| 4 | `npc_extract` | Crawl + extract structured NPC data |
| 5 | `faction_search_extract` | Search + crawl + extract faction data |
| 6 | `lore_search_extract` | Search + crawl + extract lore/history/cosmology |
| 7 | `narrative_items_search_extract` | Search + crawl + extract legendary items/artifacts |
| 8 | `cross_reference` | Cross-reference all extractions for consistency |
| 9 | `discover_connected_zones` | Find adjacent zones, feed progression queue |
| 10 | `package_and_send` | Assemble ResearchPackage, publish to RabbitMQ |

## What We're Changing

**Primary change: `pipeline.py`.** Additional changes required in `agent.py` and `daemon.py` (see below).

### Step-by-Step Changes

**Steps 1-7** — `pipeline.py` removes direct `mcp_client.web_search()` and `mcp_client.crawl_url()` calls. Instead, each step function in `pipeline.py` calls:
1. `LoreResearcher.research_zone()` — `_research_agent` (which has MCP toolsets) autonomously calls Web Search MCP and crawl4ai to gather raw content.
2. `LoreResearcher.extract_zone_data()` — `_extraction_agent` takes the raw content from step above, returns structured Pydantic models (`ZoneData`, `NPCData`, `FactionData`, `LoreData`, `NarrativeItemData`).
3. `pipeline.py` stores the structured models in `checkpoint.step_data` (not raw strings).

**Step 8** — `pipeline.py` calls `LoreResearcher.cross_reference()`. `_cross_ref_agent` takes all structured extractions from steps 1-7, returns `CrossReferenceResult` with conflicts and confidence scores. `pipeline.py` stores the result in `checkpoint.step_data`.

**Step 9** — `pipeline.py` calls `LoreResearcher.research_zone()` with a zone-discovery prompt. `_research_agent` searches for connected zones and returns parsed zone name slugs. `pipeline.py` adds them to `checkpoint.progression_queue` (filtering out `completed_zones`).

**Step 10** — `pipeline.py` assembles a full `ResearchPackage` from steps 1-8 structured output in `checkpoint.step_data` (populated `npcs`, `factions`, `lore`, `narrative_items`, `conflicts`, `confidence`). `pipeline.py` publishes it as a `MessageEnvelope` to RabbitMQ queue `agent.world_lore_validator`.

### crawl4ai as Agent Tool

crawl4ai uses REST API (not MCP). Register a custom Pydantic AI tool on `_research_agent` that wraps the REST call. The agent decides what to crawl, not the pipeline.

## Additional Fixes (discovered during dry-run)

### `agent.py` — 4 changes needed

**1. Register crawl4ai as a Pydantic AI tool on `_research_agent`.**
Currently `_research_agent` only has Web Search MCP in its toolsets (`mcp_config.json` declares only `search`). crawl4ai is REST, not MCP. `agent.py` must register a custom `@_research_agent.tool` function that wraps the `mcp_client.crawl_url()` REST call. Without this, the agent can search but can't crawl.

**2. `research_zone()` returns `str` — needs to return raw content + sources.**
`pipeline.py` needs raw content and source URLs to pass to `extract_zone_data()`. Currently `research_zone()` returns a single string with no source tracking. Change return type to a structured result containing `raw_content: list[str]` and `sources: list[SourceReference]`.

**3. `extract_zone_data()` extracts everything at once — no per-topic support.**
It returns one `ZoneExtraction` (zone + npcs + factions + lore + narrative_items). The 10-step pipeline calls extraction per topic (steps 1-7 each focus on one domain). Either:
- (a) Call `extract_zone_data()` once after all raw content is gathered (collapse steps 1-7 into research-then-extract), or
- (b) Add per-topic extraction methods (`extract_npcs()`, `extract_factions()`, etc.)

**Decision needed from Kaushik before implementation.**

**4. Add a zone-discovery prompt and method.**
Step 9 needs the agent to search for connected zones and return zone name slugs. Currently no prompt exists for this, and `research_zone()` returns `str` not a list. `agent.py` needs a `discover_connected_zones()` method with a dedicated prompt in `prompts/discover_zones.md` that returns `list[str]`.

### `daemon.py` — 1 change needed

**5. Pass RabbitMQ channel to pipeline.**
Step 10 publishes to RabbitMQ, but `pipeline.py` has no access to the RabbitMQ connection. `daemon.py` owns it. `daemon.py` must pass the RabbitMQ channel (or a publish function) to `run_pipeline()` so `pipeline.py` can publish the `MessageEnvelope` at step 10.

## Validation Checklist

- [ ] `pipeline.py` does NOT import `web_search` or `crawl_url` from `mcp_client`
- [ ] `pipeline.py` creates a `LoreResearcher` instance and calls its methods
- [ ] Steps 1-7 store structured Pydantic models in `step_data`, not raw strings
- [ ] Step 8 calls `cross_reference()` and returns conflicts + confidence
- [ ] Step 9 populates `checkpoint.progression_queue` with zone slugs
- [ ] Step 10 assembles a complete `ResearchPackage` with all fields populated
- [ ] Step 10 publishes to RabbitMQ (`agent.world_lore_validator` queue)
- [ ] Checkpoint saves after each step (crash resilience preserved)
- [ ] Unit tests updated — mock the agent, not `mcp_client`
