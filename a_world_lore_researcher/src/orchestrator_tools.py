"""Orchestrator tool functions — registered on the orchestrator agent.

Each tool delegates to a worker agent (research, extraction, cross-ref,
discovery) or external service (MCP Summarizer, crawl4ai). Structured
results accumulate in OrchestratorContext deps; the orchestrator LLM
only sees brief text summaries.

Worker agent calls are wrapped in asyncio.create_task() to isolate their
anyio cancel scopes from the outer orchestrator's task group. Without this,
pydantic-ai's nested agent.run() pushes cancel scopes onto the same stack
as the outer agent, causing interleaved scope cleanup failures.
"""

import asyncio

from pydantic_ai import RunContext
from pydantic_ai.usage import UsageLimits

from shared.prompt_loader import load_prompt

from src.config import (
    CRAWL_CONTENT_TRUNCATE_CHARS,
    MCP_SUMMARIZER_URL,
    PER_ZONE_TOKEN_BUDGET,
    get_topic_instructions,
    get_topic_schema_hints,
    get_topic_section_header,
)
from src.mcp_client import crawl_url as rest_crawl_url, mcp_call
from src.models import ZoneExtraction
from src.tools import make_source_ref, normalize_url


# ---------------------------------------------------------------------------
# Category-to-topic mapping
# ---------------------------------------------------------------------------

CATEGORY_TO_TOPIC = {
    "zone": "zone_overview_research",
    "npcs": "npc_research",
    "factions": "faction_research",
    "lore": "lore_research",
    "narrative_items": "narrative_items_research",
}


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


async def research_topic(ctx: RunContext, topic: str) -> str:
    """Research a specific topic for the current zone.

    Searches the web and crawls pages for a specific aspect of the zone.
    Content is accumulated internally.

    Args:
        topic: One of: zone_overview_research, npc_research, faction_research,
               lore_research, narrative_items_research
    """
    from src.agent import ResearchContext

    deps = ctx.deps

    instructions = get_topic_instructions(topic).format(
        zone=deps.zone_name.replace("_", " "),
        game=deps.game_name,
    )

    template = load_prompt(deps.agent_file, "research_zone")
    prompt = template.format(
        zone_name=deps.zone_name.replace("_", " "),
        instructions=instructions,
    )

    research_ctx = ResearchContext(crawl_cache=deps.crawl_cache)

    result = await asyncio.create_task(deps.research_agent.run(
        prompt,
        deps=research_ctx,
        usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET, request_limit=75),
    ))

    deps.research_content.setdefault(topic, []).extend(research_ctx.raw_content)
    deps.sources.extend(research_ctx.sources)
    deps.worker_tokens += result.usage().total_tokens or 0

    content_chars = sum(len(c) for c in research_ctx.raw_content)
    return (
        f"Researched {topic}: {len(research_ctx.raw_content)} content blocks "
        f"({content_chars:,} chars), {len(research_ctx.sources)} sources"
    )


async def extract_category(ctx: RunContext, category: str) -> str:
    """Extract structured data for one category from accumulated research content.

    Reads accumulated content for the corresponding topic internally.
    Must be called after researching the relevant topic.

    Args:
        category: One of: zone, npcs, factions, lore, narrative_items
    """
    from src.agent import EXTRACTION_CATEGORIES

    deps = ctx.deps
    topic = CATEGORY_TO_TOPIC[category]

    content_blocks = deps.research_content.get(topic, [])
    if not content_blocks:
        return f"No research content for category '{category}' (topic '{topic}'). Research first."

    header = get_topic_section_header(topic)
    content = f"{header}\n\n" + "\n\n".join(content_blocks)

    _, prompt_name, token_share = EXTRACTION_CATEGORIES[category]
    source_info = "\n".join(f"- {s.url} (tier: {s.tier.value})" for s in deps.sources)
    template = load_prompt(deps.agent_file, prompt_name)
    prompt = template.format(
        zone_name=deps.zone_name,
        source_info=source_info,
        raw_content=content,
    )

    agent = deps.extraction_agents[category]
    budget = int(PER_ZONE_TOKEN_BUDGET * token_share)
    result = await asyncio.create_task(agent.run(
        prompt,
        usage_limits=UsageLimits(output_tokens_limit=budget, request_limit=75),
    ))
    deps.worker_tokens += result.usage().total_tokens or 0

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


async def cross_reference(ctx: RunContext) -> str:
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

    template = load_prompt(deps.agent_file, "cross_reference_task")
    prompt = template.format(
        zone_name=extraction.zone.name,
        npc_count=len(extraction.npcs),
        faction_count=len(extraction.factions),
        lore_count=len(extraction.lore),
        narrative_item_count=len(extraction.narrative_items),
        full_data=extraction.model_dump_json(indent=2),
    )

    result = await asyncio.create_task(deps.cross_ref_agent.run(
        prompt,
        usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET // 2, request_limit=75),
    ))
    deps.worker_tokens += result.usage().total_tokens or 0
    deps.cross_ref_result = result.output

    return (
        f"Cross-reference complete: consistent={result.output.is_consistent}, "
        f"{len(result.output.conflicts)} conflicts, "
        f"confidence: {result.output.confidence}"
    )


async def discover_zones(ctx: RunContext) -> str:
    """Discover zones connected to the current zone for wave expansion."""
    deps = ctx.deps
    zone_display = deps.zone_name.replace("_", " ")

    template = load_prompt(deps.agent_file, "discover_zones")
    prompt = template.format(zone_name=zone_display, game_name=deps.game_name)

    result = await asyncio.create_task(deps.discovery_agent.run(
        prompt,
        usage_limits=UsageLimits(output_tokens_limit=PER_ZONE_TOKEN_BUDGET // 4, request_limit=75),
    ))

    deps.worker_tokens += result.usage().total_tokens or 0
    deps.discovered_zones = result.output.zone_slugs

    slugs = result.output.zone_slugs
    preview = ", ".join(slugs[:5]) + ("..." if len(slugs) > 5 else "")
    return f"Discovered {len(slugs)} connected zones: {preview}"


async def summarize_content(ctx: RunContext, topic: str) -> str:
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


async def crawl_webpage(ctx: RunContext, url: str) -> str:
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
