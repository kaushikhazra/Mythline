"""E2E smoke test — runs the real orchestrator against a live zone.

NOT a pytest test. Run manually when you want to validate the full pipeline
with real LLM calls, web search, and crawling.

Usage:
    python scripts/e2e_smoke.py                          # default: elwynn_forest
    python scripts/e2e_smoke.py --zone westfall
    python scripts/e2e_smoke.py --zone elwynn_forest --skip-discovery

Prerequisites:
    - Docker services running: crawl4ai (port 11235), MCP web search
    - OPENROUTER_API_KEY set in .env or environment
    - LLM_MODEL set (or defaults from config.py)

Output:
    - Console summary with mechanical metrics
    - Full JSON saved to .claude/research/e2e-results/{zone}_{timestamp}.json
    - Read the JSON file with Velasari for qualitative scorecard
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# --- Path setup (script is in scripts/, imports from src/ and shared/) ---
agent_root = Path(__file__).resolve().parent.parent
repo_root = agent_root.parent
sys.path.insert(0, str(agent_root))
sys.path.insert(0, str(repo_root))

from dotenv import load_dotenv
load_dotenv(agent_root / ".env")

# --- Local overrides: Docker hostnames -> localhost for local runs ---
_LOCAL_OVERRIDES = {
    "MCP_WEB_SEARCH_URL": "http://localhost:8006/mcp",
    "MCP_STORAGE_URL": "http://localhost:8005/mcp",
    "MCP_WEB_CRAWLER_URL": "http://localhost:11235",
    "RABBITMQ_URL": "amqp://mythline:mythline@localhost:5672/",
}
for key, value in _LOCAL_OVERRIDES.items():
    if key not in os.environ or "localhost" not in os.environ[key]:
        os.environ[key] = value

from src.agent import LoreResearcher, OrchestratorResult
from src.daemon import Daemon, _apply_confidence_caps, _compute_quality_warnings
from src.logging_config import setup_logging
from src.models import (
    ResearchPackage,
    ZoneData,
    ZoneExtraction,
)


def _serialize_result(result: OrchestratorResult) -> dict:
    """Convert OrchestratorResult to a JSON-serializable dict."""
    return {
        "zone_data": result.zone_data.model_dump(mode="json") if result.zone_data else None,
        "npcs": [n.model_dump(mode="json") for n in result.npcs],
        "factions": [f.model_dump(mode="json") for f in result.factions],
        "lore": [l.model_dump(mode="json") for l in result.lore],
        "narrative_items": [i.model_dump(mode="json") for i in result.narrative_items],
        "sources": [s.model_dump(mode="json") for s in result.sources],
        "cross_ref_result": (
            result.cross_ref_result.model_dump(mode="json")
            if result.cross_ref_result else None
        ),
        "discovered_zones": result.discovered_zones,
        "orchestrator_tokens": result.orchestrator_tokens,
        "worker_tokens": result.worker_tokens,
    }


def _compute_metrics(result: OrchestratorResult, package: ResearchPackage) -> dict:
    """Compute mechanical quality metrics from the orchestrator output."""
    # Source tier distribution
    tier_counts: dict[str, int] = {}
    unique_domains: set[str] = set()
    for s in result.sources:
        tier_counts[s.tier.value] = tier_counts.get(s.tier.value, 0) + 1
        unique_domains.add(s.domain)

    # NPC field completeness
    npcs_with_personality = sum(1 for n in result.npcs if n.personality)
    npcs_with_role = sum(1 for n in result.npcs if n.occupation)
    npcs_with_motivations = sum(1 for n in result.npcs if n.motivations)

    # Faction field completeness
    factions_with_ideology = sum(1 for f in result.factions if f.ideology)
    factions_with_goals = sum(1 for f in result.factions if f.goals)
    factions_with_relations = sum(1 for f in result.factions if f.inter_faction)

    # Lore field completeness
    lore_with_content = sum(1 for l in result.lore if len(l.content) > 50)

    # Narrative arc length
    narrative_arc_len = len(result.zone_data.narrative_arc) if result.zone_data else 0

    return {
        "completeness": {
            "zone_data_present": result.zone_data is not None,
            "narrative_arc_chars": narrative_arc_len,
            "npc_count": len(result.npcs),
            "npcs_with_personality": npcs_with_personality,
            "npcs_with_role": npcs_with_role,
            "npcs_with_motivations": npcs_with_motivations,
            "faction_count": len(result.factions),
            "factions_with_ideology": factions_with_ideology,
            "factions_with_goals": factions_with_goals,
            "factions_with_relations": factions_with_relations,
            "lore_count": len(result.lore),
            "lore_with_content": lore_with_content,
            "narrative_item_count": len(result.narrative_items),
        },
        "sources": {
            "total_sources": len(result.sources),
            "unique_domains": len(unique_domains),
            "domains": sorted(unique_domains),
            "tier_distribution": tier_counts,
        },
        "cross_reference": {
            "ran": result.cross_ref_result is not None,
            "is_consistent": (
                result.cross_ref_result.is_consistent
                if result.cross_ref_result else None
            ),
            "conflict_count": (
                len(result.cross_ref_result.conflicts)
                if result.cross_ref_result else 0
            ),
            "confidence": (
                result.cross_ref_result.confidence
                if result.cross_ref_result else {}
            ),
        },
        "discovery": {
            "zone_count": len(result.discovered_zones),
            "zones": result.discovered_zones,
        },
        "tokens": {
            "orchestrator": result.orchestrator_tokens,
            "worker": result.worker_tokens,
            "total": result.orchestrator_tokens + result.worker_tokens,
        },
        "quality_warnings": package.quality_warnings,
        "final_confidence": package.confidence,
    }


def _print_summary(zone_name: str, metrics: dict, elapsed: float, output_path: str):
    """Print a human-readable summary to console."""
    sep = "=" * 55
    c = metrics["completeness"]
    s = metrics["sources"]
    xr = metrics["cross_reference"]
    d = metrics["discovery"]
    t = metrics["tokens"]

    print(f"\n{sep}")
    print(f"  WLR E2E Smoke Test -- {zone_name}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(sep)

    # Completeness
    arc = c["narrative_arc_chars"]
    zone_mark = "present" if c["zone_data_present"] else "MISSING"
    print(f"  Zone Data:     {zone_mark} (narrative_arc: {arc:,} chars)")
    print(f"  NPCs:          {c['npc_count']} ({c['npcs_with_personality']} personality, {c['npcs_with_role']} role, {c['npcs_with_motivations']} motivations)")
    print(f"  Factions:      {c['faction_count']} ({c['factions_with_ideology']} ideology, {c['factions_with_goals']} goals, {c['factions_with_relations']} relations)")
    print(f"  Lore:          {c['lore_count']} entries ({c['lore_with_content']} with content >50 chars)")
    print(f"  Items:         {c['narrative_item_count']} narrative items")

    # Sources
    tiers = s["tier_distribution"]
    tier_str = ", ".join(f"{k}={v}" for k, v in sorted(tiers.items()))
    print(f"  Sources:       {s['total_sources']} ({s['unique_domains']} domains) [{tier_str}]")

    # Cross-reference
    if xr["ran"]:
        consistent = "consistent" if xr["is_consistent"] else "INCONSISTENT"
        conf_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(xr["confidence"].items()))
        print(f"  Cross-ref:     {consistent}, {xr['conflict_count']} conflicts")
        print(f"  Confidence:    {conf_str}")
    else:
        print(f"  Cross-ref:     DID NOT RUN")

    # Final confidence (after caps)
    final = metrics["final_confidence"]
    if final:
        final_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(final.items()))
        print(f"  Final conf:    {final_str}")

    # Discovery
    if d["zones"]:
        preview = ", ".join(d["zones"][:5])
        if d["zone_count"] > 5:
            preview += "..."
        print(f"  Discovery:     {d['zone_count']} zones ({preview})")
    else:
        print(f"  Discovery:     none (skipped or empty)")

    # Warnings
    warnings = metrics["quality_warnings"]
    if warnings:
        print(f"  Warnings:      {', '.join(warnings)}")
    else:
        print(f"  Warnings:      none")

    # Tokens
    print(f"  Tokens:        orchestrator={t['orchestrator']:,}  workers={t['worker']:,}  total={t['total']:,}")

    print(sep)
    print(f"  Saved: {output_path}")
    print(sep)


async def run(zone_name: str, skip_discovery: bool):
    """Run the orchestrator and save results."""
    setup_logging()

    print(f"\nStarting WLR orchestrator for zone: {zone_name}")
    if skip_discovery:
        print("  (discovery skipped)")
    print("  This will make real LLM calls and cost tokens.\n")

    researcher = LoreResearcher()

    start = time.time()
    result = await researcher.research_zone(zone_name, skip_discovery=skip_discovery)
    elapsed = time.time() - start

    # Assemble package (applies quality warnings + confidence caps)
    daemon = Daemon()
    package = daemon._assemble_package(result, zone_name)

    # Compute metrics
    metrics = _compute_metrics(result, package)

    # Build output document
    output = {
        "metadata": {
            "zone_name": zone_name,
            "skip_discovery": skip_discovery,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
        },
        "metrics": metrics,
        "orchestrator_result": _serialize_result(result),
        "research_package": package.model_dump(mode="json"),
    }

    # Save to file
    output_dir = repo_root / ".claude" / "research" / "e2e-results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{zone_name}_{timestamp}.json"
    output_file.write_text(json.dumps(output, indent=2, default=str))

    # Print summary
    _print_summary(zone_name, metrics, elapsed, str(output_file.relative_to(repo_root)))


def main():
    parser = argparse.ArgumentParser(description="WLR E2E smoke test — real orchestrator run")
    parser.add_argument("--zone", default="elwynn_forest", help="Zone slug to research (default: elwynn_forest)")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip zone discovery (saves tokens)")
    args = parser.parse_args()

    asyncio.run(run(args.zone, args.skip_discovery))


if __name__ == "__main__":
    main()
