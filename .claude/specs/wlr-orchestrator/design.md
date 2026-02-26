# WLR LLM-Driven Orchestrator — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Orchestrator agent has no `output_type` — structured data accumulated via `OrchestratorContext` deps | Worker tools return large structured data (ZoneData, NPCExtractionResult, etc.). Using `output_type` would force the LLM to re-serialize all accumulated data in its final response — expensive and error-prone. Deps-based accumulation keeps structured data intact through the tool layer. _(WO-1, WO-2)_ |
| D2 | Worker agent instances passed to orchestrator via deps, not captured as closures | Pydantic-ai tool functions only access state through `ctx.deps`. Putting worker agents in `OrchestratorContext` gives tools clean access without closures or module-level singletons. Follows the established `ResearchContext` pattern. _(WO-2)_ |
| D3 | Orchestrator has NO MCP toolsets directly — delegates web search via `research_topic` worker tool | Blueprint principle: "An orchestrator orchestrates — it does not also do web search." The research worker agent has MCP toolsets; the orchestrator delegates. `crawl_webpage` stays as a direct tool for ad-hoc URL crawling. _(WO-1, Blueprint)_ |
| D4 | Tool functions take minimal arguments (decision parameters only) — read accumulated data from deps | The orchestrator LLM decides WHAT to do (which topic, which category). Tools handle the HOW (reading from deps, formatting prompts, calling workers). Avoids passing huge content strings through tool arguments. _(WO-2)_ |
| D5 | `summarize_content` is a separate explicit tool, not bundled into `extract_category` | WO-2 lists it as a distinct tool. Gives the orchestrator explicit control over when to summarize. The system prompt instructs the orchestrator to summarize before extracting when content is large. _(WO-2, WO-3)_ |
| D6 | `_compute_quality_warnings` and `_apply_confidence_caps` move to daemon.py as private helpers | WO-3 says these move into the daemon's packaging step. They're small (<40 lines each), mechanical, and only called during packaging. No need for a separate module. _(WO-3, WO-4)_ |
| D7 | Orchestrator tools live in a new `orchestrator_tools.py` module (separate from existing `tools.py`) | The orchestrator's tools have `RunContext[OrchestratorContext]` deps type. The existing `crawl_webpage` in tools.py has `RunContext[ResearchContext]`. Different dep types require different functions. Separate files keep the separation clean and each file focused. _(Blueprint: tools.py per agent concern)_ |
| D8 | `OrchestratorResult` and `OrchestratorContext` are dataclasses in agent.py, not Pydantic models | They are internal data structures — `OrchestratorContext` is agent runtime deps, `OrchestratorResult` is a return value between `research_zone()` and the daemon. Not message schemas or LLM output types. Blueprint: "Dataclasses used as agent runtime deps stay in agent.py." _(Blueprint anatomy)_ |
| D9 | Checkpoint code stays but per-zone functions are unused — budget functions remain active | No checkpointing initially per requirements. checkpoint.py's budget functions (save/load/check budget) are still used by the daemon. Per-zone checkpoint functions become dormant, ready for future checkpoint spec. _(WO out of scope)_ |
| D10 | `PIPELINE_STEPS`, `STEP_FUNCTIONS`, `run_pipeline()` and all step functions deleted — no dead code kept | Pipeline.py disappears entirely per WO-3. The orchestrator replaces the pipeline. Keeping dead code invites confusion and maintenance burden. _(WO-3)_ |
| D11 | Topic accessor functions (`get_topic_instructions`, etc.) move from pipeline.py to config.py | These are configuration accessors — they read from `research_topics.yml`. config.py already owns `load_research_topics()`. Centralizing topic access in config.py follows the blueprint: "config.py = centralized env var reads + config loaders." _(WO-3, Blueprint)_ |
| D12 | Last-wave skip of `discover_zones` controlled via task prompt, not by removing tools | The orchestrator's task prompt includes an optional `{skip_discovery}` directive. Simpler than dynamically modifying the tool set. Saves a few thousand tokens. _(WO-4)_ |

---

## 1. Orchestrator Agent Architecture

### 1.1 High-Level Flow

```
Daemon
  -> researcher.research_zone(zone_name)
    -> Orchestrator Agent (single LLM conversation)
      -> research_topic("zone_overview_research")     [worker -> research agent]
      -> research_topic("npc_research")                [worker -> research agent]
      -> research_topic("faction_research")            [worker -> research agent]
      -> research_topic("lore_research")               [worker -> research agent]
      -> research_topic("narrative_items_research")    [worker -> research agent]
      -> summarize_content("npc_research")             [worker -> MCP Summarizer]  (if large)
      -> extract_category("zone")                      [worker -> extraction agent]
      -> extract_category("npcs")                      [worker -> extraction agent]
      -> extract_category("factions")                  [worker -> extraction agent]
      -> extract_category("lore")                      [worker -> extraction agent]
      -> extract_category("narrative_items")           [worker -> extraction agent]
      -> cross_reference()                             [worker -> cross-ref agent]
      -> discover_zones()                              [worker -> discovery agent]
    <- OrchestratorResult (assembled from accumulated deps)
  -> Daemon assembles ResearchPackage
  -> Daemon computes quality warnings + confidence caps
  -> Daemon publishes to validator queue
```

The flow above is a **typical** sequence, not a fixed order. The orchestrator LLM dynamically decides:
- Order and frequency of tool calls
- Whether to research a topic multiple times if initial results are sparse
- Whether to skip topics if the zone has no relevant data for a category
- When to summarize (based on accumulated content size)
- Whether to crawl additional URLs directly via `crawl_webpage`

### 1.2 Agent Construction

```python
# agent.py

class LoreResearcher:
    AGENT_ID = "world_lore_researcher"

    def __init__(self):
        self._zone_tokens: int = 0
        self._crawl_cache: dict[str, str] = {}
        self._mcp_servers = load_mcp_config(__file__)

        # --- Worker agents (construction unchanged from current) ---

        self._research_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            deps_type=ResearchContext,
            toolsets=self._mcp_servers,
            retries=2,
        )
        self._research_agent.tool(crawl_webpage)  # from tools.py (ResearchContext)

        self._extraction_agents: dict[str, Agent] = {}
        for category, (output_type, _, _) in EXTRACTION_CATEGORIES.items():
            self._extraction_agents[category] = Agent(
                LLM_MODEL,
                system_prompt=load_prompt(__file__, "system_prompt"),
                output_type=output_type,
                retries=2,
            )

        self._cross_ref_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "cross_reference"),
            output_type=CrossReferenceResult,
            retries=2,
        )

        self._zone_discovery_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "discover_zones_system"),
            output_type=ConnectedZonesResult,
            toolsets=self._mcp_servers,
            retries=2,
        )

        # --- Orchestrator agent (NEW) ---

        self._orchestrator = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "orchestrator_system"),
            deps_type=OrchestratorContext,
            retries=2,
        )
        # Register orchestrator tools (from orchestrator_tools.py)
        self._orchestrator.tool(orch_research_topic)
        self._orchestrator.tool(orch_extract_category)
        self._orchestrator.tool(orch_cross_reference)
        self._orchestrator.tool(orch_discover_zones)
        self._orchestrator.tool(orch_summarize_content)
        self._orchestrator.tool(orch_crawl_webpage)
```

**Worker agents are unchanged.** Same system prompts, same output types, same retry settings, same MCP toolsets. The only change is who calls them — orchestrator tools instead of pipeline step functions.

### 1.3 OrchestratorContext (deps dataclass)

```python
# agent.py

@dataclass
class OrchestratorContext:
    """Accumulates results from worker tool calls during orchestration.

    Worker tools read zone context, delegate to worker agents, and store
    results here. The orchestrator LLM only sees brief text summaries;
    the structured data flows through deps without LLM re-serialization.
    """
    # --- Worker agent references (set once in research_zone) ---
    research_agent: Agent
    extraction_agents: dict[str, Agent]
    cross_ref_agent: Agent
    discovery_agent: Agent
    mcp_servers: list  # MCPServerStreamableHTTP instances

    # --- Zone context ---
    zone_name: str
    game_name: str
    crawl_cache: dict[str, str]

    # --- Research accumulator (populated by research_topic + crawl_webpage) ---
    research_content: dict[str, list[str]] = field(default_factory=dict)
    sources: list[SourceReference] = field(default_factory=list)

    # --- Extraction accumulator (populated by extract_category) ---
    zone_data: ZoneData | None = None
    npcs: list[NPCData] = field(default_factory=list)
    factions: list[FactionData] = field(default_factory=list)
    lore: list[LoreData] = field(default_factory=list)
    narrative_items: list[NarrativeItemData] = field(default_factory=list)

    # --- Cross-reference (populated by cross_reference) ---
    cross_ref_result: CrossReferenceResult | None = None

    # --- Discovery (populated by discover_zones) ---
    discovered_zones: list[str] = field(default_factory=list)

    # --- Token tracking ---
    worker_tokens: int = 0
```

### 1.4 OrchestratorResult (return dataclass)

```python
# agent.py

@dataclass
class OrchestratorResult:
    """Result from a complete zone research orchestration.

    Assembled from OrchestratorContext after the orchestrator conversation
    completes. The daemon reads this to build ResearchPackage.
    """
    zone_data: ZoneData | None = None
    npcs: list[NPCData] = field(default_factory=list)
    factions: list[FactionData] = field(default_factory=list)
    lore: list[LoreData] = field(default_factory=list)
    narrative_items: list[NarrativeItemData] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)
    cross_ref_result: CrossReferenceResult | None = None
    discovered_zones: list[str] = field(default_factory=list)
    orchestrator_tokens: int = 0
    worker_tokens: int = 0
```

### 1.5 research_zone() — Entry Point

```python
# agent.py — LoreResearcher method

async def research_zone(self, zone_name: str, skip_discovery: bool = False) -> OrchestratorResult:
    """Run the orchestrator to research a zone comprehensively.

    Returns OrchestratorResult assembled from accumulated deps.
    The daemon uses this to build the ResearchPackage.
    """
    template = load_prompt(__file__, "orchestrator_task")
    skip_msg = (
        "\nDo NOT call discover_zones - this is the final depth wave."
        if skip_discovery else ""
    )
    prompt = template.format(
        zone_name=zone_name.replace("_", " "),
        game_name=GAME_NAME,
        skip_discovery=skip_msg,
    )

    context = OrchestratorContext(
        research_agent=self._research_agent,
        extraction_agents=self._extraction_agents,
        cross_ref_agent=self._cross_ref_agent,
        discovery_agent=self._zone_discovery_agent,
        mcp_servers=self._mcp_servers,
        zone_name=zone_name,
        game_name=GAME_NAME,
        crawl_cache=self._crawl_cache,
    )

    result = await self._orchestrator.run(prompt, deps=context)

    orchestrator_tokens = result.usage().total_tokens or 0
    self._zone_tokens += orchestrator_tokens + context.worker_tokens

    return OrchestratorResult(
        zone_data=context.zone_data,
        npcs=context.npcs,
        factions=context.factions,
        lore=context.lore,
        narrative_items=context.narrative_items,
        sources=context.sources,
        cross_ref_result=context.cross_ref_result,
        discovered_zones=context.discovered_zones,
        orchestrator_tokens=orchestrator_tokens,
        worker_tokens=context.worker_tokens,
    )
```

**Removed methods:** `extract_category()`, `cross_reference()`, `discover_connected_zones()` — these were the old facade methods called by pipeline step functions. Now handled by orchestrator tools.

**Kept:** `zone_tokens` property, `reset_zone_state()` — daemon interface unchanged.

### 1.6 Orchestrator Prompt Strategy

Two new prompt files:

**`prompts/orchestrator_system.md`** — Persona and lifecycle instructions:
- Persona: research coordinator that dynamically plans zone research
- Available tools listed with descriptions and when to use each
- Workflow guidance: research -> summarize (if needed) -> extract -> cross-reference -> discover
- Topic list: `zone_overview_research`, `npc_research`, `faction_research`, `lore_research`, `narrative_items_research`
- Category list: `zone`, `npcs`, `factions`, `lore`, `narrative_items`
- Content budget guidance: summarize topics before extracting if total research content exceeds ~300k characters
- Quality mandate: research all 5 topics, extract all 5 categories, always cross-reference
- Constraints: never fabricate data, never skip cross-reference

**`prompts/orchestrator_task.md`** — Per-zone task template:

```markdown
Research zone '{zone_name}' for game '{game_name}' comprehensively.

Research all five topics, extract structured data for all five categories,
cross-reference the results, and discover connected zones.

Available topics: zone_overview_research, npc_research, faction_research,
lore_research, narrative_items_research

Available extraction categories: zone, npcs, factions, lore, narrative_items
{skip_discovery}
```

---

## 2. Worker Tools Interface

All orchestrator tool functions live in `src/orchestrator_tools.py`. Each tool:
1. Takes minimal arguments (decision parameters — which topic, which category)
2. Reads accumulated data from `ctx.deps` (OrchestratorContext)
3. Delegates to a worker agent (pydantic-ai Agent instance from deps)
4. Stores structured results back in `ctx.deps`
5. Returns a brief text summary to the orchestrator LLM

### 2.1 Category-to-Topic Mapping

```python
# orchestrator_tools.py

CATEGORY_TO_TOPIC = {
    "zone": "zone_overview_research",
    "npcs": "npc_research",
    "factions": "faction_research",
    "lore": "lore_research",
    "narrative_items": "narrative_items_research",
}
```

### 2.2 research_topic

```python
async def research_topic(ctx: RunContext[OrchestratorContext], topic: str) -> str:
    """Research a specific topic for the current zone.

    Searches the web and crawls pages for a specific aspect of the zone.
    Content is accumulated internally.

    Args:
        topic: One of: zone_overview_research, npc_research, faction_research,
               lore_research, narrative_items_research
    """
    deps = ctx.deps

    # Load topic instructions from research_topics.yml (via config)
    instructions = get_topic_instructions(topic).format(
        zone=deps.zone_name.replace("_", " "),
        game=deps.game_name,
    )

    # Format the research prompt (same template as current)
    template = load_prompt(__file__, "research_zone")
    prompt = template.format(
        zone_name=deps.zone_name.replace("_", " "),
        instructions=instructions,
    )

    # Create research context with shared crawl cache
    research_ctx = ResearchContext(crawl_cache=deps.crawl_cache)

    # Run the research worker agent (with MCP toolsets for web search)
    async with AsyncExitStack() as stack:
        for server in deps.mcp_servers:
            await stack.enter_async_context(server)
        result = await deps.research_agent.run(
            prompt,
            deps=research_ctx,
            usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET),
        )

    # Accumulate in orchestrator deps
    deps.research_content.setdefault(topic, []).extend(research_ctx.raw_content)
    deps.sources.extend(research_ctx.sources)
    deps.worker_tokens += result.usage().total_tokens or 0

    content_chars = sum(len(c) for c in research_ctx.raw_content)
    return (
        f"Researched {topic}: {len(research_ctx.raw_content)} content blocks "
        f"({content_chars:,} chars), {len(research_ctx.sources)} sources"
    )
```

**Key:** The research worker agent uses `ResearchContext` deps internally (unchanged). The orchestrator tool bridges between `OrchestratorContext` and `ResearchContext` — creating a fresh `ResearchContext` per call with the shared `crawl_cache`, then copying accumulated results back.

### 2.3 extract_category

```python
async def extract_category(ctx: RunContext[OrchestratorContext], category: str) -> str:
    """Extract structured data for one category from accumulated research content.

    Reads accumulated content for the corresponding topic internally.
    Must be called after researching the relevant topic.

    Args:
        category: One of: zone, npcs, factions, lore, narrative_items
    """
    deps = ctx.deps
    topic = CATEGORY_TO_TOPIC[category]

    # Read accumulated content for this topic
    content_blocks = deps.research_content.get(topic, [])
    if not content_blocks:
        return f"No research content for category '{category}' (topic '{topic}'). Research first."

    header = get_topic_section_header(topic)
    content = f"{header}\n\n" + "\n\n".join(content_blocks)

    # Format extraction prompt (same templates as current)
    _, prompt_name, token_share = EXTRACTION_CATEGORIES[category]
    source_info = "\n".join(f"- {s.url} (tier: {s.tier.value})" for s in deps.sources)
    template = load_prompt(__file__, prompt_name)
    prompt = template.format(
        zone_name=deps.zone_name,
        source_info=source_info,
        raw_content=content,
    )

    # Run extraction worker agent
    agent = deps.extraction_agents[category]
    budget = int(PER_ZONE_TOKEN_BUDGET * token_share)
    result = await agent.run(
        prompt,
        usage_limits=UsageLimits(output_tokens_limit=budget),
    )
    deps.worker_tokens += result.usage().total_tokens or 0

    # Store structured result in deps (type depends on category)
    output = result.output
    if category == "zone":
        deps.zone_data = output
        return f"Extracted zone: {output.name}, narrative_arc={len(output.narrative_arc)} chars"
    elif category == "npcs":
        deps.npcs = output.npcs
        return f"Extracted {len(output.npcs)} NPCs"
    elif category == "factions":
        deps.factions = output.factions
        return f"Extracted {len(output.factions)} factions"
    elif category == "lore":
        deps.lore = output.lore
        return f"Extracted {len(output.lore)} lore entries"
    elif category == "narrative_items":
        deps.narrative_items = output.narrative_items
        return f"Extracted {len(output.narrative_items)} narrative items"

    return f"Unknown category: {category}"
```

### 2.4 cross_reference

```python
async def cross_reference(ctx: RunContext[OrchestratorContext]) -> str:
    """Cross-reference all extracted data for consistency and confidence scores.

    Must be called after all categories are extracted.
    """
    deps = ctx.deps

    if not deps.zone_data:
        return "Error: no zone data extracted yet. Extract all categories first."

    extraction = ZoneExtraction(
        zone=deps.zone_data,
        npcs=deps.npcs,
        factions=deps.factions,
        lore=deps.lore,
        narrative_items=deps.narrative_items,
    )

    template = load_prompt(__file__, "cross_reference_task")
    prompt = template.format(
        zone_name=extraction.zone.name,
        npc_count=len(extraction.npcs),
        faction_count=len(extraction.factions),
        lore_count=len(extraction.lore),
        narrative_item_count=len(extraction.narrative_items),
        full_data=extraction.model_dump_json(indent=2),
    )

    result = await deps.cross_ref_agent.run(
        prompt,
        usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET // 2),
    )
    deps.worker_tokens += result.usage().total_tokens or 0
    deps.cross_ref_result = result.output

    return (
        f"Cross-reference complete: consistent={result.output.is_consistent}, "
        f"{len(result.output.conflicts)} conflicts, "
        f"confidence: {result.output.confidence}"
    )
```

### 2.5 discover_zones

```python
async def discover_zones(ctx: RunContext[OrchestratorContext]) -> str:
    """Discover zones connected to the current zone for wave expansion."""
    deps = ctx.deps
    zone_display = deps.zone_name.replace("_", " ")

    template = load_prompt(__file__, "discover_zones")
    prompt = template.format(zone_name=zone_display, game_name=deps.game_name)

    async with AsyncExitStack() as stack:
        for server in deps.mcp_servers:
            await stack.enter_async_context(server)
        result = await deps.discovery_agent.run(
            prompt,
            usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET // 4),
        )

    deps.worker_tokens += result.usage().total_tokens or 0
    deps.discovered_zones = result.output.zone_slugs

    slugs = result.output.zone_slugs
    preview = ", ".join(slugs[:5]) + ("..." if len(slugs) > 5 else "")
    return f"Discovered {len(slugs)} connected zones: {preview}"
```

### 2.6 summarize_content

```python
async def summarize_content(ctx: RunContext[OrchestratorContext], topic: str) -> str:
    """Compress accumulated research content for a topic via the MCP Summarizer.

    Replaces the raw content for the specified topic with a compressed version.
    Call this before extract_category if accumulated content is very large.

    Args:
        topic: The topic to summarize (same names as research_topic)
    """
    deps = ctx.deps
    content_blocks = deps.research_content.get(topic, [])
    if not content_blocks:
        return f"No content for topic '{topic}' - nothing to summarize."

    body = "\n\n".join(content_blocks)
    original_chars = len(body)
    schema_hint = get_topic_schema_hints(topic)
    num_topics = max(len(deps.research_content), 1)

    result = await mcp_call(
        MCP_SUMMARIZER_URL,
        "summarize_for_extraction",
        {
            "content": body,
            "schema_hint": schema_hint,
            "max_output_tokens": 75_000 // num_topics,
        },
        timeout=30.0,
        sse_read_timeout=300.0,
    )

    if result and isinstance(result, str) and len(result) < original_chars:
        deps.research_content[topic] = [result]
        return f"Summarized {topic}: {original_chars:,} -> {len(result):,} chars"
    else:
        return f"Summarization failed for {topic} - content unchanged ({original_chars:,} chars)"
```

### 2.7 crawl_webpage (orchestrator version)

```python
async def crawl_webpage(ctx: RunContext[OrchestratorContext], url: str) -> str:
    """Crawl a URL and extract its content as markdown.

    Use this for ad-hoc URL crawling. Content accumulates under the '_direct' topic.
    """
    deps = ctx.deps
    cache_key = normalize_url(url)

    if cache_key in deps.crawl_cache:
        content = deps.crawl_cache[cache_key]
        deps.research_content.setdefault("_direct", []).append(content)
        deps.sources.append(make_source_ref(url))
        truncated = content[:CRAWL_CONTENT_TRUNCATE_CHARS]
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return truncated + "\n\n[... cached, full version captured ...]"
        return content

    result = await rest_crawl_url(url)
    content = result.get("content")
    if content:
        deps.crawl_cache[cache_key] = content
        deps.research_content.setdefault("_direct", []).append(content)
        deps.sources.append(make_source_ref(url))
        if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
            return (
                content[:CRAWL_CONTENT_TRUNCATE_CHARS]
                + "\n\n[... content truncated, full version captured ...]"
            )
        return content

    error = result.get("error", "unknown error")
    return f"Failed to crawl {url}: {error}"
```

### 2.8 Tool Name Registration

Orchestrator tools are imported with aliases in agent.py to avoid name collisions with existing tools/methods, but the pydantic-ai tool name (visible to the LLM) comes from the function's `__name__`:

```python
# agent.py imports
from src.orchestrator_tools import (
    research_topic as orch_research_topic,       # LLM sees: research_topic
    extract_category as orch_extract_category,   # LLM sees: extract_category
    cross_reference as orch_cross_reference,     # LLM sees: cross_reference
    discover_zones as orch_discover_zones,       # LLM sees: discover_zones
    summarize_content as orch_summarize_content, # LLM sees: summarize_content
    crawl_webpage as orch_crawl_webpage,         # LLM sees: crawl_webpage
)
```

### 2.9 Prompt File Reuse

Orchestrator tools reuse existing prompt templates. The `load_prompt(__file__, name)` calls resolve to the same `prompts/` directory:

| Tool | Prompt | Notes |
|------|--------|-------|
| `research_topic` | `prompts/research_zone.md` | Same template, same `{zone_name}` and `{instructions}` placeholders |
| `extract_category` | `prompts/extract_zone.md`, `extract_npcs.md`, etc. | Same per-category templates |
| `cross_reference` | `prompts/cross_reference_task.md` | Unchanged |
| `discover_zones` | `prompts/discover_zones.md` | Unchanged |
| `summarize_content` | N/A — calls MCP directly | No prompt file needed |
| `crawl_webpage` | N/A — calls REST API directly | No prompt file needed |

**However**, `load_prompt(__file__, name)` resolves relative to the calling file. Since orchestrator_tools.py is in `src/`, but prompts are in `prompts/`, the `load_prompt` call must use the agent root path. The tool functions receive this indirectly — the prompt files are found via the path of `agent.py` (which is one directory up from `src/`). To handle this, orchestrator_tools.py should import and use the same `load_prompt` with an explicit base path, or the prompts can be loaded by the LoreResearcher and stored in the context. The simplest approach: pass the agent's `__file__` reference through OrchestratorContext so tools can load prompts.

Add to `OrchestratorContext`:

```python
agent_file: str  # __file__ from agent.py, for load_prompt resolution
```

Tools use: `load_prompt(ctx.deps.agent_file, "research_zone")`

---

## 3. Daemon-Orchestrator Integration

### 3.1 Interface Change

**Old:**
```python
checkpoint = await run_pipeline(checkpoint, researcher, publish_fn, skip_steps, on_step_progress)
```

**New:**
```python
result = await researcher.research_zone(zone_name, skip_discovery=is_last_wave)
```

### 3.2 Packaging Functions (moved from pipeline.py)

Two functions move to daemon.py as private helpers. Logic is unchanged:

**`_compute_quality_warnings(extraction: ZoneExtraction) -> list[str]`**
- `shallow_narrative_arc`: zone.narrative_arc < 200 chars
- `no_npc_personality_data`: all NPCs have empty personality
- `missing_antagonists`: zone mentions dungeon/raid but has no antagonist NPC or hostile faction

**`_apply_confidence_caps(extraction: ZoneExtraction, confidence: dict[str, float]) -> dict[str, float]`**
- If no NPCs: cap npcs confidence to 0.2
- If >50% NPCs missing personality or role: cap to 0.4
- If no factions: cap factions confidence to 0.2

### 3.3 Package Assembly

New private method on Daemon:

```python
def _assemble_package(
    self,
    result: OrchestratorResult,
    zone_name: str,
) -> ResearchPackage:
    """Assemble ResearchPackage from orchestrator output.

    Applies mechanical quality gates (code decisions, not LLM decisions):
    quality warnings based on content thresholds, confidence caps based
    on field completeness.
    """
    extraction = ZoneExtraction(
        zone=result.zone_data or ZoneData(name=zone_name),
        npcs=result.npcs,
        factions=result.factions,
        lore=result.lore,
        narrative_items=result.narrative_items,
    )

    warnings = _compute_quality_warnings(extraction)

    confidence = result.cross_ref_result.confidence if result.cross_ref_result else {}
    confidence = _apply_confidence_caps(extraction, confidence)

    conflicts = result.cross_ref_result.conflicts if result.cross_ref_result else []

    return ResearchPackage(
        zone_name=zone_name,
        zone_data=extraction.zone,
        npcs=extraction.npcs,
        factions=extraction.factions,
        lore=extraction.lore,
        narrative_items=extraction.narrative_items,
        sources=result.sources,
        confidence=confidence,
        conflicts=conflicts,
        quality_warnings=warnings,
    )
```

### 3.4 Simplified Wave Loop

The `_execute_job` method simplifies significantly. Per-zone processing:

```python
for zone_name in current_wave:
    is_last_wave = current_depth >= max_depth

    # 1. Publish ZONE_STARTED
    await self._publish_status(JobStatusUpdate(
        job_id=job.job_id,
        status=JobStatus.ZONE_STARTED,
        zone_name=zone_name,
        zones_completed=len(zones_completed),
        zones_total=zones_total,
    ))

    try:
        # 2. Run orchestrator
        result = await researcher.research_zone(
            zone_name, skip_discovery=is_last_wave,
        )

        # 3. Track tokens + persist budget
        budget = add_tokens_used(budget, researcher.zone_tokens)
        researcher.reset_zone_state()
        await save_budget(budget)

        # 4. Package + publish
        package = self._assemble_package(result, zone_name)
        envelope = MessageEnvelope(
            source_agent=AGENT_ID,
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
            payload=package.model_dump(mode="json"),
        )
        await publish_fn(envelope)

        # 5. Token observability log
        logger.info("zone_tokens", extra={
            "zone_name": zone_name,
            "total_tokens": result.orchestrator_tokens + result.worker_tokens,
            "orchestrator_tokens": result.orchestrator_tokens,
            "worker_tokens": result.worker_tokens,
        })

        # 6. Zone completed
        zones_completed.append(zone_name)

        # 7. Next wave expansion
        if not is_last_wave:
            for z in result.discovered_zones:
                if z not in zones_completed and z not in next_wave:
                    next_wave.append(z)

        # 8. Publish ZONE_COMPLETED
        await self._publish_status(JobStatusUpdate(
            job_id=job.job_id,
            status=JobStatus.ZONE_COMPLETED,
            zone_name=zone_name,
            zones_completed=len(zones_completed),
            zones_total=zones_total,
        ))

    except Exception as exc:
        logger.error("zone_failed", extra={
            "job_id": job.job_id, "zone": zone_name,
        }, exc_info=True)
        budget = add_tokens_used(budget, researcher.zone_tokens)
        researcher.reset_zone_state()
        await save_budget(budget)
        zones_failed_list.append(ZoneFailure(
            zone_name=zone_name, error=str(exc),
        ))
```

### 3.5 Removed Daemon Logic

| Removed | Reason |
|---------|--------|
| Checkpoint creation/loading/saving per zone | No checkpointing initially _(out of scope)_ |
| `_cleanup_job_checkpoints()` method | No checkpoints to clean up |
| Crash recovery scanning (existing_keys, recovered_checkpoints) | No checkpoints to recover from |
| `on_step_progress` callback construction | No pipeline steps; fine-grained progress deferred _(WO-4)_ |
| `TOTAL_STEPS` constant | No pipeline steps |
| `from src.pipeline import PIPELINE_STEPS, run_pipeline` | Pipeline.py deleted |
| `skip_steps` logic | Orchestrator decides internally; last-wave handled via prompt |

### 3.6 Kept Daemon Logic

| Kept | Reason |
|------|--------|
| Budget loading, daily reset, exhaustion check | Budget tracking unchanged _(WO-5)_ |
| Token tracking after each zone (`researcher.zone_tokens`) | Same mechanism |
| Wave loop with depth control | Same wave expansion logic _(WO-4)_ |
| Status publishing (ACCEPTED, ZONE_STARTED, ZONE_COMPLETED, JOB_*) | Same lifecycle events minus STEP_PROGRESS |
| RabbitMQ connection, queue declaration, message consume | Unchanged infrastructure |
| Signal handlers, graceful shutdown | Unchanged |
| `_make_publish_fn()` for validator queue | Unchanged |
| Exception handling per zone with `zones_failed_list` | Unchanged |

### 3.7 Crash Behavior (No Checkpointing)

Without checkpointing:
- If the daemon crashes mid-zone: the RabbitMQ message is unacked, gets redelivered on restart, and the entire job restarts from scratch
- Zones already completed in the job get re-researched and re-published
- The validator must handle duplicate packages idempotently (already the case — validator accepts or rejects, no side effects on duplicates)
- This is explicitly acceptable per requirements — checkpoint-based recovery is a future spec

---

## 4. Token Observability

### 4.1 Two-Counter Tracking

Every zone research produces two token counts:

| Counter | Source | Tracks |
|---------|--------|--------|
| `orchestrator_tokens` | `orchestrator.run(prompt).usage().total_tokens` | The orchestrator's own conversation with the LLM — planning decisions, reading tool results, deciding next steps |
| `worker_tokens` | `OrchestratorContext.worker_tokens` (accumulated by tools) | Sum of all worker agent calls — research, extraction, cross-ref, discovery |

Combined: `self._zone_tokens += orchestrator_tokens + context.worker_tokens`

### 4.2 Worker Token Accumulation

Each orchestrator tool increments `deps.worker_tokens` after calling its worker agent:

```python
result = await deps.research_agent.run(prompt, deps=research_ctx, ...)
deps.worker_tokens += result.usage().total_tokens or 0
```

This captures all worker costs regardless of how many times the orchestrator calls each tool.

### 4.3 Structured Log Event

After each zone, the daemon logs:

```python
logger.info("zone_tokens", extra={
    "zone_name": zone_name,
    "total_tokens": result.orchestrator_tokens + result.worker_tokens,
    "orchestrator_tokens": result.orchestrator_tokens,
    "worker_tokens": result.worker_tokens,
})
```

This enables:
- Per-zone cost analysis (which zones are expensive?)
- Orchestrator overhead measurement (how much does coordination cost vs. actual work?)
- Budget planning (average tokens per zone -> daily budget sizing)

### 4.4 No Caps on Orchestrator

Per WO-5, the orchestrator agent runs without `UsageLimits`. Worker agents retain their existing per-call limits as safety nets:

| Agent | Limit | Value |
|-------|-------|-------|
| Research agent | `output_tokens_limit` | `PER_ZONE_TOKEN_BUDGET` (50k) |
| Extraction agents | `output_tokens_limit` | `PER_ZONE_TOKEN_BUDGET * token_share` (5k-15k) |
| Cross-ref agent | `output_tokens_limit` | `PER_ZONE_TOKEN_BUDGET // 2` (25k) |
| Discovery agent | `output_tokens_limit` | `PER_ZONE_TOKEN_BUDGET // 4` (12.5k) |
| **Orchestrator** | **None** | **Uncapped** |

Daily budget tracking at the daemon level (`DAILY_TOKEN_BUDGET`) remains the global safety net.

---

## 5. Error Handling

### 5.1 Worker Tool Failures

If a worker agent call fails (LLM timeout, validation error, MCP unreachable):

1. **Pydantic-ai retries first** — each worker agent has `retries=2`, so transient failures get 2 additional attempts
2. **If retries exhaust** — the tool function raises an exception
3. **Pydantic-ai returns the error to the orchestrator** — the LLM sees the error message as a tool result
4. **Orchestrator decides** — retry the tool, skip it, or continue with partial data

This is a key advantage over the pipeline: the pipeline crashed on any step failure. The orchestrator can adaptively handle failures.

### 5.2 MCP Summarizer Failures

If the MCP Summarizer is unavailable or returns invalid data:
- `summarize_content` returns a failure message ("Summarization failed... content unchanged")
- The orchestrator proceeds with unsummarized content
- `extract_category` works with larger content — extraction agents handle it, potentially with slightly lower quality
- This matches the current pipeline's fallback behavior (truncate, not crash)

### 5.3 Orchestrator-Level Failure

If the orchestrator's own LLM conversation fails:
- The exception propagates from `self._orchestrator.run()` through `research_zone()` to the daemon
- The daemon catches it in the zone processing `try/except` block
- The zone is marked as failed (`zones_failed_list`)
- Partial token budget is saved
- The job continues with remaining zones

### 5.4 Missing Data Validation

After `research_zone()` returns, `_assemble_package` handles incomplete results:
- `result.zone_data is None` → uses `ZoneData(name=zone_name)` as fallback (empty zone)
- `result.cross_ref_result is None` → empty confidence dict and no conflicts
- Empty lists for npcs/factions/lore/narrative_items → valid (some zones genuinely have sparse data)

---

## 6. Configuration Changes

### 6.1 Topic Accessor Functions (moved to config.py)

The three topic accessor functions move from pipeline.py to config.py alongside the existing `load_research_topics()`:

```python
# config.py additions

_TOPICS_CONFIG = load_research_topics()["topics"]


def get_topic_instructions(topic_key: str) -> str:
    """Return the research instructions template for a topic."""
    return _TOPICS_CONFIG[topic_key]["instructions"]


def get_topic_section_header(topic_key: str) -> str:
    """Return the section header for a topic."""
    return _TOPICS_CONFIG[topic_key]["section_header"]


def get_topic_schema_hints(topic_key: str) -> str:
    """Return the schema hints for a topic."""
    return _TOPICS_CONFIG[topic_key]["schema_hints"]
```

### 6.2 No New Environment Variables

The orchestrator uses the same `LLM_MODEL`, `MCP_WEB_SEARCH_URL`, `MCP_SUMMARIZER_URL`, and all other config from config.py. No new env vars needed.

---

## Files Changed

### Deleted

| File | Reason |
|------|--------|
| `src/pipeline.py` | Replaced by orchestrator. All step functions, `PIPELINE_STEPS`, `STEP_FUNCTIONS`, `run_pipeline()` removed. _(WO-3)_ |
| `tests/test_pipeline.py` | Tests for deleted pipeline. Replaced by orchestrator tool tests. _(WO-3)_ |

### New

| File | Purpose |
|------|---------|
| `src/orchestrator_tools.py` | Tool functions for the orchestrator: `research_topic`, `extract_category`, `cross_reference`, `discover_zones`, `summarize_content`, `crawl_webpage`. _(WO-2)_ |
| `prompts/orchestrator_system.md` | System prompt — orchestrator persona, tools, workflow, constraints. _(WO-1)_ |
| `prompts/orchestrator_task.md` | Per-zone task template — `{zone_name}`, `{game_name}`, `{skip_discovery}`. _(WO-1)_ |
| `tests/test_orchestrator_tools.py` | Unit tests for all orchestrator tool functions. _(WO-2)_ |

### Modified

| File | Change |
|------|--------|
| `src/agent.py` | Add `OrchestratorContext` and `OrchestratorResult` dataclasses. Add orchestrator agent construction and tool registration in `__init__`. Rewrite `research_zone()` to use orchestrator (new signature: `zone_name, skip_discovery` -> `OrchestratorResult`). Remove old facade methods: `extract_category()`, `cross_reference()`, `discover_connected_zones()`. Keep `ResearchContext`, `EXTRACTION_CATEGORIES`, worker agent construction, `zone_tokens`, `reset_zone_state()`. _(WO-1, WO-2)_ |
| `src/daemon.py` | Replace `run_pipeline()` call with `researcher.research_zone()`. Add `_assemble_package()` method. Move `_compute_quality_warnings()` and `_apply_confidence_caps()` from pipeline.py. Add `zone_tokens` structured log event. Remove checkpoint logic (creation, loading, saving, cleanup, crash recovery scanning). Remove step progress callback. Remove `TOTAL_STEPS`. Remove pipeline import. Simplify wave loop. _(WO-3, WO-4, WO-5)_ |
| `src/config.py` | Add topic accessor functions (`get_topic_instructions`, `get_topic_section_header`, `get_topic_schema_hints`) and module-level `_TOPICS_CONFIG` — moved from pipeline.py. _(WO-3, D11)_ |
| `src/models.py` | Remove `ResearchResult` (unused after pipeline elimination — was only used by old `research_zone()` return). All other models unchanged. _(WO-6)_ |
| `tests/test_agent.py` | Rewrite tests for new `research_zone()` API (returns `OrchestratorResult`, takes `skip_discovery`). Remove tests for `extract_category()`, `cross_reference()`, `discover_connected_zones()`. Add tests for `OrchestratorContext` and `OrchestratorResult` construction. _(WO-1)_ |
| `tests/test_daemon.py` | Update tests: remove pipeline-related assertions, add tests for `_assemble_package()`, `_compute_quality_warnings()`, `_apply_confidence_caps()`. Update zone processing flow assertions. _(WO-4)_ |
| `tests/test_config.py` | Add tests for new topic accessor functions. _(D11)_ |

### Unchanged

| File | Reason |
|------|--------|
| `src/tools.py` | Existing `crawl_webpage` for research worker agent — unchanged |
| `src/mcp_client.py` | `mcp_call` and `crawl_url` — still used by orchestrator tools and research worker |
| `src/checkpoint.py` | Budget functions still used. Per-zone checkpoint functions dormant. _(D9)_ |
| `src/logging_config.py` | No changes |
| `config/mcp_config.json` | Same MCP servers |
| `config/research_topics.yml` | Still used by orchestrator tools via config accessors _(WO-3)_ |
| `config/sources.yml` | Unchanged |
| All existing prompt files | Reused by worker agents and orchestrator tools |

---

## Future Work (Out of Scope)

- **Checkpointing** — orchestrator crash resilience. If it crashes mid-zone, zone restarts. Future spec adds checkpoint-based recovery.
- **Token caps on orchestrator** — observe actual per-zone cost, finetune prompts, then cap. Worker safety nets stay as-is.
- **Fine-grained step progress** — daemon reports ZONE_STARTED/ZONE_COMPLETED only. Per-tool progress events deferred.
- **Prompt optimization** — orchestrator and worker prompts need tuning after observing real runs. Iterative, not spec'd.
- **Multi-zone parallelism** — zones process sequentially within a wave. Parallel zone research is a future optimization.
- **Validator changes** — identical ResearchPackage schema, no validator impact.
