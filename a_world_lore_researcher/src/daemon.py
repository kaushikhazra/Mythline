"""Daemon — job consumer for the World Lore Researcher.

Connects to RabbitMQ, consumes research jobs from the job queue,
executes zone research pipelines with depth-based wave expansion,
and publishes status updates. Processes one job at a time (prefetch=1).
"""

from __future__ import annotations

import asyncio
import logging
import signal

import aio_pika

from src.agent import LoreResearcher
from src.checkpoint import (
    add_tokens_used,
    check_daily_budget_reset,
    delete_checkpoint,
    is_daily_budget_exhausted,
    list_checkpoints,
    load_budget,
    load_checkpoint,
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
    JobStatus,
    JobStatusUpdate,
    MessageEnvelope,
    MessageType,
    ResearchCheckpoint,
    ResearchJob,
    ZoneFailure,
)
from src.logging_config import setup_logging
from src.pipeline import PIPELINE_STEPS, run_pipeline

logger = logging.getLogger(__name__)

TOTAL_STEPS = len(PIPELINE_STEPS)


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
            # Clean up all per-zone checkpoints only after successful ack
            await self._cleanup_job_checkpoints(job.job_id)
        except Exception as exc:
            logger.error("job_failed", extra={"job_id": job.job_id}, exc_info=True)
            await self._publish_status(JobStatusUpdate(
                job_id=job.job_id,
                status=JobStatus.JOB_FAILED,
                error=str(exc),
            ))
            await message.nack(requeue=False)

    async def _execute_job(self, job: ResearchJob, researcher: LoreResearcher):
        """Wave-loop job executor — manages zones, depth, crash recovery."""
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

        # Crash recovery — scan for existing per-zone checkpoints
        zones_completed: list[str] = []
        zones_pending: list[str] = [job.zone_name]
        zones_failed_list: list[ZoneFailure] = []
        current_depth = 0
        max_depth = job.depth

        checkpoint_prefix = f"{AGENT_ID}:{job.job_id}:"
        existing_keys = await list_checkpoints(checkpoint_prefix)
        recovered_checkpoints: dict[str, ResearchCheckpoint] = {}

        for key in existing_keys:
            # Key format: {agent_id}:{job_id}:{zone_name}
            zone_name = key.removeprefix(checkpoint_prefix)
            if not zone_name:
                continue
            cp = await load_checkpoint(key)
            if not cp:
                continue
            recovered_checkpoints[zone_name] = cp
            if cp.current_step >= TOTAL_STEPS:
                # Fully completed — skip and recover discovered zones
                zones_completed.append(zone_name)
                if zone_name in zones_pending:
                    zones_pending.remove(zone_name)
                if max_depth > 0:
                    discovered = cp.step_data.get("discovered_zones", [])
                    for z in discovered:
                        if z not in zones_completed and z not in zones_pending:
                            zones_pending.append(z)
                logger.info("crash_recovery_skip_completed", extra={
                    "job_id": job.job_id, "zone": zone_name,
                    "discovered_recovered": len(cp.step_data.get("discovered_zones", [])),
                })
            else:
                # Partially completed — resume from last checkpointed step
                if zone_name not in zones_pending:
                    zones_pending.append(zone_name)
                logger.info("crash_recovery_resume_partial", extra={
                    "job_id": job.job_id, "zone": zone_name,
                    "current_step": cp.current_step,
                })

        # Determine starting depth from recovered checkpoints
        if recovered_checkpoints and zones_pending:
            max_pending_depth = 0
            for zn in zones_pending:
                cp = recovered_checkpoints.get(zn)
                if cp and cp.wave_depth > 0:
                    max_pending_depth = max(max_pending_depth, cp.wave_depth)
            if max_pending_depth > 0:
                current_depth = max_pending_depth
            elif job.zone_name in zones_completed and max_depth > 0:
                # Fallback for legacy checkpoints without wave_depth
                current_depth = 1
        elif job.zone_name in zones_completed and max_depth > 0:
            current_depth = 1

        publish_fn = self._make_publish_fn()
        zones_total = len(zones_pending) + len(zones_completed)

        while zones_pending and current_depth <= max_depth:
            # Process current wave
            current_wave = list(zones_pending)
            zones_pending.clear()
            next_wave: list[str] = []

            for zone_name in current_wave:
                # Determine whether to skip discovery for this zone
                is_last_wave = current_depth >= max_depth
                skip_steps: set[str] | None = None
                if is_last_wave:
                    skip_steps = {"discover_connected_zones"}

                # Publish ZONE_STARTED
                await self._publish_status(JobStatusUpdate(
                    job_id=job.job_id,
                    status=JobStatus.ZONE_STARTED,
                    zone_name=zone_name,
                    zones_completed=len(zones_completed),
                    zones_total=zones_total,
                ))

                try:
                    # Create or load per-zone checkpoint
                    checkpoint_key = f"{AGENT_ID}:{job.job_id}:{zone_name}"
                    checkpoint = await load_checkpoint(checkpoint_key)
                    if checkpoint and checkpoint.current_step >= TOTAL_STEPS:
                        # Already completed (crash recovery detected mid-wave)
                        zones_completed.append(zone_name)
                        continue
                    if not checkpoint:
                        checkpoint = ResearchCheckpoint(
                            job_id=job.job_id,
                            zone_name=zone_name,
                            wave_depth=current_depth,
                        )

                    # Build step progress callback for this zone
                    async def on_step_progress(
                        step_name: str, step_number: int, total_steps: int,
                        _job_id: str = job.job_id, _zone: str = zone_name,
                    ):
                        await self._publish_status(JobStatusUpdate(
                            job_id=_job_id,
                            status=JobStatus.STEP_PROGRESS,
                            zone_name=_zone,
                            step_name=step_name,
                            step_number=step_number,
                            total_steps=total_steps,
                        ))

                    # Run pipeline with step progress reporting
                    checkpoint = await run_pipeline(
                        checkpoint, researcher, publish_fn,
                        skip_steps=skip_steps,
                        on_step_progress=on_step_progress,
                    )

                    # Track token usage and persist budget
                    budget = add_tokens_used(budget, researcher.zone_tokens)
                    researcher.reset_zone_state()
                    await save_budget(budget)

                    # Zone completed
                    zones_completed.append(zone_name)

                    # Read discovered zones for next wave
                    if not is_last_wave:
                        discovered = checkpoint.step_data.get("discovered_zones", [])
                        for z in discovered:
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

    async def _cleanup_job_checkpoints(self, job_id: str):
        """Delete all per-zone checkpoints for a completed job."""
        prefix = f"{AGENT_ID}:{job_id}:"
        keys = await list_checkpoints(prefix)
        for key in keys:
            await delete_checkpoint(key)
        if keys:
            logger.info("job_checkpoints_cleaned", extra={
                "job_id": job_id, "count": len(keys),
            })

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
