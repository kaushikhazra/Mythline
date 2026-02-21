"""Checkpoint system for crash-resilient research state.

Persists research progress via Storage MCP's research_state collection.
On crash/restart, the daemon resumes from the last completed step.
"""

from __future__ import annotations

import json
from datetime import date

import httpx

from src.config import AGENT_ID, MCP_STORAGE_URL, DAILY_TOKEN_BUDGET
from src.models import ResearchCheckpoint


async def save_checkpoint(checkpoint: ResearchCheckpoint) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_STORAGE_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "save_checkpoint",
                    "arguments": {
                        "agent_id": AGENT_ID,
                        "state": checkpoint.model_dump_json(),
                    },
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()


async def load_checkpoint() -> ResearchCheckpoint | None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_STORAGE_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "load_checkpoint",
                    "arguments": {
                        "agent_id": AGENT_ID,
                    },
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()

        content = _extract_mcp_text(result)
        if not content or content == "null":
            return None

        data = json.loads(content)
        if not data:
            return None

        return ResearchCheckpoint(**data)


async def delete_checkpoint() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_STORAGE_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "delete_checkpoint",
                    "arguments": {
                        "agent_id": AGENT_ID,
                    },
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()


def check_daily_budget_reset(checkpoint: ResearchCheckpoint) -> ResearchCheckpoint:
    today = date.today().isoformat()
    if checkpoint.last_reset_date != today:
        checkpoint.daily_tokens_used = 0
        checkpoint.last_reset_date = today
    return checkpoint


def is_daily_budget_exhausted(checkpoint: ResearchCheckpoint) -> bool:
    return checkpoint.daily_tokens_used >= DAILY_TOKEN_BUDGET


def add_tokens_used(checkpoint: ResearchCheckpoint, tokens: int) -> ResearchCheckpoint:
    checkpoint.daily_tokens_used += tokens
    return checkpoint


def _extract_mcp_text(response_json: dict) -> str | None:
    result = response_json.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content, list):
        for item in content:
            if item.get("type") == "text":
                return item.get("text")
    return None
