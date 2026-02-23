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

from src.agent import (
    CrossReferenceResult,
    LoreResearcher,
    ResearchResult,
    ZoneExtraction,
)
from src.checkpoint import save_checkpoint
from src.config import AGENT_ID, GAME_NAME, MCP_SUMMARIZER_URL
from src.mcp_client import mcp_call
from src.models import (
    MessageEnvelope,
    MessageType,
    ResearchCheckpoint,
    ResearchPackage,
    SourceReference,
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
        "zone overview for {zone} in {game}: "
        "level range, narrative arc, political climate, access gating, "
        "phase states, and general atmosphere."
    ),
    "npc_research": (
        "NPCs and notable characters in {zone} in {game}: "
        "names, faction allegiance, personality, motivations, relationships, "
        "quest involvement, and phased states."
    ),
    "faction_research": (
        "factions and organizations in {zone} in {game}: "
        "hierarchy, inter-faction relationships, mutual exclusions, ideology, goals."
    ),
    "lore_research": (
        "lore, history, mythology, and cosmology of {zone} in {game}: "
        "historical events, power sources, cosmic rules, world-shaping moments."
    ),
    "narrative_items_research": (
        "legendary items, artifacts, and narrative objects in {zone} "
        "in {game}: story arcs, wielder lineage, power descriptions, significance."
    ),
}


async def _summarize_research_result(
    result: ResearchResult, topic_key: str, zone_name: str = ""
) -> ResearchResult:
    """Compress raw content blocks via MCP summarizer before accumulation.

    Concatenates all raw content blocks, sends to the summarizer with the
    topic's research focus as the schema_hint, and returns a new
    ResearchResult with a single summarized block.

    On failure: returns the original result unchanged (graceful degradation).
    """
    if not result.raw_content or not MCP_SUMMARIZER_URL:
        return result

    combined = "\n\n---\n\n".join(result.raw_content)
    template = RESEARCH_TOPICS.get(topic_key, "")
    schema_hint = template.format(zone=zone_name, game=GAME_NAME) if template else ""

    summary = await mcp_call(
        MCP_SUMMARIZER_URL,
        "summarize_for_extraction",
        {"content": combined, "schema_hint": schema_hint},
        timeout=120.0,
        sse_read_timeout=300.0,
    )

    summary = str(summary) if summary is not None else None

    if summary is None:
        logger.warning(
            "summarizer_failed_graceful_degradation",
            extra={"topic": topic_key, "raw_blocks": len(result.raw_content)},
        )
        return result

    logger.info(
        "research_content_summarized",
        extra={
            "topic": topic_key,
            "raw_blocks": len(result.raw_content),
            "raw_chars": len(combined),
            "summary_chars": len(summary),
        },
    )

    return ResearchResult(
        raw_content=[summary],
        sources=result.sources,
        summary=result.summary,
    )


def _make_research_step(topic_key: str):
    """Factory that returns an async step function for a research topic."""
    template = RESEARCH_TOPICS[topic_key]

    async def step(
        checkpoint: ResearchCheckpoint,
        researcher: LoreResearcher,
        publish_fn: Callable | None = None,
    ) -> ResearchCheckpoint:
        zone_name = checkpoint.zone_name.replace("_", " ")
        instructions = "Focus on " + template.format(zone=zone_name, game=GAME_NAME)
        result = await researcher.research_zone(zone_name, instructions=instructions)
        result = await _summarize_research_result(result, topic_key, zone_name)
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


def _reconstruct_labeled_content(raw_blocks: list[dict]) -> list[str]:
    """Group labeled content blocks by topic and prepend section headers.

    Returns a list of strings, one per topic section, with the section
    header followed by all content blocks for that topic.
    """
    from collections import OrderedDict

    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for block in raw_blocks:
        topic = block.get("topic", "unknown")
        grouped.setdefault(topic, []).append(block.get("content", ""))

    sections = []
    for topic, contents in grouped.items():
        header = TOPIC_SECTION_HEADERS.get(topic, f"## {topic.upper()}")
        section = header + "\n\n" + "\n\n".join(contents)
        sections.append(section)

    return sections


async def step_extract_all(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name
    raw_blocks = checkpoint.step_data.get("research_raw_content", [])
    source_dicts = checkpoint.step_data.get("research_sources", [])
    sources = [SourceReference(**sd) for sd in source_dicts]

    labeled_content = _reconstruct_labeled_content(raw_blocks)
    extraction = await researcher.extract_zone_data(zone_name, labeled_content, sources)
    checkpoint.step_data["extraction"] = extraction.model_dump(mode="json")
    return checkpoint


# ---------------------------------------------------------------------------
# Step 7: Cross-reference
# ---------------------------------------------------------------------------


async def step_cross_reference(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
) -> ResearchCheckpoint:
    extraction_dict = checkpoint.step_data.get("extraction", {})
    extraction = ZoneExtraction.model_validate(extraction_dict)

    cr_result = await researcher.cross_reference(extraction)
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
