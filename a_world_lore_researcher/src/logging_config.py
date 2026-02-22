"""Structured JSON logging for the World Lore Researcher agent.

Emits all log events as structured JSON with base fields:
agent_id, domain, timestamp, level, event.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from src.config import AGENT_ID

DOMAIN = "world_lore"

EVENT_TYPES = [
    "daemon_started",
    "checkpoint_loaded",
    "research_cycle_started",
    "pipeline_step_started",
    "pipeline_step_completed",
    "search_executed",
    "crawl_executed",
    "conflict_detected",
    "package_sent",
    "validation_received",
    "validation_rejected",
    "fork_detected",
    "user_decision_requested",
    "user_decision_received",
    "budget_warning",
    "budget_exhausted",
    "error",
    "daemon_shutdown",
]


class StructuredJsonFormatter(logging.Formatter):

    _DEFAULT_RECORD_KEYS = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__
    ) | {"extra_fields", "message"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "agent_id": AGENT_ID,
            "domain": DOMAIN,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        elif isinstance(getattr(record, "args", None), dict):
            pass

        for key in vars(record):
            if key not in self._DEFAULT_RECORD_KEYS:
                val = getattr(record, key)
                if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                    log_entry[key] = val

        return json.dumps(log_entry, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
