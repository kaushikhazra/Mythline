"""Checkpoint system for crash-resilient research state.

Persists research progress via Storage MCP's research_state collection.
On crash/restart, the daemon resumes from the last completed step.
"""

from __future__ import annotations

import json
from datetime import date

from src.config import AGENT_ID, MCP_STORAGE_URL, DAILY_TOKEN_BUDGET
from src.mcp_client import mcp_call
from src.models import ResearchCheckpoint


async def save_checkpoint(checkpoint: ResearchCheckpoint) -> None:
    await mcp_call(
        MCP_STORAGE_URL,
        "save_checkpoint",
        {"agent_id": AGENT_ID, "state": checkpoint.model_dump_json()},
    )


async def load_checkpoint() -> ResearchCheckpoint | None:
    result = await mcp_call(
        MCP_STORAGE_URL,
        "load_checkpoint",
        {"agent_id": AGENT_ID},
    )

    if not result or result == "null":
        return None

    if isinstance(result, str):
        data = json.loads(result)
    else:
        data = result

    if not data:
        return None

    return ResearchCheckpoint(**data)


async def delete_checkpoint() -> None:
    await mcp_call(
        MCP_STORAGE_URL,
        "delete_checkpoint",
        {"agent_id": AGENT_ID},
    )


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
