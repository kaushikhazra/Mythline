"""Daemon loop — main entry point for the World Lore Researcher.

Handles lifecycle: startup, main research loop, shutdown, signal handling.
Connects to RabbitMQ for validator communication and user decisions.
"""

from __future__ import annotations

import asyncio
import logging
import signal

import aio_pika

from src.checkpoint import (
    check_daily_budget_reset,
    is_daily_budget_exhausted,
    load_checkpoint,
    save_checkpoint,
)
from src.config import (
    AGENT_ID,
    RABBITMQ_URL,
    RESEARCH_CYCLE_DELAY_MINUTES,
    STARTING_ZONE,
)
from src.models import ResearchCheckpoint
from src.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class Daemon:

    def __init__(self):
        self._running = False
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def start(self):
        logger.info("daemon_started", extra={"agent_id": AGENT_ID})
        self._running = True
        self._setup_signal_handlers()

        await self._connect_rabbitmq()

        checkpoint = await load_checkpoint()
        if checkpoint:
            logger.info("checkpoint_loaded", extra={"zone": checkpoint.zone_name, "step": checkpoint.current_step})
            checkpoint = check_daily_budget_reset(checkpoint)
        else:
            logger.info("no_checkpoint_found", extra={"starting_zone": STARTING_ZONE})
            checkpoint = ResearchCheckpoint(zone_name=STARTING_ZONE)

        try:
            await self._main_loop(checkpoint)
        finally:
            await self._shutdown(checkpoint)

    async def _main_loop(self, checkpoint: ResearchCheckpoint):
        while self._running:
            if is_daily_budget_exhausted(checkpoint):
                logger.warning("budget_exhausted", extra={"type": "daily", "tokens_used": checkpoint.daily_tokens_used})
                await asyncio.sleep(RESEARCH_CYCLE_DELAY_MINUTES * 60)
                checkpoint = check_daily_budget_reset(checkpoint)
                continue

            zone = self._pick_next_zone(checkpoint)
            if not zone:
                logger.info("no_zones_to_research")
                await asyncio.sleep(RESEARCH_CYCLE_DELAY_MINUTES * 60)
                continue

            logger.info("research_cycle_started", extra={"zone_name": zone})
            checkpoint.zone_name = zone
            checkpoint.current_step = 0
            checkpoint.step_data = {}

            checkpoint = await run_pipeline(checkpoint)

            checkpoint.completed_zones.append(zone)
            if zone in checkpoint.progression_queue:
                checkpoint.progression_queue.remove(zone)
            if zone in checkpoint.priority_queue:
                checkpoint.priority_queue.remove(zone)

            checkpoint.zone_name = ""
            checkpoint.current_step = 0
            checkpoint.step_data = {}
            await save_checkpoint(checkpoint)

            logger.info("research_cycle_completed", extra={"zone_name": zone})

            if not self._running:
                break

            await asyncio.sleep(RESEARCH_CYCLE_DELAY_MINUTES * 60)

    def _pick_next_zone(self, checkpoint: ResearchCheckpoint) -> str | None:
        if checkpoint.zone_name and checkpoint.current_step > 0:
            return checkpoint.zone_name

        for zone in checkpoint.priority_queue:
            if zone not in checkpoint.completed_zones:
                return zone

        for zone in checkpoint.progression_queue:
            if zone not in checkpoint.completed_zones:
                return zone

        if STARTING_ZONE not in checkpoint.completed_zones:
            return STARTING_ZONE

        return None

    async def _connect_rabbitmq(self):
        try:
            self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self._channel = await self._connection.channel()
            logger.info("rabbitmq_connected")
        except Exception:
            logger.warning("rabbitmq_connection_failed", exc_info=True)

    async def _shutdown(self, checkpoint: ResearchCheckpoint):
        logger.info("daemon_shutdown", extra={"reason": "signal"})
        self._running = False

        try:
            await save_checkpoint(checkpoint)
        except Exception:
            logger.error("checkpoint_save_failed_on_shutdown", exc_info=True)

        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()

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
    from src.logging_config import setup_logging
    setup_logging()
    daemon = Daemon()
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
