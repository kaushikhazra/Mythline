"""9-step research pipeline for zone-level lore extraction.

Each step is checkpointed for crash resilience. The pipeline runs for
a single zone and produces a ResearchPackage for the validator.

Steps 1-5: Per-topic research (agent searches + crawls autonomously).
Step 6: Single extraction (all raw content -> structured Pydantic models).
Step 7: Cross-reference (consistency check + confidence scores).
Step 8: Discover connected zones (populate progression queue).
Step 9: Package and send (assemble ResearchPackage, publish to RabbitMQ).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import cast

from src.agent import (
    CrossReferenceResult,
    FactionExtractionResult,
    LoreExtractionResult,
    LoreResearcher,
    NPCExtractionResult,
    NarrativeItemExtractionResult,
    ResearchResult,
    ZoneExtraction,
)
from src.checkpoint import save_checkpoint
from src.config import AGENT_ID, GAME_NAME, MCP_SUMMARIZER_URL
from src.mcp_client import mcp_call
from src.models import (
    FactionStance,
    MessageEnvelope,
    MessageType,
    ResearchCheckpoint,
    ResearchPackage,
    SourceReference,
    ZoneData,
)

logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    "zone_overview_research",
    "npc_research",
    "faction_research",
    "lore_research",
    "narrative_items_research",
    "extract_all",
    "cross_reference",
    "discover_connected_zones",
    "package_and_send",
]


async def run_pipeline(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable[[MessageEnvelope], Awaitable[None]] | None = None,
    skip_steps: set[str] | None = None,
    on_step_progress: Callable[[str, int, int], Awaitable[None]] | None = None,
) -> ResearchCheckpoint:
    """Run the research pipeline for a single zone.

    Args:
        checkpoint: Current research state (supports resume from any step).
        researcher: LoreResearcher instance with agent + tools.
        publish_fn: Async callable to publish MessageEnvelope to RabbitMQ.
                    None in tests or when RabbitMQ is unavailable.
        skip_steps: Step names to skip (logged but not executed).
        on_step_progress: Callback(step_name, step_number, total_steps) called
                          after each step completes. Used for STEP_PROGRESS status.
    """
    zone_name = checkpoint.zone_name
    start_step = checkpoint.current_step
    checkpoint_key = f"{AGENT_ID}:{checkpoint.job_id}:{zone_name}"
    total_steps = len(PIPELINE_STEPS)

    for step_idx in range(start_step, len(PIPELINE_STEPS)):
        step_name = PIPELINE_STEPS[step_idx]

        if skip_steps and step_name in skip_steps:
            logger.info(
                "pipeline_step_skipped",
                extra={"zone_name": zone_name, "step": step_idx + 1, "step_name": step_name},
            )
            checkpoint.current_step = step_idx + 1
            await save_checkpoint(checkpoint, checkpoint_key)
            if on_step_progress:
                await on_step_progress(step_name, step_idx + 1, total_steps)
            continue

        logger.info(
            "pipeline_step_started",
            extra={"zone_name": zone_name, "step": step_idx + 1, "step_name": step_name},
        )

        step_fn = STEP_FUNCTIONS.get(step_name)
        if step_fn:
            checkpoint = await step_fn(checkpoint, researcher, publish_fn)

        checkpoint.current_step = step_idx + 1
        await save_checkpoint(checkpoint, checkpoint_key)
        logger.info(
            "pipeline_step_completed",
            extra={"zone_name": zone_name, "step": step_idx + 1, "step_name": step_name},
        )

        if on_step_progress:
            await on_step_progress(step_name, step_idx + 1, total_steps)

    return checkpoint


# ---------------------------------------------------------------------------
# Helper: accumulate research results into step_data
# ---------------------------------------------------------------------------


def _accumulate_research(
    checkpoint: ResearchCheckpoint, result: ResearchResult, topic_key: str
) -> None:
    """Append raw content + sources from a research run into step_data.

    Each content block is labeled with its topic_key so the extraction
    step can reconstruct section-delimited content for the LLM.
    """
    raw = checkpoint.step_data.get("research_raw_content", [])
    raw.extend({"topic": topic_key, "content": block} for block in result.raw_content)
    checkpoint.step_data["research_raw_content"] = raw

    sources = checkpoint.step_data.get("research_sources", [])
    sources.extend(s.model_dump(mode="json") for s in result.sources)
    checkpoint.step_data["research_sources"] = sources


# ---------------------------------------------------------------------------
# Steps 1-5: Per-topic research (data-driven)
# ---------------------------------------------------------------------------

RESEARCH_TOPICS = {
    "zone_overview_research": (
        "Focus on zone overview for {zone} in {game}.\n\n"
        "Phase 1 — Search for the zone's main wiki page and overview articles. "
        "Extract: level range, expansion era, narrative arc (the FULL story — "
        "political backstory, primary conflict, factional tensions, and resolution, "
        "not just a one-sentence summary), political climate (governing factions, "
        "neglected populations, power struggles), access gating, phase states "
        "(Cataclysm changes, quest progression phases), sub-areas and landmarks.\n\n"
        "Phase 2 — If the zone has a major storyline or dungeon, search for and crawl "
        "the dedicated wiki page for that storyline or dungeon (e.g., 'The Deadmines' "
        "page, not just the zone page that mentions it)."
    ),
    "npc_research": (
        "Focus on NPCs and notable characters in {zone} in {game}.\n\n"
        "Phase 1 — Search for NPC lists, zone quest givers, and notable characters. "
        "Crawl category/overview pages to discover NPC NAMES.\n\n"
        "Phase 2 — For the 10-15 most important NPCs discovered, search for and crawl "
        "each NPC's INDIVIDUAL wiki page. Extract from each page: personality, "
        "motivations, relationships to other NPCs, role (quest giver, vendor, boss, "
        "antagonist, faction leader), quest chains, phased/expansion appearances.\n\n"
        "CRITICAL: Search for BOTH friendly and hostile NPCs:\n"
        "- Quest givers, vendors, flight masters, innkeepers\n"
        "- Dungeon bosses and raid bosses associated with this zone\n"
        "- Antagonist leaders and villain NPCs\n"
        "- Faction leaders (both allied and enemy)\n"
        "Do NOT stop at quest-giver lists. Explicitly search for "
        "'{zone} bosses', '{zone} antagonists', and '{zone} dungeon bosses'."
    ),
    "faction_research": (
        "Focus on factions and organizations in {zone} in {game}.\n\n"
        "Phase 1 — Search for factions active in this zone. Crawl overview pages "
        "to discover faction NAMES.\n\n"
        "Phase 2 — For EVERY named faction discovered, search for and crawl the "
        "faction's INDIVIDUAL wiki page. Extract: ideology, core beliefs, origin "
        "story (how and why the faction formed), goals, key members and leaders, "
        "inter-faction relationships (allied, hostile, neutral — name the specific "
        "factions), hierarchy (parent factions, sub-factions), mutual exclusions.\n\n"
        "CRITICAL: Search for BOTH friendly and hostile factions:\n"
        "- Allied organizations and militia groups\n"
        "- Antagonist factions, criminal organizations, hostile forces\n"
        "- Governing authorities and their local presence\n"
        "Do NOT stop at allied faction pages. Explicitly search for "
        "'{zone} enemy factions', '{zone} hostile organizations'."
    ),
    "lore_research": (
        "Focus on lore, history, mythology, and cosmology of {zone} in {game}.\n\n"
        "Phase 1 — Search for the zone's lore and history articles. Crawl overview "
        "pages to identify major lore EVENTS and FIGURES.\n\n"
        "Phase 2 — For each major lore event or figure, search for and crawl its "
        "INDIVIDUAL wiki page. Extract: what happened, WHY it happened (causes), "
        "what it caused (consequences), named actors involved, era/timeline placement.\n\n"
        "Prioritize causal chains: the sequence of events that created the zone's "
        "current state. Include origin stories for major factions and conflicts."
    ),
    "narrative_items_research": (
        "Focus on narrative items and artifacts in {zone} in {game}.\n\n"
        "Search for legendary items, quest items with story significance, "
        "dungeon loot with narrative context, and artifacts tied to the zone's lore.\n\n"
        "Extract: story arc, wielder lineage, power description, significance tier.\n\n"
        "ONLY include items with genuine narrative significance — NOT crafting recipes, "
        "cooking items, vendor trash, or generic consumables. If the zone has no "
        "truly significant narrative items, that is acceptable — an empty result "
        "is better than padding with irrelevant items."
    ),
}


def _make_research_step(topic_key: str):
    """Factory that returns an async step function for a research topic."""
    template = RESEARCH_TOPICS[topic_key]

    async def step(
        checkpoint: ResearchCheckpoint,
        researcher: LoreResearcher,
        publish_fn: Callable | None = None,
    ) -> ResearchCheckpoint:
        zone_name = checkpoint.zone_name.replace("_", " ")
        instructions = template.format(zone=zone_name, game=GAME_NAME)
        result = await researcher.research_zone(zone_name, instructions=instructions)
        _accumulate_research(checkpoint, result, topic_key)
        return checkpoint

    step.__name__ = f"step_{topic_key}"
    return step


step_zone_overview_research = _make_research_step("zone_overview_research")
step_npc_research = _make_research_step("npc_research")
step_faction_research = _make_research_step("faction_research")
step_lore_research = _make_research_step("lore_research")
step_narrative_items_research = _make_research_step("narrative_items_research")


# ---------------------------------------------------------------------------
# Step 6: Extract all structured data from accumulated raw content
# ---------------------------------------------------------------------------

TOPIC_SECTION_HEADERS = {
    "zone_overview_research": "## ZONE OVERVIEW",
    "npc_research": "## NPCs AND NOTABLE CHARACTERS",
    "faction_research": "## FACTIONS AND ORGANIZATIONS",
    "lore_research": "## LORE, HISTORY, AND MYTHOLOGY",
    "narrative_items_research": "## LEGENDARY ITEMS AND NARRATIVE OBJECTS",
}

TOPIC_SCHEMA_HINTS = {
    "zone_overview_research": (
        "zone metadata: name, level range, expansion era. "
        "MUST PRESERVE: narrative arc (full storyline — political backstory, "
        "primary conflict, factional tensions, and resolution — not a tagline), "
        "political climate (governing factions, neglected populations, power "
        "struggles), phase states (Cataclysm changes, quest progression phases), "
        "sub-areas and landmarks. "
        "Preserve ALL proper nouns (NPC names, faction names, place names) "
        "even when compressing surrounding text."
    ),
    "npc_research": (
        "NPCs: names, titles, faction allegiance. "
        "MUST PRESERVE per NPC: personality traits and demeanor, motivations "
        "and goals, relationships to other NPCs (allies, rivals, family, mentors), "
        "role classification (quest giver, vendor, boss, antagonist, faction leader), "
        "quest chains they give or participate in, phased/expansion appearances. "
        "Include BOTH friendly and hostile NPCs — quest givers AND dungeon bosses, "
        "antagonist leaders, faction leaders. "
        "Preserve ALL NPC proper names even when compressing other text."
    ),
    "faction_research": (
        "factions: names, type (major faction, guild, cult, military). "
        "MUST PRESERVE: ideology and core beliefs, stated goals, "
        "origin story (how and why the faction formed), key members and leaders, "
        "inter-faction relationships (allied/hostile/neutral — name specific factions), "
        "mutual exclusions, hierarchy (parent factions, sub-factions). "
        "Include BOTH friendly and hostile factions — allied organizations AND "
        "antagonist groups, criminal organizations, hostile forces. "
        "Preserve ALL faction and leader proper names."
    ),
    "lore_research": (
        "lore: event titles, era/timeline placement. "
        "MUST PRESERVE: major historical events with causal chains (what happened, "
        "why it happened, what it caused), named actors in each event, "
        "mythology and cosmological rules, power sources and their origins. "
        "Preserve chronological ordering and cause-effect relationships. "
        "Keep ALL proper nouns (people, places, artifacts, faction names)."
    ),
    "narrative_items_research": (
        "items and artifacts: names, significance tier (legendary, epic, quest, notable). "
        "MUST PRESERVE: story arc (how the item fits into the zone's narrative), "
        "wielder lineage, power description, quest relevance. "
        "EXCLUDE crafting recipes, cooking items, vendor trash, generic consumables. "
        "An empty result is better than irrelevant items."
    ),
}

# Maximum total characters of raw content before summarization kicks in.
# ~75K tokens at ~4 chars/token. Leaves room for prompt template + output.
_EXTRACT_CONTENT_CHAR_LIMIT = 300_000


def _reconstruct_labeled_content(raw_blocks: list[dict]) -> list[tuple[str, str, str]]:
    """Group labeled content blocks by topic and prepend section headers.

    Returns a list of (topic_key, header, body) tuples, one per topic section.
    """
    from collections import OrderedDict

    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for block in raw_blocks:
        topic = block.get("topic", "unknown")
        grouped.setdefault(topic, []).append(block.get("content", ""))

    sections = []
    for topic, contents in grouped.items():
        header = TOPIC_SECTION_HEADERS.get(topic, f"## {topic.upper()}")
        body = "\n\n".join(contents)
        sections.append((topic, header, body))

    return sections


async def _maybe_summarize_sections(
    sections: list[tuple[str, str, str]],
) -> list[str]:
    """Summarize sections if total content exceeds the context budget.

    Each section is a (topic_key, header, body) tuple. If total body chars
    exceed _EXTRACT_CONTENT_CHAR_LIMIT, every section is compressed via the
    MCP Summarizer using topic-specific schema hints.

    Returns a list of ready-to-use section strings (header + body).
    """
    total_chars = sum(len(body) for _, _, body in sections)

    if total_chars <= _EXTRACT_CONTENT_CHAR_LIMIT:
        logger.info(
            "content_within_budget",
            extra={"total_chars": total_chars, "limit": _EXTRACT_CONTENT_CHAR_LIMIT},
        )
        return [f"{header}\n\n{body}" for _, header, body in sections]

    logger.info(
        "content_over_budget_summarizing",
        extra={"total_chars": total_chars, "limit": _EXTRACT_CONTENT_CHAR_LIMIT},
    )

    if not MCP_SUMMARIZER_URL:
        logger.warning("no_summarizer_url_truncating_content")
        return [f"{header}\n\n{body}" for _, header, body in sections]

    # Per-section token budget: distribute evenly across sections.
    # Target ~75K total tokens across all sections.
    per_section_tokens = 75_000 // max(len(sections), 1)

    char_limit = per_section_tokens * 4  # ~4 chars per token

    summarized: list[str] = []
    for topic, header, body in sections:
        schema_hint = TOPIC_SCHEMA_HINTS.get(topic, topic)
        result = await mcp_call(
            MCP_SUMMARIZER_URL,
            "summarize_for_extraction",
            {
                "content": body,
                "schema_hint": schema_hint,
                "max_output_tokens": per_section_tokens,
            },
            timeout=30.0,
            sse_read_timeout=300.0,
        )

        # Detect whether summarization actually reduced the content.
        # The summarizer returns original content on failure, so check size.
        if result and isinstance(result, str) and len(result) < len(body):
            logger.info(
                "section_summarized",
                extra={
                    "topic": topic,
                    "original_chars": len(body),
                    "summarized_chars": len(result),
                },
            )
            summarized.append(f"{header}\n\n{result}")
        else:
            # Summarization failed or returned full content — truncate.
            logger.warning(
                "section_summarize_failed_truncating",
                extra={"topic": topic, "char_limit": char_limit},
            )
            truncated = body[:char_limit] if len(body) > char_limit else body
            summarized.append(f"{header}\n\n{truncated}")

    return summarized


async def step_extract_all(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name
    raw_blocks = checkpoint.step_data.get("research_raw_content", [])
    source_dicts = checkpoint.step_data.get("research_sources", [])
    sources = [SourceReference(**sd) for sd in source_dicts]

    # Reconstruct and summarize
    sections = _reconstruct_labeled_content(raw_blocks)
    summarized = await _maybe_summarize_sections(sections)

    # Build topic -> summarized content map
    section_content: dict[str, str] = {}
    for (topic, _, _), content in zip(sections, summarized):
        section_content[topic] = content

    # Per-category extraction
    zone_data = cast(ZoneData, await researcher.extract_category(
        "zone", zone_name,
        section_content.get("zone_overview_research", ""), sources,
    ))
    npcs_result = cast(NPCExtractionResult, await researcher.extract_category(
        "npcs", zone_name,
        section_content.get("npc_research", ""), sources,
    ))
    factions_result = cast(FactionExtractionResult, await researcher.extract_category(
        "factions", zone_name,
        section_content.get("faction_research", ""), sources,
    ))
    lore_result = cast(LoreExtractionResult, await researcher.extract_category(
        "lore", zone_name,
        section_content.get("lore_research", ""), sources,
    ))
    items_result = cast(NarrativeItemExtractionResult, await researcher.extract_category(
        "narrative_items", zone_name,
        section_content.get("narrative_items_research", ""), sources,
    ))

    # Assemble ZoneExtraction from per-category results
    extraction = ZoneExtraction(
        zone=zone_data,
        npcs=npcs_result.npcs,
        factions=factions_result.factions,
        lore=lore_result.lore,
        narrative_items=items_result.narrative_items,
    )
    checkpoint.step_data["extraction"] = extraction.model_dump(mode="json")
    return checkpoint


# ---------------------------------------------------------------------------
# Step 7: Cross-reference
# ---------------------------------------------------------------------------


def _apply_confidence_caps(
    extraction: ZoneExtraction,
    confidence: dict[str, float],
) -> dict[str, float]:
    """Apply mechanical confidence caps based on field completeness."""
    capped = dict(confidence)

    # Zero-entity caps: if a category extracted nothing, cap low
    if not extraction.npcs:
        capped["npcs"] = min(capped.get("npcs", 0.0), 0.2)
    else:
        total = len(extraction.npcs)
        empty_personality = sum(1 for n in extraction.npcs if not n.personality)
        empty_role = sum(1 for n in extraction.npcs if not n.role)

        if empty_personality / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)
        if empty_role / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)

    if not extraction.factions:
        capped["factions"] = min(capped.get("factions", 0.0), 0.2)

    return capped


async def step_cross_reference(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    extraction_dict = checkpoint.step_data.get("extraction", {})
    extraction = ZoneExtraction.model_validate(extraction_dict)

    cr_result = await researcher.cross_reference(extraction)

    # Apply mechanical confidence caps
    cr_result.confidence = _apply_confidence_caps(extraction, cr_result.confidence)

    checkpoint.step_data["cross_reference"] = cr_result.model_dump(mode="json")
    return checkpoint


# ---------------------------------------------------------------------------
# Step 8: Discover connected zones
# ---------------------------------------------------------------------------


async def step_discover_connected_zones(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    zone_slugs = await researcher.discover_connected_zones(checkpoint.zone_name)
    checkpoint.step_data["discovered_zones"] = zone_slugs
    return checkpoint


# ---------------------------------------------------------------------------
# Step 9: Package and send
# ---------------------------------------------------------------------------


def _compute_quality_warnings(extraction: ZoneExtraction) -> list[str]:
    """Compute quality warnings based on content thresholds."""
    warnings: list[str] = []

    # Shallow narrative arc
    if len(extraction.zone.narrative_arc) < 200:
        warnings.append("shallow_narrative_arc")

    # No NPC personality data
    if extraction.npcs and all(not n.personality for n in extraction.npcs):
        warnings.append("no_npc_personality_data")

    # Missing antagonists (heuristic: check for boss/antagonist roles + hostile factions)
    has_antagonist_npc = any(
        n.role and any(
            keyword in n.role.lower()
            for keyword in ("boss", "antagonist", "villain")
        )
        for n in extraction.npcs
    )
    has_hostile_faction = any(
        any(r.stance == FactionStance.HOSTILE for r in f.inter_faction)
        for f in extraction.factions
    )
    zone_mentions_dungeon = any(
        keyword in extraction.zone.narrative_arc.lower()
        for keyword in ("dungeon", "raid", "instance", "mine", "mines")
    ) or any(
        keyword in entry.content.lower()
        for entry in extraction.lore
        for keyword in ("dungeon", "raid", "instance")
    )

    if zone_mentions_dungeon and not has_antagonist_npc and not has_hostile_faction:
        warnings.append("missing_antagonists")

    return warnings


async def step_package_and_send(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name

    # Rebuild structured data from step_data
    extraction_dict = checkpoint.step_data.get("extraction", {})
    extraction = ZoneExtraction.model_validate(extraction_dict)

    cr_dict = checkpoint.step_data.get("cross_reference", {})
    cr_result = CrossReferenceResult.model_validate(cr_dict)

    source_dicts = checkpoint.step_data.get("research_sources", [])
    all_sources = [SourceReference(**sd) for sd in source_dicts]

    warnings = _compute_quality_warnings(extraction)

    package = ResearchPackage(
        zone_name=zone_name,
        zone_data=extraction.zone,
        npcs=extraction.npcs,
        factions=extraction.factions,
        lore=extraction.lore,
        narrative_items=extraction.narrative_items,
        sources=all_sources,
        confidence=cr_result.confidence,
        conflicts=cr_result.conflicts,
        quality_warnings=warnings,
    )

    checkpoint.step_data["package"] = package.model_dump(mode="json")

    # Publish to RabbitMQ
    if publish_fn:
        envelope = MessageEnvelope(
            source_agent=LoreResearcher.AGENT_ID,
            target_agent="world_lore_validator",
            message_type=MessageType.RESEARCH_PACKAGE,
            payload=package.model_dump(mode="json"),
        )
        await publish_fn(envelope)
        logger.info("package_published", extra={"zone_name": zone_name})
    else:
        logger.warning(
            "package_not_published",
            extra={"zone_name": zone_name, "reason": "no publish_fn"},
        )

    return checkpoint


# ---------------------------------------------------------------------------
# Step dispatch table
# ---------------------------------------------------------------------------


STEP_FUNCTIONS = {
    "zone_overview_research": step_zone_overview_research,
    "npc_research": step_npc_research,
    "faction_research": step_faction_research,
    "lore_research": step_lore_research,
    "narrative_items_research": step_narrative_items_research,
    "extract_all": step_extract_all,
    "cross_reference": step_cross_reference,
    "discover_connected_zones": step_discover_connected_zones,
    "package_and_send": step_package_and_send,
}
