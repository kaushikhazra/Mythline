# Agent Anatomy — File by File

Detailed breakdown of each file's purpose, patterns, and rationale.

Files are split into two groups: **core** (every agent has these) and **agent-specific** (added as needed).

---

## Core Files

These are present in every agent, no exceptions.

### `agent.py` — The LLM Brain

The core intelligence module. Wraps pydantic-ai `Agent` instances and exposes async methods that callers invoke — whether that caller is a daemon loop, a RabbitMQ consumer, an HTTP handler, or another agent.

**Pattern:**

```python
from shared.config_loader import load_mcp_config
from shared.prompt_loader import load_prompt

class SomeAgent:
    AGENT_ID = "some_agent"

    def __init__(self):
        # LLM_MODEL is the full pydantic-ai identifier e.g. "openrouter:openai/gpt-4o-mini"
        # Agent code never hardcodes the provider — it comes from config/env.
        self._primary_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            output_type=SomeOutputModel,  # Structured output via Pydantic model
            retries=2,
        )

        # MCP servers loaded from config, not constructed here
        self._mcp_servers = load_mcp_config(__file__)

        self._tool_agent = Agent(
            LLM_MODEL,
            system_prompt=load_prompt(__file__, "system_prompt"),
            toolsets=self._mcp_servers,
            retries=2,
        )

    async def do_something(self, ...) -> SomeOutputModel:
        template = load_prompt(__file__, "do_something")
        prompt = template.format(...)
        result = await self._primary_agent.run(prompt, usage_limits=...)
        return result.output
```

**Key decisions:**
- Multiple Agent instances per class is fine — each has a different system prompt or output type
- `output_type=PydanticModel` forces structured LLM output
- `retries=2` gives the LLM two more chances on validation failures
- MCP servers that need context management use `AsyncExitStack`:

```python
from contextlib import AsyncExitStack

async with AsyncExitStack() as stack:
    for server in self._mcp_servers:
        await stack.enter_async_context(server)
    result = await self._tool_agent.run(prompt)
```

---

### `config.py` — Environment Configuration

All env vars are read here. Code provides sensible defaults. No env reads scattered across other modules.

**Pattern:**

```python
import os

def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))

AGENT_ID = os.getenv("AGENT_ID", "some_agent")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter:openai/gpt-4o-mini")
DAILY_TOKEN_BUDGET = _int_env("DAILY_TOKEN_BUDGET", 500_000)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://mythline:mythline@localhost:5672/")
```

**Key:** `LLM_MODEL` is the full pydantic-ai model identifier including the provider prefix (e.g., `openrouter:openai/gpt-4o-mini`, `ollama:llama3`, `anthropic:claude-sonnet-4-20250514`). The agent never hardcodes a provider — switching providers is a config change, not a code change. Provider-specific env vars (like `OPENROUTER_API_KEY`) are set in the environment, not read by agent code.

**Why centralized:** When debugging config issues, there's exactly one file to check. Grep for env var names leads here, nowhere else.

---

### `models.py` — Data Models

Pure Pydantic models. No logic, no side effects. These define the data shapes the agent works with.

**Conventions:**
- All models inherit from `BaseModel`
- Use `Field(default_factory=list)` for mutable defaults
- Enums for fixed categories (e.g., `SourceTier`)
- Models must roundtrip: `Model.model_validate_json(instance.model_dump_json())`

---

### `logging_config.py` — Structured Logging

Sets up Python's logging to emit JSON with correlation fields.

**Pattern:**
- Custom `StructuredJsonFormatter` on root logger
- All agent code uses standard `logging.getLogger(__name__)`
- Extra fields passed via `logger.info("event", extra={...})`
- Suppresses noisy third-party loggers (httpx, httpcore, etc.)
- Call `setup_logging()` once at process startup, regardless of invocation method

---

### `conftest.py` — Test Environment Setup

Lives at agent root (not in tests/). Adds repo root to `sys.path` so `shared/` is importable.

```python
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
```

---

### `config/mcp_config.json` — MCP Server Declaration

Declarative MCP wiring. No Python touches this — it's pure configuration.

```json
{
  "mcpServers": {
    "search": { "url": "${MCP_WEB_SEARCH_URL}", "timeout": 30 },
    "crawler": { "url": "${MCP_WEB_CRAWLER_URL}", "timeout": 60 }
  }
}
```

Key name = tool prefix. URLs support env var expansion.

---

### `prompts/*.md` — All Prompts

Two categories:
- **System prompts** — Agent persona/instructions. Sections: Persona, Task, Instructions, Constraints, Output.
- **Task templates** — User prompts with `{placeholders}`. Formatted at call site.

Naming: matches the logical purpose (e.g., `extract_zone_data.md`, `cross_reference_task.md`).

---

## Agent-Specific Files

These are added based on the agent's invocation model and domain needs. Not every agent has all of these.

### `daemon.py` — Continuous Polling Loop

For agents that run as long-lived daemons, polling for work on a cycle.

**When to use:** Knowledge acquisition agents (researchers, validators) that continuously scan for work.

**Pattern:**
- `Daemon` class with `start()` method
- Signal handlers for graceful shutdown
- Main loop: pick work → process → checkpoint → sleep
- Budget tracking with daily reset
- Entry point: `python -m src.daemon`

### `pipeline.py` — Multi-Step Processing

For agents whose work is a sequence of discrete, checkpointed steps.

**When to use:** Agents with multi-phase workflows (search → crawl → extract → validate).

**Pattern:**
- Named step list: `PIPELINE_STEPS = ["step_a", "step_b", ...]`
- Step functions: `async def step_a(checkpoint) -> checkpoint`
- Each step is checkpointed — crash at step 5 resumes from step 5
- Rate limiting via `aiolimiter.AsyncLimiter`
- Retry via `tenacity` with exponential backoff + jitter

### `mcp_client.py` — Raw MCP HTTP Calls

For agents that need to call MCP tools programmatically (without LLM involvement).

**When to use:** Pipeline steps that call MCP tools directly — code decides which tool, not the LLM.

**Pattern:**
```python
async def mcp_call(base_url, tool_name, arguments):
    async with httpx.AsyncClient() as client:
        response = await client.post(base_url, json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        })
```

**Why separate from agent.py:** The agent uses pydantic-ai's MCP integration (LLM decides tools). The pipeline uses direct HTTP calls (code decides tools). Different mechanisms, different modules.

### `checkpoint.py` — State Persistence

For agents that need crash-resilient state across restarts.

**When to use:** Any agent with long-running work that would be expensive to redo from scratch.

**Pattern:**
- Checkpoint model (Pydantic) tracks: current step, step data, budget usage, completed work
- `save_checkpoint()` / `load_checkpoint()` — thin wrappers over MCP storage calls

### Other Possibilities

Agents may introduce modules not listed here, depending on their invocation model:
- `consumer.py` — RabbitMQ message consumer (event-driven agents)
- `api.py` — HTTP endpoint (on-demand agents)
- `scheduler.py` — Cron-like scheduling logic

The blueprint doesn't prescribe these. The agent's design document should specify which invocation model it uses and which modules it needs.
