"""Pydantic AI agent — the LLM-powered research brain.

Provides autonomous web research (search + crawl), structured extraction
from raw content using LLM, cross-reference validation, and zone discovery.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from shared.config_loader import load_mcp_config
from shared.prompt_loader import load_prompt

from src.config import (
    GAME_NAME,
    LLM_MODEL,
    PER_ZONE_TOKEN_BUDGET,
    get_source_tier_for_domain,
)
from src.mcp_client import crawl_url as rest_crawl_url
from src.models import (
    Conflict,
    FactionData,
    LoreData,
    NPCData,
    NarrativeItemData,
    SourceReference,
    SourceTier,
    ZoneData,
)


# --- Constants ---

CRAWL_CONTENT_TRUNCATE_CHARS = 5000
MAX_RAW_CONTENT_BLOCKS = 10

# --- Agent output models ---


class ZoneExtraction(BaseModel):
    zone: ZoneData
    npcs: list[NPCData] = Field(default_factory=list)
    factions: list[FactionData] = Field(default_factory=list)
    lore: list[LoreData] = Field(default_factory=list)
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)


class CrossReferenceResult(BaseModel):
    is_consistent: bool = True
    conflicts: list[Conflict] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ResearchResult(BaseModel):
    """Returned by research_zone() — raw crawled content + source references."""
    raw_content: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    summary: str = ""


class ConnectedZonesResult(BaseModel):
    """Returned by _zone_discovery_agent — slugified zone names."""
    zone_slugs: list[str] = Field(default_factory=list)


# --- Research context (deps for _research_agent tool) ---


@dataclass
class ResearchContext:
    """Accumulates raw content and sources during a research_zone() run.

    The custom crawl tool appends here so that pipeline gets full content
    without relying on the agent's text output.
    """
    raw_content: list[str] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)


# --- Helpers ---


def _make_source_ref(url: str) -> SourceReference:
    """Build a SourceReference from a URL, looking up the domain's trust tier."""
    domain = urlparse(url).netloc
    tier_name = get_source_tier_for_domain(domain)
    try:
        tier = SourceTier(tier_name) if tier_name else SourceTier.TERTIARY
    except ValueError:
        tier = SourceTier.TERTIARY
    return SourceReference(url=url, domain=domain, tier=tier)


# --- Agent class ---


class LoreResearcher:

    AGENT_ID = "world_lore_researcher"

    def __init__(self):
        self._zone_tokens: int = 0
        self._mcp_servers = load_mcp_config(__file__)

        self._extraction_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            output_type=ZoneExtraction,
            retries=2,
        )

        self._cross_ref_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "cross_reference"),
            output_type=CrossReferenceResult,
            retries=2,
        )

        self._research_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            deps_type=ResearchContext,
            toolsets=self._mcp_servers,
            retries=2,
        )

        # Register crawl4ai REST wrapper as a Pydantic AI tool.
        # The agent can call this to fetch full page content from URLs
        # it discovers via web search MCP.
        @self._research_agent.tool
        async def crawl_webpage(
            ctx: RunContext[ResearchContext], url: str
        ) -> str:
            """Crawl a URL and extract its full content as markdown.

            Use this after finding interesting URLs via web search to get
            the complete page content for lore extraction.
            """
            result = await rest_crawl_url(url)
            content = result.get("content")
            if content:
                ctx.deps.raw_content.append(content)
                ctx.deps.sources.append(_make_source_ref(url))
                # Return truncated content to the agent's context window
                if len(content) > CRAWL_CONTENT_TRUNCATE_CHARS:
                    return content[:CRAWL_CONTENT_TRUNCATE_CHARS] + "\n\n[... content truncated, full version captured ...]"
                return content
            error = result.get("error", "unknown error")
            return f"Failed to crawl {url}: {error}"

        self._zone_discovery_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "discover_zones_system"),
            output_type=ConnectedZonesResult,
            toolsets=self._mcp_servers,
            retries=2,
        )

    @property
    def zone_tokens(self) -> int:
        """Total tokens used since last reset."""
        return self._zone_tokens

    def reset_zone_tokens(self) -> None:
        """Reset the per-zone token counter."""
        self._zone_tokens = 0

    async def research_zone(
        self, zone_name: str, instructions: str = ""
    ) -> ResearchResult:
        """Run the research agent to search and crawl for a topic.

        The agent autonomously calls web search MCP and crawl_webpage tool.
        Raw content and sources are captured via ResearchContext deps.
        """
        template = load_prompt(__file__, "research_zone")
        prompt = template.format(
            zone_name=zone_name,
            instructions=instructions,
        )

        context = ResearchContext()

        async with AsyncExitStack() as stack:
            for server in self._mcp_servers:
                await stack.enter_async_context(server)
            result = await self._research_agent.run(
                prompt,
                deps=context,
                usage_limits=UsageLimits(
                    response_tokens_limit=PER_ZONE_TOKEN_BUDGET
                ),
            )

        self._zone_tokens += result.usage().total_tokens or 0

        return ResearchResult(
            raw_content=context.raw_content,
            sources=context.sources,
            summary=result.output,
        )

    async def extract_zone_data(
        self,
        zone_name: str,
        raw_content: list[str],
        sources: list[SourceReference],
    ) -> ZoneExtraction:
        """Extract structured lore data from raw crawled content."""
        source_info = "\n".join(
            f"- {s.url} (tier: {s.tier.value})" for s in sources
        )
        template = load_prompt(__file__, "extract_zone_data")
        prompt = template.format(
            zone_name=zone_name,
            source_info=source_info,
            raw_content="\n\n---\n\n".join(raw_content[:MAX_RAW_CONTENT_BLOCKS]),
        )

        result = await self._extraction_agent.run(
            prompt,
            usage_limits=UsageLimits(
                response_tokens_limit=PER_ZONE_TOKEN_BUDGET
            ),
        )
        self._zone_tokens += result.usage().total_tokens or 0
        return result.output

    async def cross_reference(
        self,
        extraction: ZoneExtraction,
    ) -> CrossReferenceResult:
        """Cross-reference all extracted data for consistency."""
        template = load_prompt(__file__, "cross_reference_task")
        prompt = template.format(
            zone_name=extraction.zone.name,
            npc_count=len(extraction.npcs),
            faction_count=len(extraction.factions),
            lore_count=len(extraction.lore),
            narrative_item_count=len(extraction.narrative_items),
            full_data=extraction.model_dump_json(indent=2),
        )

        result = await self._cross_ref_agent.run(
            prompt,
            usage_limits=UsageLimits(
                response_tokens_limit=PER_ZONE_TOKEN_BUDGET // 2
            ),
        )
        self._zone_tokens += result.usage().total_tokens or 0
        return result.output

    async def discover_connected_zones(self, zone_name: str) -> list[str]:
        """Search for zones connected to the given zone, return slugified names."""
        template = load_prompt(__file__, "discover_zones")
        prompt = template.format(
            zone_name=zone_name.replace("_", " "),
            game_name=GAME_NAME,
        )

        async with AsyncExitStack() as stack:
            for server in self._mcp_servers:
                await stack.enter_async_context(server)
            result = await self._zone_discovery_agent.run(
                prompt,
                usage_limits=UsageLimits(
                    response_tokens_limit=PER_ZONE_TOKEN_BUDGET // 4
                ),
            )

        self._zone_tokens += result.usage().total_tokens or 0
        return result.output.zone_slugs
