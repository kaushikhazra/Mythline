"""Checkpoint system for crash-resilient research state.

Persists research progress via Storage MCP's research_state collection.
On crash/restart, the daemon resumes from the last completed step.

Per-job, per-zone checkpoints use composite keys: {agent_id}:{job_id}:{zone_name}.
Budget state is tracked separately under {agent_id}:budget.
"""

from __future__ import annotations

import json
from datetime import date

from src.config import AGENT_ID, MCP_STORAGE_URL, DAILY_TOKEN_BUDGET
from src.mcp_client import mcp_call
from src.models import BudgetState, ResearchCheckpoint


async def save_checkpoint(checkpoint: ResearchCheckpoint, checkpoint_key: str) -> None:
    """Save a per-zone checkpoint with composite key."""
    await mcp_call(
        MCP_STORAGE_URL,
        "save_checkpoint",
        {"agent_id": checkpoint_key, "state": checkpoint.model_dump_json()},
    )


async def load_checkpoint(checkpoint_key: str) -> ResearchCheckpoint | None:
    """Load a per-zone checkpoint by composite key."""
    result = await mcp_call(
        MCP_STORAGE_URL,
        "load_checkpoint",
        {"agent_id": checkpoint_key},
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


async def delete_checkpoint(checkpoint_key: str) -> None:
    """Delete a checkpoint by composite key."""
    await mcp_call(
        MCP_STORAGE_URL,
        "delete_checkpoint",
        {"agent_id": checkpoint_key},
    )


async def list_checkpoints(prefix: str) -> list[str]:
    """List checkpoint keys matching a prefix.

    Used for crash recovery — scanning for existing per-zone checkpoints
    matching a job's key pattern (e.g., "world_lore_researcher:job123:").
    """
    result = await mcp_call(
        MCP_STORAGE_URL,
        "list_checkpoints",
        {"prefix": prefix},
    )

    if not result:
        return []

    if isinstance(result, str):
        return json.loads(result)

    if isinstance(result, list):
        return result

    return []


# --- Budget State ---


async def save_budget(budget: BudgetState) -> None:
    """Save budget state under composite key {agent_id}:budget."""
    await mcp_call(
        MCP_STORAGE_URL,
        "save_checkpoint",
        {"agent_id": f"{AGENT_ID}:budget", "state": budget.model_dump_json()},
    )


async def load_budget() -> BudgetState:
    """Load budget state. Returns fresh state if none exists."""
    result = await mcp_call(
        MCP_STORAGE_URL,
        "load_checkpoint",
        {"agent_id": f"{AGENT_ID}:budget"},
    )

    if not result or result == "null":
        return BudgetState()

    if isinstance(result, str):
        data = json.loads(result)
    else:
        data = result

    if not data:
        return BudgetState()

    return BudgetState(**data)


# --- Budget Helpers ---


def check_daily_budget_reset(budget: BudgetState) -> BudgetState:
    """Reset daily token count if the date has changed."""
    today = date.today().isoformat()
    if budget.last_reset_date != today:
        budget.daily_tokens_used = 0
        budget.last_reset_date = today
    return budget


def is_daily_budget_exhausted(budget: BudgetState) -> bool:
    """Check if the daily token budget has been reached."""
    return budget.daily_tokens_used >= DAILY_TOKEN_BUDGET


def add_tokens_used(budget: BudgetState, tokens: int) -> BudgetState:
    """Add tokens to the daily usage counter."""
    budget.daily_tokens_used += tokens
    return budget
