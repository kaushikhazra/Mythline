"""Tests for structured JSON logging configuration."""

import json
import logging

from src.logging_config import (
    DOMAIN,
    EVENT_TYPES,
    StructuredJsonFormatter,
    setup_logging,
)


class TestEventTypes:
    def test_has_25_event_types(self):
        assert len(EVENT_TYPES) == 25

    def test_contains_key_events(self):
        assert "daemon_started" in EVENT_TYPES
        assert "daemon_shutdown" in EVENT_TYPES
        assert "job_received" in EVENT_TYPES
        assert "job_failed" in EVENT_TYPES
        assert "zone_failed" in EVENT_TYPES
        assert "status_published" in EVENT_TYPES


class TestStructuredJsonFormatter:
    def setup_method(self):
        self.formatter = StructuredJsonFormatter()

    def test_formats_as_json(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="daemon_started",
            args=None,
            exc_info=None,
        )
        output = self.formatter.format(record)
        data = json.loads(output)
        assert data["event"] == "daemon_started"
        assert data["level"] == "info"
        assert data["domain"] == DOMAIN
        assert "agent_id" in data
        assert "timestamp" in data

    def test_includes_extra_fields(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="research_cycle_started",
            args=None,
            exc_info=None,
        )
        record.zone_name = "elwynn_forest"
        record.step = 1
        output = self.formatter.format(record)
        data = json.loads(output)
        assert data["zone_name"] == "elwynn_forest"
        assert data["step"] == 1

    def test_warning_level(self):
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="budget_exhausted",
            args=None,
            exc_info=None,
        )
        output = self.formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "warning"

    def test_error_level(self):
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error",
            args=None,
            exc_info=None,
        )
        record.error_type = "ConnectionError"
        output = self.formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "error"
        assert data["error_type"] == "ConnectionError"


class TestSetupLogging:
    def test_configures_root_logger(self):
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) >= 1

        handler = root.handlers[0]
        assert isinstance(handler.formatter, StructuredJsonFormatter)

    def test_suppresses_noisy_loggers(self):
        setup_logging()
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("aio_pika").level == logging.WARNING
