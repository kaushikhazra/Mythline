"""Unit tests for src/logging_config.py — JSON formatter and setup."""

import json
import logging

from src.logging_config import JsonFormatter, SERVICE_ID, setup_logging


def test_service_id_constant():
    assert SERVICE_ID == "mcp_summarizer"


def test_json_formatter_produces_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test_event", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["event"] == "test_event"
    assert parsed["level"] == "info"
    assert parsed["service_id"] == "mcp_summarizer"
    assert parsed["logger"] == "test"
    assert "timestamp" in parsed


def test_json_formatter_includes_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="summarization_complete", args=(), exc_info=None,
    )
    record.input_tokens = 50000
    record.output_tokens = 5000
    record.compression_ratio = 10.0
    record.num_chunks = 7
    record.strategy = "semantic"
    record.model = "openai/gpt-4o-mini"
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["input_tokens"] == 50000
    assert parsed["output_tokens"] == 5000
    assert parsed["compression_ratio"] == 10.0
    assert parsed["num_chunks"] == 7
    assert parsed["strategy"] == "semantic"
    assert parsed["model"] == "openai/gpt-4o-mini"


def test_json_formatter_omits_absent_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="simple_event", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "input_tokens" not in parsed
    assert "model" not in parsed


def test_json_formatter_includes_exception():
    formatter = JsonFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="failed", args=(), exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "test error" in parsed["exception"]
    assert "ValueError" in parsed["exception"]
    assert "Traceback" in parsed["exception"]


def test_setup_logging_configures_root():
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)
    assert root.level == logging.INFO


def test_setup_logging_clears_existing_handlers():
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())
    root.addHandler(logging.StreamHandler())
    assert len(root.handlers) >= 2
    setup_logging()
    assert len(root.handlers) == 1
