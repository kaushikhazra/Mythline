"""Pydantic AI agent — the LLM-powered research brain.

Manages an orchestrator agent that coordinates worker sub-agents for
autonomous web research, structured extraction, cross-reference
validation, and zone discovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from shared.prompt_loader import load_prompt

from src.config import GAME_NAME, LLM_MODEL
from src.models import (
    ConnectedZonesResult,
    CrossReferenceResult,
    FactionData,
    FactionExtractionResult,
    LoreData,
    LoreExtractionResult,
    NPCData,
    NPCExtractionResult,
    NarrativeItemData,
    NarrativeItemExtractionResult,
    SourceReference,
    ZoneData,
)
from src.orchestrator_tools import (
    crawl_webpage as orch_crawl_webpage,
    cross_reference as orch_cross_reference,
    discover_zones as orch_discover_zones,
    extract_category as orch_extract_category,
    research_topic as orch_research_topic,
    summarize_content as orch_summarize_content,
)
from src.tools import crawl_webpage, search_news, search_web


# ---------------------------------------------------------------------------
# Extraction category wiring
# ---------------------------------------------------------------------------

# Maps category key -> (output_type, prompt_name, token_budget_share)
EXTRACTION_CATEGORIES: dict[str, tuple[type[BaseModel], str, float]] = {
    "zone": (ZoneData, "extract_zone", 0.10),
    "npcs": (NPCExtractionResult, "extract_npcs", 0.30),
    "factions": (FactionExtractionResult, "extract_factions", 0.25),
    "lore": (LoreExtractionResult, "extract_lore", 0.25),
    "narrative_items": (NarrativeItemExtractionResult, "extract_narrative_items", 0.10),
}


# ---------------------------------------------------------------------------
# Research context (deps for _research_agent tool)
# ---------------------------------------------------------------------------


@dataclass
class ResearchContext:
    """Accumulates raw content and sources during a worker research run.

    The custom crawl tool appends here so that the orchestrator tool gets
    full content without relying on the agent's text output. The crawl_cache
    is shared across multiple research calls within the same zone for URL dedup.
    """
    raw_content: list[str] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)
    crawl_cache: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator context and result (deps for _orchestrator agent)
# ---------------------------------------------------------------------------


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
    agent_file: str

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


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class LoreResearcher:
    """LLM-powered lore research agent.

    Manages an orchestrator agent that coordinates worker sub-agents:
    - _orchestrator: central LLM agent with worker tools (NEW)
    - _research_agent: autonomous search + crawl (with MCP toolsets)
    - _extraction_agents: per-category structured extraction (5 agents)
    - _cross_ref_agent: cross-reference validation
    - _zone_discovery_agent: connected zone discovery (with MCP toolsets)
    """

    AGENT_ID = "world_lore_researcher"

    def __init__(self):
        self._zone_tokens: int = 0
        self._crawl_cache: dict[str, str] = {}

        # --- Worker agents ---

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

        # Research and discovery agents use plain function tools for web
        # search instead of MCP toolsets. MCP toolsets create anyio cancel
        # scope lifecycles that conflict with the outer orchestrator's task
        # group when these agents run inside orchestrator tool functions.
        self._research_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            deps_type=ResearchContext,
            retries=2,
        )
        self._research_agent.tool(crawl_webpage)
        self._research_agent.tool(search_web)
        self._research_agent.tool(search_news)

        self._zone_discovery_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "discover_zones_system"),
            output_type=ConnectedZonesResult,
            retries=2,
        )
        self._zone_discovery_agent.tool(search_web)
        self._zone_discovery_agent.tool(search_news)

        # --- Orchestrator agent (NEW) ---

        self._orchestrator = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "orchestrator_system"),
            deps_type=OrchestratorContext,
            retries=2,
        )
        self._orchestrator.tool(orch_research_topic)
        self._orchestrator.tool(orch_extract_category)
        self._orchestrator.tool(orch_cross_reference)
        self._orchestrator.tool(orch_discover_zones)
        self._orchestrator.tool(orch_summarize_content)
        self._orchestrator.tool(orch_crawl_webpage)

    @property
    def zone_tokens(self) -> int:
        """Total tokens used since last reset."""
        return self._zone_tokens

    def reset_zone_state(self) -> None:
        """Reset per-zone state: token counter and crawl cache."""
        self._zone_tokens = 0
        self._crawl_cache.clear()

    async def research_zone(
        self, zone_name: str, skip_discovery: bool = False
    ) -> OrchestratorResult:
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
            agent_file=__file__,
            zone_name=zone_name,
            game_name=GAME_NAME,
            crawl_cache=self._crawl_cache,
        )

        result = await self._orchestrator.run(
            prompt,
            deps=context,
            usage_limits=UsageLimits(request_limit=75),
        )

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
