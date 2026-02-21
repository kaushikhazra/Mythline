"""Pydantic AI agent — the LLM-powered research brain.

Provides structured extraction from raw crawled content using LLM,
and cross-reference validation for consistency checking.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

from src.config import (
    LLM_MODEL,
    MCP_WEB_CRAWLER_URL,
    MCP_WEB_SEARCH_URL,
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

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8")


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
        model_name = f"openrouter:{LLM_MODEL}"

        self._extraction_agent = Agent(
            model_name,
            system_prompt=_load_prompt("system_prompt"),
            output_type=ZoneExtraction,
            retries=2,
        )

        self._cross_ref_agent = Agent(
            model_name,
            system_prompt=_load_prompt("cross_reference"),
            output_type=CrossReferenceResult,
            retries=2,
        )

        self._search_server = MCPServerStreamableHTTP(
            MCP_WEB_SEARCH_URL,
            tool_prefix="search",
            timeout=30,
        )
        self._crawler_server = MCPServerStreamableHTTP(
            MCP_WEB_CRAWLER_URL,
            tool_prefix="crawler",
            timeout=60,
        )

        self._research_agent = Agent(
            model_name,
            system_prompt=_load_prompt("system_prompt"),
            toolsets=[self._search_server, self._crawler_server],
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
        prompt = (
            f"Extract all structured lore data for the zone '{zone_name}' "
            f"from the following raw content.\n\n"
            f"Sources used (prefer higher-tier sources for conflicts):\n{source_info}\n\n"
            f"--- RAW CONTENT ---\n\n"
            + "\n\n---\n\n".join(raw_content[:5])
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
        prompt = (
            f"Cross-reference the following extracted lore data for consistency.\n"
            f"Check for contradictions between NPCs, factions, lore entries, and zone info.\n"
            f"Assign confidence scores (0.0-1.0) per category.\n\n"
            f"Zone: {extraction.zone.name}\n"
            f"NPCs: {len(extraction.npcs)}\n"
            f"Factions: {len(extraction.factions)}\n"
            f"Lore entries: {len(extraction.lore)}\n"
            f"Narrative items: {len(extraction.narrative_items)}\n\n"
            f"Full data:\n{extraction.model_dump_json(indent=2)}"
        )

        result = await self._cross_ref_agent.run(
            prompt,
            usage_limits=UsageLimits(response_tokens_limit=PER_CYCLE_TOKEN_BUDGET // 2),
        )
        return result.output

    async def research_zone(self, zone_name: str, instructions: str = "") -> str:
        prompt = (
            f"Research the zone '{zone_name}' using your web search and crawler tools. "
            f"Find comprehensive lore information including NPCs, factions, history, "
            f"and notable items. {instructions}"
        )

        async with self._search_server, self._crawler_server:
            result = await self._research_agent.run(
                prompt,
                usage_limits=UsageLimits(response_tokens_limit=PER_CYCLE_TOKEN_BUDGET),
            )
        return result.output

