"""Pydantic AI agent — the LLM-powered research brain.

Provides structured extraction from raw crawled content using LLM,
and cross-reference validation for consistency checking.
"""

from __future__ import annotations

from contextlib import AsyncExitStack

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from shared.config_loader import load_mcp_config
from shared.prompt_loader import load_prompt

from src.config import (
    LLM_MODEL,
    PER_CYCLE_TOKEN_BUDGET,
)
from src.models import (
    Conflict,
    FactionData,
    LoreData,
    NPCData,
    NarrativeItemData,
    SourceReference,
    ZoneData,
)


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


class LoreResearcher:

    AGENT_ID = "world_lore_researcher"

    def __init__(self):
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

        self._mcp_servers = load_mcp_config(__file__)

        self._research_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            toolsets=self._mcp_servers,
            retries=2,
        )

    async def extract_zone_data(
        self,
        zone_name: str,
        raw_content: list[str],
        sources: list[SourceReference],
    ) -> ZoneExtraction:
        source_info = "\n".join(
            f"- {s.url} (tier: {s.tier.value})" for s in sources
        )
        template = load_prompt(__file__, "extract_zone_data")
        prompt = template.format(
            zone_name=zone_name,
            source_info=source_info,
            raw_content="\n\n---\n\n".join(raw_content[:5]),
        )

        result = await self._extraction_agent.run(
            prompt,
            usage_limits=UsageLimits(response_tokens_limit=PER_CYCLE_TOKEN_BUDGET),
        )
        return result.output

    async def cross_reference(
        self,
        extraction: ZoneExtraction,
    ) -> CrossReferenceResult:
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
            usage_limits=UsageLimits(response_tokens_limit=PER_CYCLE_TOKEN_BUDGET // 2),
        )
        return result.output

    async def research_zone(self, zone_name: str, instructions: str = "") -> str:
        template = load_prompt(__file__, "research_zone")
        prompt = template.format(
            zone_name=zone_name,
            instructions=instructions,
        )

        async with AsyncExitStack() as stack:
            for server in self._mcp_servers:
                await stack.enter_async_context(server)
            result = await self._research_agent.run(
                prompt,
                usage_limits=UsageLimits(response_tokens_limit=PER_CYCLE_TOKEN_BUDGET),
            )
        return result.output

