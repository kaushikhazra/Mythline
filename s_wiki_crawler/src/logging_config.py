"""Structured JSON logging configuration for the Wiki Crawler service."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from src.config import SERVICE_ID


class StructuredFormatter(logging.Formatter):
    """Format log records as structured JSON events."""

    # Cache default LogRecord keys once at class level (avoids per-message allocation
    # and works on Python 3.12 which requires all positional args).
    _DEFAULT_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "service_id": SERVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "logger": record.name,
        }

        # Merge extra fields (passed via logger.info("msg", extra={...}))
        for key, value in record.__dict__.items():
            if key not in self._DEFAULT_KEYS and key not in event:
                event[key] = value

        return json.dumps(event, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for the service."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
