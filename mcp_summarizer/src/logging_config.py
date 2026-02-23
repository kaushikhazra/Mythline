"""Structured JSON logging with service_id in every event."""

import json
import logging
import sys

SERVICE_ID = "mcp_summarizer"

# Keys that may appear as structured extras in log calls
_EXTRA_KEYS = (
    "input_tokens", "output_tokens", "compression_ratio",
    "num_chunks", "strategy", "max_tokens_per_chunk",
    "combined_tokens", "target", "pass", "topic",
    "raw_blocks", "raw_chars", "summary_chars", "model",
)


class JsonFormatter(logging.Formatter):
    """JSON log formatter that includes service_id in every event."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname.lower(),
            "service_id": SERVICE_ID,
            "event": record.getMessage(),
            "logger": record.name,
        }
        for key in _EXTRA_KEYS:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging() -> None:
    """Configure structured JSON logging for the summarizer service."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
