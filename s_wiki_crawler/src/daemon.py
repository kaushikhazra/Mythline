"""Daemon — job consumer for the Wiki Crawler service.

Connects to RabbitMQ, consumes crawl jobs from the job queue, and
executes the deterministic crawl pipeline per zone. Two operating modes:

  Mode A — Process seed zones from the queue (priority)
  Mode B — Refresh the oldest stale zone when queue is empty

Processes one zone at a time (prefetch=1). No LLM calls — all decisions
are algorithmic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import aio_pika
from pydantic import ValidationError

from shared.crawl import DomainThrottle
from src.config import (
    CRAWL_CACHE_ROOT,
    CRAWL_JOB_QUEUE,
    MCP_STORAGE_URL,
    RABBITMQ_URL,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    REFRESH_INTERVAL_HOURS,
    SERVICE_ID,
)
from src.crawler import (
    crawl_page,
    extract_connected_zones,
    mcp_call,
    search_for_category,
    select_urls,
)
from src.logging_config import configure_logging
from src.models import CrawlJob, CrawlScope
from src.storage import _url_to_record_id, store_page, store_page_with_change_detection

logger = logging.getLogger(__name__)

# Idle interval between refresh checks when the queue is empty.
_IDLE_INTERVAL_S = 30


class CrawlerDaemon:

    def __init__(self, crawl_scope: CrawlScope):
        self._running = False
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self.crawl_scope = crawl_scope
        self.throttle = DomainThrottle(RATE_LIMIT_REQUESTS_PER_MINUTE)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the daemon — connect, declare queues, consume jobs."""
        self._running = True
        self._setup_signal_handlers()

        await self._connect_rabbitmq()
        await self._declare_queues()

        if not self._channel:
            logger.error("daemon_no_channel", extra={"reason": "RabbitMQ connection failed"})
            return

        await self._channel.set_qos(prefetch_count=1)

        logger.info("daemon_started", extra={
            "service_id": SERVICE_ID,
            "queue": CRAWL_JOB_QUEUE,
            "cache_root": CRAWL_CACHE_ROOT,
            "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
            "categories": list(self.crawl_scope.categories.keys()),
        })

        queue = await self._channel.get_queue(CRAWL_JOB_QUEUE)

        while self._running:
            # Mode A: try to get a message from the queue (non-blocking)
            message = await queue.get(fail=False)

            if message is not None:
                await self._process_seed(message)
            else:
                # Mode B: refresh oldest stale zone
                did_refresh = await self._refresh_oldest_zone()
                if not did_refresh:
                    await asyncio.sleep(_IDLE_INTERVAL_S)

        await self._shutdown()

    async def _declare_queues(self) -> None:
        """Declare job queue with DLQ binding and priority support."""
        if not self._channel:
            return

        dlq_name = f"{CRAWL_JOB_QUEUE}.dlq"

        # Dead-letter queue
        await self._channel.declare_queue(dlq_name, durable=True)

        # Main job queue with DLQ routing and priority
        await self._channel.declare_queue(
            CRAWL_JOB_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dlq_name,
                "x-max-priority": 10,
            },
        )

        logger.info("queues_declared", extra={
            "job_queue": CRAWL_JOB_QUEUE,
            "dlq": dlq_name,
        })

    # ------------------------------------------------------------------
    # Mode A — Seed Processing
    # ------------------------------------------------------------------

    async def _process_seed(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """Process a crawl job from the queue."""
        try:
            body = json.loads(message.body.decode())
            job = CrawlJob.model_validate(body)
        except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
            logger.warning("message_rejected", extra={
                "error": str(exc),
                "body_preview": message.body[:500].decode(errors="replace"),
            })
            await message.reject(requeue=False)  # → DLQ
            return

        # Freshness check
        zone_record = await self._get_zone_record(job.zone_name)
        if zone_record and zone_record.get("status") == "complete":
            crawled_at_str = zone_record.get("crawled_at")
            if crawled_at_str:
                crawled_at = datetime.fromisoformat(crawled_at_str)
                age_hours = (datetime.now(timezone.utc) - crawled_at).total_seconds() / 3600
                if age_hours < REFRESH_INTERVAL_HOURS:
                    logger.info("zone_fresh_skipped", extra={
                        "zone": job.zone_name,
                        "age_hours": round(age_hours, 1),
                    })
                    await message.ack()
                    return

        try:
            await self._crawl_zone(job.zone_name, job.game)
            await message.ack()
        except Exception as exc:
            logger.error("zone_crawl_error", extra={
                "zone": job.zone_name,
                "error": str(exc),
            }, exc_info=True)
            await message.reject(requeue=False)  # → DLQ

    # ------------------------------------------------------------------
    # Mode B — Refresh
    # ------------------------------------------------------------------

    async def _refresh_oldest_zone(self) -> bool:
        """Find and refresh the oldest stale zone. Returns True if work was done."""
        result = await mcp_call(MCP_STORAGE_URL, "query_records", {
            "table": "crawl_zone",
            "filter_expr": f"status = 'complete' AND crawled_at < time::now() - {REFRESH_INTERVAL_HOURS}h",
            "limit": 1,
        })

        if not result or (isinstance(result, list) and len(result) == 0):
            return False

        zone = result[0] if isinstance(result, list) else result
        if not isinstance(zone, dict):
            return False

        zone_name = zone.get("name", "")
        game = zone.get("game", "wow")
        if not zone_name:
            return False

        logger.info("refresh_cycle_started", extra={"zone": zone_name})
        try:
            await self._crawl_zone(zone_name, game, is_refresh=True)
        except Exception as exc:
            logger.error("refresh_crawl_error", extra={
                "zone": zone_name, "error": str(exc),
            }, exc_info=True)
        return True

    # ------------------------------------------------------------------
    # Zone Crawl Execution
    # ------------------------------------------------------------------

    async def _crawl_zone(
        self,
        zone_name: str,
        game: str,
        is_refresh: bool = False,
    ) -> None:
        """Execute the full crawl pipeline for a zone."""
        logger.info("zone_crawl_started", extra={
            "zone": zone_name, "game": game, "is_refresh": is_refresh,
        })
        start = time.monotonic()

        # Set zone status to crawling
        await self._upsert_zone_record(zone_name, game, status="crawling")

        pages_stored = 0
        pages_failed = 0
        already_crawled: set[str] = set()

        for category_name, category_config in self.crawl_scope.categories.items():
            # 1. Search
            search_results = await search_for_category(zone_name, game, category_config)

            # 2. Select URLs
            selected = select_urls(search_results, category_config, already_crawled)

            # 3. Crawl + store each URL (fail-forward: per-page errors don't stop the zone)
            for search_result in selected:
                try:
                    crawl_result = await crawl_page(search_result.url, self.throttle)
                    already_crawled.add(search_result.url)

                    if crawl_result.content:
                        if is_refresh:
                            file_path, _ = await store_page_with_change_detection(
                                crawl_result, zone_name, game, category_name,
                            )
                        else:
                            file_path = await store_page(
                                crawl_result, zone_name, game, category_name,
                            )

                        if file_path:
                            pages_stored += 1

                            # Store inter-page links in graph
                            for link_url in crawl_result.links:
                                await self._create_page_link(crawl_result.url, link_url)

                        # Link-discovered sub-pages
                        for link_url in crawl_result.links:
                            if link_url not in already_crawled and len(already_crawled) < category_config.max_pages:
                                sub_result = await crawl_page(link_url, self.throttle)
                                already_crawled.add(link_url)
                                if sub_result.content:
                                    if is_refresh:
                                        await store_page_with_change_detection(
                                            sub_result, zone_name, game, category_name,
                                        )
                                    else:
                                        await store_page(sub_result, zone_name, game, category_name)
                                    pages_stored += 1
                    else:
                        pages_failed += 1
                        logger.warning("page_crawl_failed", extra={
                            "zone": zone_name,
                            "url": search_result.url,
                            "error": crawl_result.error,
                        })
                except Exception as exc:
                    pages_failed += 1
                    already_crawled.add(search_result.url)
                    logger.error("page_processing_error", extra={
                        "zone": zone_name,
                        "url": search_result.url,
                        "error": str(exc),
                    }, exc_info=True)

        # Connected zone discovery (from zone_overview pages)
        await self._discover_and_publish_connected_zones(zone_name, game)

        # Update zone record
        await self._upsert_zone_record(
            zone_name, game, status="complete", page_count=pages_stored,
        )

        duration = time.monotonic() - start
        logger.info("zone_crawl_completed", extra={
            "zone": zone_name,
            "pages_stored": pages_stored,
            "pages_failed": pages_failed,
            "duration_s": round(duration, 1),
        })

    # ------------------------------------------------------------------
    # Connected Zone Discovery + Publishing
    # ------------------------------------------------------------------

    async def _discover_and_publish_connected_zones(
        self,
        zone_name: str,
        game: str,
    ) -> None:
        """Extract connected zones from overview content and publish to queue."""
        overview_dir = Path(CRAWL_CACHE_ROOT) / game / zone_name / "zone_overview"
        if not overview_dir.exists():
            return

        all_connected: list[str] = []
        for md_file in overview_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            connected = extract_connected_zones(content, zone_name)
            all_connected.extend(connected)

        # Deduplicate
        unique_zones = list(dict.fromkeys(all_connected))

        for connected_zone in unique_zones:
            # Check if already in graph
            existing = await mcp_call(MCP_STORAGE_URL, "get_record", {
                "table": "crawl_zone",
                "record_id": connected_zone,
            })

            # Create connected_to edge regardless
            await mcp_call(MCP_STORAGE_URL, "create_relation", {
                "relation_type": "connected_to",
                "from_record": f"crawl_zone:{zone_name}",
                "to_record": f"crawl_zone:{connected_zone}",
            })

            if not existing:
                # New zone — create pending record and publish to queue
                await mcp_call(MCP_STORAGE_URL, "create_record", {
                    "table": "crawl_zone",
                    "record_id": connected_zone,
                    "data": json.dumps({
                        "name": connected_zone,
                        "game": game,
                        "status": "pending",
                        "page_count": 0,
                    }),
                })

                job = CrawlJob(zone_name=connected_zone, game=game, priority=-1)
                await self._publish_job(job)

                logger.info("connected_zone_discovered", extra={
                    "source_zone": zone_name,
                    "target_zone": connected_zone,
                })

    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------

    async def _get_zone_record(self, zone_name: str) -> dict | None:
        """Fetch a crawl_zone record from the graph."""
        result = await mcp_call(MCP_STORAGE_URL, "get_record", {
            "table": "crawl_zone",
            "record_id": zone_name,
        })
        return result if isinstance(result, dict) else None

    async def _upsert_zone_record(
        self,
        zone_name: str,
        game: str,
        status: str,
        page_count: int | None = None,
    ) -> None:
        """Create or update a crawl_zone record."""
        data: dict = {
            "name": zone_name,
            "game": game,
            "status": status,
        }
        if status == "complete":
            data["crawled_at"] = datetime.now(timezone.utc).isoformat()
        if page_count is not None:
            data["page_count"] = page_count

        await mcp_call(MCP_STORAGE_URL, "update_record", {
            "table": "crawl_zone",
            "record_id": zone_name,
            "data": json.dumps(data),
        })

    async def _create_page_link(self, from_url: str, to_url: str) -> None:
        """Create a links_to edge between two crawl_page records."""
        from_id = _url_to_record_id(from_url)
        to_id = _url_to_record_id(to_url)

        await mcp_call(MCP_STORAGE_URL, "create_relation", {
            "relation_type": "links_to",
            "from_record": f"crawl_page:{from_id}",
            "to_record": f"crawl_page:{to_id}",
        })

    async def _publish_job(self, job: CrawlJob) -> None:
        """Publish a crawl job to the job queue."""
        if not self._channel:
            logger.warning("publish_skipped", extra={"reason": "no channel"})
            return

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=job.model_dump_json().encode(),
                content_type="application/json",
                priority=max(0, job.priority + 5),  # Shift to RabbitMQ range (0-10)
            ),
            routing_key=CRAWL_JOB_QUEUE,
        )

    # ------------------------------------------------------------------
    # RabbitMQ connection
    # ------------------------------------------------------------------

    async def _connect_rabbitmq(self, max_retries: int = 5) -> None:
        """Connect to RabbitMQ with exponential backoff."""
        for attempt in range(1, max_retries + 1):
            try:
                self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
                self._channel = await self._connection.channel()
                logger.info("rabbitmq_connected")
                return
            except Exception:
                if attempt == max_retries:
                    logger.error("rabbitmq_connection_failed", extra={
                        "attempts": attempt,
                    }, exc_info=True)
                    return
                delay = min(2 ** attempt, 30)
                logger.warning("rabbitmq_connection_retry", extra={
                    "attempt": attempt, "retry_in_seconds": delay,
                })
                await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def _shutdown(self) -> None:
        """Graceful shutdown — finish current page, close connections."""
        logger.info("daemon_shutdown", extra={"reason": "signal"})
        self._running = False

        if self._channel:
            try:
                await self._channel.close()
            except Exception:
                logger.warning("channel_close_failed", exc_info=True)
        if self._connection:
            try:
                await self._connection.close()
            except Exception:
                logger.warning("connection_close_failed", exc_info=True)

    def _setup_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_signal)
            except NotImplementedError:
                # Windows does not support add_signal_handler
                signal.signal(sig, lambda s, f: self._handle_signal())

    def _handle_signal(self) -> None:
        logger.info("signal_received")
        self._running = False


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    configure_logging()

    from src.config import load_crawl_scope
    crawl_scope = load_crawl_scope()

    daemon = CrawlerDaemon(crawl_scope)
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
