"""E2E smoke test — publishes a seed job and verifies the crawl pipeline.

NOT a pytest test. Run manually against live Docker services to validate
the full wiki-crawler pipeline: RabbitMQ → daemon → crawl4ai → filesystem
→ SurrealDB graph.

Usage:
    python scripts/e2e_smoke.py                          # default: elwynn_forest
    python scripts/e2e_smoke.py --zone westfall
    python scripts/e2e_smoke.py --zone duskwood --timeout 300

Prerequisites:
    - Docker services running: rabbitmq, mcp-storage, mcp-web-search, crawl4ai
    - wiki-crawler daemon running (docker compose up wiki-crawler)

Output:
    - Console summary with crawl metrics
    - Full JSON saved to .claude/research/e2e-results/wc_{zone}_{timestamp}.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# --- Path setup (script is in scripts/, imports from src/ and shared/) ---
service_root = Path(__file__).resolve().parent.parent
repo_root = service_root.parent
sys.path.insert(0, str(service_root))
sys.path.insert(0, str(repo_root))

import aio_pika

# --- Local overrides: Docker hostnames -> localhost for local runs ---
_LOCAL_OVERRIDES = {
    "MCP_STORAGE_URL": "http://localhost:8005/mcp",
    "MCP_WEB_SEARCH_URL": "http://localhost:8006/mcp",
    "CRAWL4AI_URL": "http://localhost:11235",
    "RABBITMQ_URL": "amqp://mythline:mythline@localhost:5672/",
    "CRAWL_JOB_QUEUE": "s.wiki_crawler.jobs",
}
for key, value in _LOCAL_OVERRIDES.items():
    if key not in os.environ or "localhost" not in os.environ.get(key, ""):
        os.environ[key] = value

from src.config import CRAWL_JOB_QUEUE, MCP_STORAGE_URL, RABBITMQ_URL
from src.crawler import mcp_call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _publish_seed(zone_name: str, game: str) -> None:
    """Publish a CrawlJob seed message to the wiki-crawler queue."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declare queue (idempotent — matches daemon's declaration)
        dlq_name = f"{CRAWL_JOB_QUEUE}.dlq"
        await channel.declare_queue(dlq_name, durable=True)
        await channel.declare_queue(
            CRAWL_JOB_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dlq_name,
                "x-max-priority": 10,
            },
        )

        job = {"zone_name": zone_name, "game": game, "priority": 5}
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(job).encode(),
                content_type="application/json",
                priority=10,  # Highest priority — process immediately
            ),
            routing_key=CRAWL_JOB_QUEUE,
        )
        print(f"  Published seed: {job}")


async def _poll_zone_status(
    zone_name: str,
    timeout: float,
    poll_interval: float = 5.0,
) -> dict | None:
    """Poll the crawl_zone record until status=complete or timeout."""
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        result = await mcp_call(MCP_STORAGE_URL, "get_record", {
            "table": "crawl_zone",
            "record_id": zone_name,
        })

        if isinstance(result, dict):
            status = result.get("status", "")
            page_count = result.get("page_count", 0)
            elapsed = time.monotonic() - start
            print(f"  [{elapsed:5.1f}s] crawl_zone:{zone_name} status={status} pages={page_count}")

            if status == "complete":
                return result
        else:
            elapsed = time.monotonic() - start
            print(f"  [{elapsed:5.1f}s] crawl_zone:{zone_name} not found yet")

        await asyncio.sleep(poll_interval)

    return None


async def _query_pages(zone_name: str) -> list[dict]:
    """Fetch all crawl_page records linked to this zone via has_page edges."""
    result = await mcp_call(MCP_STORAGE_URL, "traverse", {
        "start_record": f"crawl_zone:{zone_name}",
        "relation_type": "has_page",
        "direction": "outbound",
    })

    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    return []


async def _query_connected_zones(zone_name: str) -> list[dict]:
    """Fetch connected_to edges from this zone."""
    result = await mcp_call(MCP_STORAGE_URL, "traverse", {
        "start_record": f"crawl_zone:{zone_name}",
        "relation_type": "connected_to",
        "direction": "outbound",
    })

    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    return []


async def _check_dlq() -> int:
    """Check how many messages are in the dead-letter queue."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        dlq_name = f"{CRAWL_JOB_QUEUE}.dlq"
        try:
            queue = await channel.declare_queue(dlq_name, durable=True, passive=True)
            return queue.declaration_result.message_count
        except Exception:
            return 0


async def _check_queue_depth() -> int:
    """Check how many messages remain in the main job queue."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        try:
            queue = await channel.declare_queue(
                CRAWL_JOB_QUEUE,
                durable=True,
                passive=True,
            )
            return queue.declaration_result.message_count
        except Exception:
            return 0


async def _purge_queue() -> int:
    """Purge all messages from the job queue. Returns count of purged messages."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        dlq_name = f"{CRAWL_JOB_QUEUE}.dlq"

        # Declare both queues (idempotent)
        await channel.declare_queue(dlq_name, durable=True)
        queue = await channel.declare_queue(
            CRAWL_JOB_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dlq_name,
                "x-max-priority": 10,
            },
        )

        count = queue.declaration_result.message_count
        if count > 0:
            await queue.purge()
        return count


# ---------------------------------------------------------------------------
# Metrics & reporting
# ---------------------------------------------------------------------------


def _compute_metrics(
    zone_record: dict,
    pages: list[dict],
    connected: list[dict],
    dlq_count: int,
    queue_depth: int,
    elapsed: float,
) -> dict:
    """Compute metrics from the crawl results."""
    # Page category distribution
    categories: dict[str, int] = {}
    domains: dict[str, int] = {}
    total_content_length = 0

    for page in pages:
        cat = page.get("page_type", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        domain = page.get("domain", "unknown")
        domains[domain] = domains.get(domain, 0) + 1
        total_content_length += page.get("content_length", 0)

    return {
        "zone": {
            "name": zone_record.get("name", ""),
            "game": zone_record.get("game", ""),
            "status": zone_record.get("status", ""),
            "page_count": zone_record.get("page_count", 0),
        },
        "pages": {
            "total_from_graph": len(pages),
            "categories": categories,
            "domains": domains,
            "total_content_bytes": total_content_length,
        },
        "graph": {
            "connected_zones": len(connected),
            "connected_zone_names": [
                z.get("name", z.get("id", "?")) for z in connected
            ],
        },
        "health": {
            "dlq_messages": dlq_count,
            "remaining_queue_depth": queue_depth,
        },
        "timing": {
            "elapsed_seconds": round(elapsed, 1),
        },
    }


def _print_summary(zone_name: str, metrics: dict, output_path: str):
    """Print a human-readable summary to console."""
    sep = "=" * 60
    z = metrics["zone"]
    p = metrics["pages"]
    g = metrics["graph"]
    h = metrics["health"]
    t = metrics["timing"]

    print(f"\n{sep}")
    print(f"  Wiki Crawler E2E Smoke Test -- {zone_name}")
    print(f"  Elapsed: {t['elapsed_seconds']}s")
    print(sep)

    # Zone
    print(f"  Zone:          {z['name']} ({z['game']}) — status: {z['status']}")
    print(f"  Pages stored:  {z['page_count']} (zone record)")
    print(f"  Pages in graph: {p['total_from_graph']} (via has_page edges)")
    print(f"  Content size:  {p['total_content_bytes']:,} bytes")

    # Categories
    if p["categories"]:
        cat_str = ", ".join(f"{k}={v}" for k, v in sorted(p["categories"].items()))
        print(f"  Categories:    {cat_str}")

    # Domains
    if p["domains"]:
        dom_str = ", ".join(f"{k}={v}" for k, v in sorted(p["domains"].items()))
        print(f"  Domains:       {dom_str}")

    # Graph
    if g["connected_zones"] > 0:
        preview = ", ".join(g["connected_zone_names"][:5])
        if g["connected_zones"] > 5:
            preview += "..."
        print(f"  Connected:     {g['connected_zones']} zones ({preview})")
    else:
        print(f"  Connected:     none discovered")

    # Health
    if h["dlq_messages"] > 0:
        print(f"  DLQ:           {h['dlq_messages']} FAILED MESSAGES")
    else:
        print(f"  DLQ:           clean")
    print(f"  Queue depth:   {h['remaining_queue_depth']} remaining")

    # Verdict
    print(sep)
    passed = (
        z["status"] == "complete"
        and z["page_count"] > 0
        and p["total_from_graph"] > 0
        and h["dlq_messages"] == 0
    )
    verdict = "PASS" if passed else "FAIL"
    print(f"  Verdict: {verdict}")
    print(f"  Saved: {output_path}")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run(zone_name: str, game: str, timeout: float, purge: bool = True):
    """Publish a seed job and verify the full pipeline."""
    print(f"\nWiki Crawler E2E Smoke Test")
    print(f"  Zone: {zone_name}")
    print(f"  Game: {game}")
    print(f"  Timeout: {timeout}s")
    print(f"  Queue: {CRAWL_JOB_QUEUE}")
    print()

    # 0. Purge stale messages (avoids the daemon consuming old seeds that
    #    reset the zone back to "crawling" before our poll detects "complete")
    if purge:
        print("Step 0: Purging stale messages from queue...")
        purged = await _purge_queue()
        if purged > 0:
            print(f"  Purged {purged} stale message(s)")
        else:
            print(f"  Queue was already empty")
        print()

    # 1. Publish seed job
    print("Step 1: Publishing seed job to RabbitMQ...")
    await _publish_seed(zone_name, game)

    # 2. Poll until complete
    print("\nStep 2: Polling crawl_zone status...")
    start = time.monotonic()
    zone_record = await _poll_zone_status(zone_name, timeout)
    elapsed = time.monotonic() - start

    if not zone_record:
        print(f"\n  TIMEOUT after {timeout}s — zone never reached 'complete'")
        print("  Check wiki-crawler logs: docker compose logs wiki-crawler --tail 50")
        sys.exit(1)

    # 3. Query graph for pages and connections
    print("\nStep 3: Querying graph for pages and connections...")
    pages = await _query_pages(zone_name)
    connected = await _query_connected_zones(zone_name)
    dlq_count = await _check_dlq()
    queue_depth = await _check_queue_depth()

    # 4. Compute metrics
    metrics = _compute_metrics(zone_record, pages, connected, dlq_count, queue_depth, elapsed)

    # 5. Save results
    output_dir = repo_root / ".claude" / "research" / "e2e-results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"wc_{zone_name}_{timestamp}.json"

    output = {
        "metadata": {
            "test": "wiki-crawler-e2e",
            "zone_name": zone_name,
            "game": game,
            "timestamp": datetime.now().isoformat(),
            "timeout": timeout,
        },
        "metrics": metrics,
        "zone_record": zone_record,
        "pages": pages,
        "connected_zones": connected,
    }
    output_file.write_text(json.dumps(output, indent=2, default=str))

    # 6. Print summary
    relative_path = str(output_file.relative_to(repo_root))
    _print_summary(zone_name, metrics, relative_path)


def main():
    parser = argparse.ArgumentParser(
        description="Wiki Crawler E2E smoke test — publish seed, verify pipeline",
    )
    parser.add_argument(
        "--zone", default="elwynn_forest",
        help="Zone slug to crawl (default: elwynn_forest)",
    )
    parser.add_argument(
        "--game", default="wow",
        help="Game identifier (default: wow)",
    )
    parser.add_argument(
        "--timeout", type=float, default=600,
        help="Max seconds to wait for crawl completion (default: 600)",
    )
    parser.add_argument(
        "--no-purge", action="store_true",
        help="Skip purging stale messages from the queue before publishing",
    )
    args = parser.parse_args()

    asyncio.run(run(args.zone, args.game, args.timeout, purge=not args.no_purge))


if __name__ == "__main__":
    main()
