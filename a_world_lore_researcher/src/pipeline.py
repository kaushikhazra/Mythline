"""10-step research pipeline for zone-level lore extraction.

Each step is checkpointed for crash resilience. The pipeline runs for
a single zone and produces a ResearchPackage for the validator.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from src.checkpoint import save_checkpoint
from src.config import (
    GAME_NAME,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    get_source_tier_for_domain,
)
from src.mcp_client import web_search, crawl_url
from src.models import (
    ResearchCheckpoint,
    ResearchPackage,
    SourceReference,
    SourceTier,
    ZoneData,
)

logger = logging.getLogger(__name__)

search_limiter = AsyncLimiter(RATE_LIMIT_REQUESTS_PER_MINUTE, 60)
crawl_limiter = AsyncLimiter(RATE_LIMIT_REQUESTS_PER_MINUTE, 60)

PIPELINE_STEPS = [
    "zone_overview_search",
    "zone_overview_extract",
    "npc_search",
    "npc_extract",
    "faction_search_extract",
    "lore_search_extract",
    "narrative_items_search_extract",
    "cross_reference",
    "discover_connected_zones",
    "package_and_send",
]


def _make_source_ref(url: str) -> SourceReference:
    domain = urlparse(url).netloc
    tier_name = get_source_tier_for_domain(domain)
    try:
        tier = SourceTier(tier_name) if tier_name else SourceTier.TERTIARY
    except ValueError:
        tier = SourceTier.TERTIARY
    return SourceReference(url=url, domain=domain, tier=tier)


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=30))
async def _rate_limited_search(query: str, max_results: int = 10) -> list[dict]:
    async with search_limiter:
        return await web_search(query, max_results)


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=30))
async def _rate_limited_crawl(url: str) -> dict:
    async with crawl_limiter:
        return await crawl_url(url)


async def run_pipeline(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name
    start_step = checkpoint.current_step

    for step_idx in range(start_step, len(PIPELINE_STEPS)):
        step_name = PIPELINE_STEPS[step_idx]
        logger.info("pipeline_step_started", extra={"zone_name": zone_name, "step": step_idx + 1, "step_name": step_name})

        step_fn = STEP_FUNCTIONS.get(step_name)
        if step_fn:
            checkpoint = await step_fn(checkpoint)

        checkpoint.current_step = step_idx + 1
        await save_checkpoint(checkpoint)
        logger.info("pipeline_step_completed", extra={"zone_name": zone_name, "step": step_idx + 1, "step_name": step_name})

    return checkpoint


async def step_zone_overview_search(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} lore zone overview"
    results = await _rate_limited_search(query)
    checkpoint.step_data["zone_overview_urls"] = [r.get("url", "") for r in results if r.get("url")]
    checkpoint.step_data["zone_overview_snippets"] = [r.get("snippet", "") for r in results]
    return checkpoint


async def step_zone_overview_extract(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    urls = checkpoint.step_data.get("zone_overview_urls", [])
    crawled_content = []
    sources = []

    for url in urls[:5]:
        try:
            result = await _rate_limited_crawl(url)
            if result.get("content"):
                crawled_content.append(result["content"])
                sources.append(_make_source_ref(url))
        except Exception:
            logger.warning("crawl_failed", extra={"url": url})

    checkpoint.step_data["zone_overview_content"] = crawled_content
    checkpoint.step_data["zone_overview_sources"] = [s.model_dump() for s in sources]
    return checkpoint


async def step_npc_search(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} NPCs notable characters"
    results = await _rate_limited_search(query)
    checkpoint.step_data["npc_urls"] = [r.get("url", "") for r in results if r.get("url")]
    return checkpoint


async def step_npc_extract(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    urls = checkpoint.step_data.get("npc_urls", [])
    crawled_content = []
    sources = []

    for url in urls[:5]:
        try:
            result = await _rate_limited_crawl(url)
            if result.get("content"):
                crawled_content.append(result["content"])
                sources.append(_make_source_ref(url))
        except Exception:
            logger.warning("crawl_failed", extra={"url": url})

    checkpoint.step_data["npc_content"] = crawled_content
    checkpoint.step_data["npc_sources"] = [s.model_dump() for s in sources]
    return checkpoint


async def step_faction_search_extract(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} factions organizations"
    results = await _rate_limited_search(query)
    urls = [r.get("url", "") for r in results if r.get("url")]

    crawled_content = []
    sources = []
    for url in urls[:5]:
        try:
            result = await _rate_limited_crawl(url)
            if result.get("content"):
                crawled_content.append(result["content"])
                sources.append(_make_source_ref(url))
        except Exception:
            logger.warning("crawl_failed", extra={"url": url})

    checkpoint.step_data["faction_content"] = crawled_content
    checkpoint.step_data["faction_sources"] = [s.model_dump() for s in sources]
    return checkpoint


async def step_lore_search_extract(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} lore history mythology cosmology"
    results = await _rate_limited_search(query)
    urls = [r.get("url", "") for r in results if r.get("url")]

    crawled_content = []
    sources = []
    for url in urls[:5]:
        try:
            result = await _rate_limited_crawl(url)
            if result.get("content"):
                crawled_content.append(result["content"])
                sources.append(_make_source_ref(url))
        except Exception:
            logger.warning("crawl_failed", extra={"url": url})

    checkpoint.step_data["lore_content"] = crawled_content
    checkpoint.step_data["lore_sources"] = [s.model_dump() for s in sources]
    return checkpoint


async def step_narrative_items_search_extract(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} legendary items artifacts"
    results = await _rate_limited_search(query)
    urls = [r.get("url", "") for r in results if r.get("url")]

    crawled_content = []
    sources = []
    for url in urls[:5]:
        try:
            result = await _rate_limited_crawl(url)
            if result.get("content"):
                crawled_content.append(result["content"])
                sources.append(_make_source_ref(url))
        except Exception:
            logger.warning("crawl_failed", extra={"url": url})

    checkpoint.step_data["narrative_items_content"] = crawled_content
    checkpoint.step_data["narrative_items_sources"] = [s.model_dump() for s in sources]
    return checkpoint


async def step_cross_reference(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    checkpoint.step_data["cross_reference_complete"] = True
    return checkpoint


async def step_discover_connected_zones(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name.replace("_", " ")
    query = f"{zone_name} {GAME_NAME} connected zones adjacent areas"
    results = await _rate_limited_search(query)

    checkpoint.step_data["connected_zone_urls"] = [r.get("url", "") for r in results if r.get("url")]
    checkpoint.step_data["discover_connected_complete"] = True
    return checkpoint


async def step_package_and_send(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    zone_name = checkpoint.zone_name
    zone_data = ZoneData(name=zone_name.replace("_", " ").title(), game=GAME_NAME)

    all_sources = []
    for key in ["zone_overview_sources", "npc_sources", "faction_sources", "lore_sources", "narrative_items_sources"]:
        source_dicts = checkpoint.step_data.get(key, [])
        for sd in source_dicts:
            all_sources.append(SourceReference(**sd))

    package = ResearchPackage(
        zone_name=zone_name,
        zone_data=zone_data,
        sources=all_sources,
    )

    checkpoint.step_data["package"] = package.model_dump()
    checkpoint.step_data["package_ready"] = True
    return checkpoint


STEP_FUNCTIONS = {
    "zone_overview_search": step_zone_overview_search,
    "zone_overview_extract": step_zone_overview_extract,
    "npc_search": step_npc_search,
    "npc_extract": step_npc_extract,
    "faction_search_extract": step_faction_search_extract,
    "lore_search_extract": step_lore_search_extract,
    "narrative_items_search_extract": step_narrative_items_search_extract,
    "cross_reference": step_cross_reference,
    "discover_connected_zones": step_discover_connected_zones,
    "package_and_send": step_package_and_send,
}
