"""Daemon — job consumer for the World Lore Researcher.

Connects to RabbitMQ, consumes research jobs from the job queue,
executes zone research via the LLM-driven orchestrator with depth-based
wave expansion, and publishes status updates. Processes one job at a time
(prefetch=1).
"""

from __future__ import annotations

import asyncio
import logging
import signal

import aio_pika

from src.agent import LoreResearcher, OrchestratorResult
from src.checkpoint import (
    add_tokens_used,
    check_daily_budget_reset,
    is_daily_budget_exhausted,
    load_budget,
    save_budget,
)
from src.config import (
    AGENT_ID,
    JOB_QUEUE,
    RABBITMQ_URL,
    STATUS_QUEUE,
    VALIDATOR_QUEUE,
)
from src.models import (
    FactionStance,
    JobStatus,
    JobStatusUpdate,
    MessageEnvelope,
    MessageType,
    ResearchJob,
    ResearchPackage,
    ZoneData,
    ZoneExtraction,
    ZoneFailure,
)
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Packaging helpers (moved from pipeline.py per D6)
# ---------------------------------------------------------------------------


def _compute_quality_warnings(extraction: ZoneExtraction) -> list[str]:
    """Compute quality warnings based on content thresholds."""
    warnings: list[str] = []

    if len(extraction.zone.narrative_arc) < 200:
        warnings.append("shallow_narrative_arc")

    if extraction.npcs and all(not n.personality for n in extraction.npcs):
        warnings.append("no_npc_personality_data")

    has_antagonist_npc = any(
        n.occupation and any(
            keyword in n.occupation.lower()
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


def _apply_confidence_caps(
    extraction: ZoneExtraction,
    confidence: dict[str, float],
) -> dict[str, float]:
    """Apply mechanical confidence caps based on field completeness."""
    capped = dict(confidence)

    if not extraction.npcs:
        capped["npcs"] = min(capped.get("npcs", 0.0), 0.2)
    else:
        total = len(extraction.npcs)
        empty_personality = sum(1 for n in extraction.npcs if not n.personality)
        empty_role = sum(1 for n in extraction.npcs if not n.occupation)

        if empty_personality / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)
        if empty_role / total > 0.5:
            capped["npcs"] = min(capped.get("npcs", 0.0), 0.4)

    if not extraction.factions:
        capped["factions"] = min(capped.get("factions", 0.0), 0.2)

    return capped


class Daemon:

    def __init__(self):
        self._running = False
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def run(self):
        """Start the daemon — connect, declare queues, consume jobs."""
        logger.info("daemon_started", extra={"agent_id": AGENT_ID})
        self._running = True
        self._setup_signal_handlers()

        await self._connect_rabbitmq()
        await self._declare_queues()

        researcher = LoreResearcher()

        if not self._channel:
            logger.error("daemon_no_channel", extra={"reason": "RabbitMQ connection failed"})
            return

        await self._channel.set_qos(prefetch_count=1)

        queue = await self._channel.get_queue(JOB_QUEUE)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break
                await self._on_job_message(message, researcher)

        await self._shutdown()

    async def _declare_queues(self):
        """Declare job and status queues on RabbitMQ startup."""
        if not self._channel:
            return
        await self._channel.declare_queue(JOB_QUEUE, durable=True)
        await self._channel.declare_queue(STATUS_QUEUE, durable=True)
        await self._channel.declare_queue(VALIDATOR_QUEUE, durable=True)
        logger.info("queues_declared", extra={
            "job_queue": JOB_QUEUE,
            "status_queue": STATUS_QUEUE,
            "validator_queue": VALIDATOR_QUEUE,
        })

    async def _on_job_message(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
        researcher: LoreResearcher,
    ):
        """Callback for incoming job messages — parse, execute, ack/nack."""
        try:
            envelope = MessageEnvelope.model_validate_json(message.body)
            job = ResearchJob.model_validate(envelope.payload)
        except Exception:
            logger.error("job_message_parse_failed", exc_info=True)
            await message.nack(requeue=False)
            return

        logger.info("job_received", extra={"job_id": job.job_id, "zone": job.zone_name, "depth": job.depth})

        try:
            await self._execute_job(job, researcher)
            await message.ack()
        except Exception as exc:
            logger.error("job_failed", extra={"job_id": job.job_id}, exc_info=True)
            await self._publish_status(JobStatusUpdate(
                job_id=job.job_id,
                status=JobStatus.JOB_FAILED,
                error=str(exc),
            ))
            await message.nack(requeue=False)

    async def _execute_job(self, job: ResearchJob, researcher: LoreResearcher):
        """Wave-loop job executor — manages zones and depth expansion."""
        # Publish ACCEPTED
        await self._publish_status(JobStatusUpdate(
            job_id=job.job_id,
            status=JobStatus.ACCEPTED,
            zone_name=job.zone_name,
        ))

        # Load budget and persist any date-based reset
        budget = await load_budget()
        budget = check_daily_budget_reset(budget)
        await save_budget(budget)

        if is_daily_budget_exhausted(budget):
            raise RuntimeError("daily token budget exhausted")

        zones_completed: list[str] = []
        zones_pending: list[str] = [job.zone_name]
        zones_failed_list: list[ZoneFailure] = []
        current_depth = 0
        max_depth = job.depth

        publish_fn = self._make_publish_fn()
        zones_total = len(zones_pending)

        while zones_pending and current_depth <= max_depth:
            # Process current wave
            current_wave = list(zones_pending)
            zones_pending.clear()
            next_wave: list[str] = []

            for zone_name in current_wave:
                is_last_wave = current_depth >= max_depth

                # Publish ZONE_STARTED
                await self._publish_status(JobStatusUpdate(
                    job_id=job.job_id,
                    status=JobStatus.ZONE_STARTED,
                    zone_name=zone_name,
                    zones_completed=len(zones_completed),
                    zones_total=zones_total,
                ))

                try:
                    # Run orchestrator
                    result = await researcher.research_zone(
                        zone_name, skip_discovery=is_last_wave,
                    )

                    # Track tokens + persist budget
                    budget = add_tokens_used(budget, researcher.zone_tokens)
                    researcher.reset_zone_state()
                    await save_budget(budget)

                    # Package + publish to validator
                    package = self._assemble_package(result, zone_name)
                    envelope = MessageEnvelope(
                        source_agent=AGENT_ID,
                        target_agent="world_lore_validator",
                        message_type=MessageType.RESEARCH_PACKAGE,
                        payload=package.model_dump(mode="json"),
                    )
                    await publish_fn(envelope)

                    # Token observability log
                    logger.info("zone_tokens", extra={
                        "zone_name": zone_name,
                        "total_tokens": result.orchestrator_tokens + result.worker_tokens,
                        "orchestrator_tokens": result.orchestrator_tokens,
                        "worker_tokens": result.worker_tokens,
                    })

                    # Zone completed
                    zones_completed.append(zone_name)

                    # Next wave expansion
                    if not is_last_wave:
                        for z in result.discovered_zones:
                            if z not in zones_completed and z not in next_wave:
                                next_wave.append(z)

                    await self._publish_status(JobStatusUpdate(
                        job_id=job.job_id,
                        status=JobStatus.ZONE_COMPLETED,
                        zone_name=zone_name,
                        zones_completed=len(zones_completed),
                        zones_total=zones_total,
                    ))

                except Exception as exc:
                    logger.error("zone_failed", extra={
                        "job_id": job.job_id, "zone": zone_name,
                    }, exc_info=True)
                    # Track partial tokens even on failure
                    budget = add_tokens_used(budget, researcher.zone_tokens)
                    researcher.reset_zone_state()
                    await save_budget(budget)
                    zones_failed_list.append(ZoneFailure(
                        zone_name=zone_name,
                        error=str(exc),
                    ))

            # Prepare next wave
            if next_wave:
                zones_pending.extend(next_wave)
                zones_total += len(next_wave)
            current_depth += 1

        # Publish final status
        if zones_failed_list and not zones_completed:
            # Every zone failed — propagate as job failure so _on_job_message nacks
            failed_names = ", ".join(f.zone_name for f in zones_failed_list)
            raise RuntimeError(f"all zones failed: {failed_names}")
        elif zones_failed_list:
            await self._publish_status(JobStatusUpdate(
                job_id=job.job_id,
                status=JobStatus.JOB_PARTIAL_COMPLETED,
                zones_completed=len(zones_completed),
                zones_total=zones_total,
                zones_failed=zones_failed_list,
            ))
        else:
            await self._publish_status(JobStatusUpdate(
                job_id=job.job_id,
                status=JobStatus.JOB_COMPLETED,
                zones_completed=len(zones_completed),
                zones_total=zones_total,
            ))

    def _assemble_package(
        self,
        result: OrchestratorResult,
        zone_name: str,
    ) -> ResearchPackage:
        """Assemble ResearchPackage from orchestrator output.

        Applies mechanical quality gates (code decisions, not LLM decisions):
        quality warnings based on content thresholds, confidence caps based
        on field completeness.
        """
        extraction = ZoneExtraction(
            zone=result.zone_data or ZoneData(
                name=zone_name,
                narrative_arc="No narrative arc extracted — zone extraction failed.",
                political_climate="No political climate extracted.",
                connected_zones=["unknown"],
                era="unknown",
                confidence=0.0,
            ),
            npcs=result.npcs,
            factions=result.factions,
            lore=result.lore,
            narrative_items=result.narrative_items,
        )

        warnings = _compute_quality_warnings(extraction)

        confidence = result.cross_ref_result.confidence if result.cross_ref_result else {}
        confidence = _apply_confidence_caps(extraction, confidence)

        conflicts = result.cross_ref_result.conflicts if result.cross_ref_result else []

        return ResearchPackage(
            zone_name=zone_name,
            zone_data=extraction.zone,
            npcs=extraction.npcs,
            factions=extraction.factions,
            lore=extraction.lore,
            narrative_items=extraction.narrative_items,
            sources=result.sources,
            confidence=confidence,
            conflicts=conflicts,
            quality_warnings=warnings,
        )

    async def _publish_status(self, update: JobStatusUpdate):
        """Publish a job status update to the status queue."""
        if not self._channel:
            logger.warning("status_publish_skipped", extra={"reason": "no channel"})
            return

        envelope = MessageEnvelope(
            source_agent=AGENT_ID,
            target_agent="",
            message_type=MessageType.JOB_STATUS_UPDATE,
            payload=update.model_dump(mode="json"),
        )

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=envelope.model_dump_json().encode(),
                content_type="application/json",
            ),
            routing_key=STATUS_QUEUE,
        )
        logger.info("status_published", extra={
            "job_id": update.job_id, "status": update.status.value,
        })

    def _make_publish_fn(self):
        """Return an async callable that publishes a MessageEnvelope to RabbitMQ."""
        async def publish(envelope: MessageEnvelope):
            if not self._channel:
                logger.warning("rabbitmq_publish_skipped", extra={"reason": "no channel"})
                return
            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=envelope.model_dump_json().encode(),
                    content_type="application/json",
                ),
                routing_key=VALIDATOR_QUEUE,
            )
        return publish

    async def _connect_rabbitmq(self, max_retries: int = 5):
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

    async def _shutdown(self):
        """Clean shutdown — close RabbitMQ connections."""
        logger.info("daemon_shutdown")
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

    def _setup_signal_handlers(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_signal)
            except NotImplementedError:
                signal.signal(sig, lambda s, f: self._handle_signal())

    def _handle_signal(self):
        logger.info("signal_received")
        self._running = False


async def main():
    setup_logging()
    daemon = Daemon()
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
