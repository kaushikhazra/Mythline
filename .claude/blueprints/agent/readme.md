# Agent Blueprint

This is the architectural blueprint for building any Mythline agent. It captures structural decisions learned from building the World Lore Researcher — the first v2 agent. These patterns are non-negotiable for all agents unless explicitly discussed and revised.

## Index

- [readme.md](readme.md) — This file. Design philosophy, folder structure, wiring, and constraints.
- [anatomy.md](anatomy.md) — Detailed file-by-file anatomy with purpose and patterns.
- [docker.md](docker.md) — Dockerfile and docker-compose conventions.

---

## Design Philosophy: Single Responsibility + Composition at Every Level

Three principles govern every agent design decision:

1. **Know the patterns** — the catalog below lists agentic design patterns with rough domain fit and source links. Use them as a compass when designing agent interactions.
2. **Compose freely** — real problems cross domain lines. Mix patterns as needed. The domain groupings are guidance, not fences.
3. **Single Responsibility governs every agent** — each agent has one responsibility. An orchestrator orchestrates — it does not also do web search. If it needs web search, it calls a web search agent as a tool. If a class or agent accumulates a second responsibility, decompose it into smaller single-responsibility pieces and compose them via an aggregator (traditional code) or orchestrator with tools (agentic code).

### Agentic Design Patterns Catalog

The domains below are fuzzy — patterns can serve multiple purposes and often combine.

#### Hierarchical Task Management

Breaking down and delegating complex work.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Orchestrator-Workers** | Central agent dynamically decomposes and delegates to sub-agents | [Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) |
| **Supervisor / Hierarchical** | Manager oversees a predefined roster of specialist agents | [CrewAI Docs](https://docs.crewai.com/en/concepts/agents), [LangGraph Blog](https://blog.langchain.com/langgraph-multi-agent-workflows/) |

#### Job Handling

Executing work — serial, parallel, or hybrid.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Sequential Pipeline** | Fixed linear chain — output of one feeds the next | [Azure AI Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns), [Anthropic](https://www.anthropic.com/research/building-effective-agents) |
| **Fan-out / Fan-in** | Same input to multiple agents simultaneously, results merge | [Azure AI Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns), [Anthropic](https://www.anthropic.com/research/building-effective-agents) |
| **Handoff** | Mid-task transfer of control + context to another agent | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/handoffs/), [AutoGen Docs](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/handoffs.html) |
| **Swarm** | Decentralized peer network — any agent can hand off to any other, no coordinator | [OpenAI Swarm](https://github.com/openai/swarm) |

#### Research

Exploring a problem space, converging on answers.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Group Chat / Roundtable** | Shared conversation thread with a chat manager controlling turns | [Azure AI Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns), [AutoGen Docs](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/intro.html) |
| **Multi-Agent Debate** | Adversarial argumentation — agents critique each other, judge decides | [AutoGen Docs](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/intro.html), [ACL 2025](https://arxiv.org/abs/2502.19130) |
| **Voting / Quorum / Consensus** | Independent answers + decision protocol (majority, weighted, unanimity) | [ACL 2025](https://arxiv.org/abs/2502.19130) |
| **Blackboard** | Agents collaborate through shared state, not messages — read/write structured data | [Classical AI](https://en.wikipedia.org/wiki/Blackboard_system), [arXiv 2025](https://arxiv.org/html/2507.01701v1) |

#### Output Validation

Quality assurance — applies across all domains.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Reflection / Self-Critique** | Single agent reviews its own output and revises | [Andrew Ng](https://x.com/AndrewYNg/status/1773393357022298617), [AutoGen Docs](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/intro.html) |
| **Evaluator-Optimizer** | Generator + Critic in a feedback loop until quality threshold | [Anthropic](https://www.anthropic.com/research/building-effective-agents), [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html) |
| **Voting / Quorum / Consensus** | Cross-cutting — also used for validation via independent agreement | (same as Research) |

#### Heterogeneous Problems

When the problem requires fundamentally different skills combined.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Mixture of Agents (MoA)** | Layered aggregation — neural-net-inspired layers of proposers and aggregators | [Together AI Paper](https://arxiv.org/abs/2406.04692), [AutoGen Docs](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/mixture-of-agents.html) |

#### Guarded Decisions

When autonomous choice carries risk.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **Human-in-the-Loop Gate** | Autonomous execution with approval checkpoints at risk points | [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [Azure AI Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) |

#### Dynamic Agent Environment

Agents aren't known upfront, discovered or dispatched at runtime.

| Pattern | Core Idea | Source |
|---------|-----------|--------|
| **A2A Discovery** | Protocol-based capability cards — agents advertise, discover, and delegate dynamically | [Google A2A Protocol](https://a2a-protocol.org/latest/) |
| **Routing / Triage** | Classifier dispatches incoming requests to the right specialist | [Anthropic](https://www.anthropic.com/research/building-effective-agents), [OpenAI Swarm](https://github.com/openai/swarm) |

---

## Folder Structure

Every agent follows this exact layout. No exceptions.

```
a_{agent_name}/
├── Dockerfile
├── .env.example
├── pyproject.toml
├── conftest.py                  # Adds repo root to sys.path for shared/
├── config/
│   ├── mcp_config.json          # Declarative MCP server wiring
│   └── *.yml                    # Agent-specific config (e.g., sources.yml)
├── prompts/
│   ├── system_prompt.md         # System prompt for the primary agent
│   └── *.md                     # All other prompts — system or user-facing
├── src/
│   ├── __init__.py
│   ├── agent.py                 # LLM-powered brain (pydantic-ai Agents)
│   ├── config.py                # Env var loading, agent-specific config
│   ├── models.py                # Pydantic data models
│   ├── logging_config.py        # Structured JSON logging setup
│   └── ...                      # Agent-specific modules (see below)
└── tests/
    ├── __init__.py
    ├── test_agent.py
    ├── test_models.py
    ├── test_config.py
    ├── test_integration.py      # Gated behind INTEGRATION_TESTS=true
    └── test_*.py                # One test file per source module
```

The core files above (`agent.py`, `config.py`, `models.py`, `logging_config.py`) are present in every agent. Beyond these, agents add modules as needed for their specific concerns — there is no prescribed set. Examples from the World Lore Researcher:

- `daemon.py` — continuous polling loop (because it runs as a long-lived daemon)
- `pipeline.py` — multi-step search/crawl/extract workflow
- `checkpoint.py` — crash-resilient state persistence
- `mcp_client.py` — raw HTTP calls to MCP services (non-LLM)

A different agent might instead have a `consumer.py` (RabbitMQ listener), an `api.py` (HTTP endpoint), or none of these — just `agent.py` invoked by another agent directly.

### Naming Convention

- Root folder: `a_{agent_name}/` — the `a_` prefix identifies agents
- Python: `snake_case` everywhere (PEP 8)
- Prompt files: `snake_case.md` — name matches the logical purpose

---

## Core Wiring Rules

### 1. All prompts live in `.md` files

**No hardcoded prompt strings in Python code. Ever.**

Prompts are loaded via the shared utility:

```python
from shared.prompt_loader import load_prompt

# System prompts — passed to Agent constructor
system = load_prompt(__file__, "system_prompt")

# User/task prompts — loaded as templates, formatted with .format()
template = load_prompt(__file__, "extract_zone_data")
prompt = template.format(zone_name=zone_name, source_info=source_info)
```

Two types of prompts:
- **System prompts** — define agent persona and behaviour. Passed to `Agent(system_prompt=...)`.
- **Task prompts** — templates with `{placeholders}`. Loaded, formatted, passed to `agent.run(prompt)`.

### 2. MCP servers are declared in JSON config

**No manual `MCPServerStreamableHTTP(...)` construction in Python code.**

MCP wiring is configuration, not logic. Each agent declares its servers in `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "search": { "url": "${MCP_WEB_SEARCH_URL}", "timeout": 30 },
    "crawler": { "url": "${MCP_WEB_CRAWLER_URL}", "timeout": 60 }
  }
}
```

- The dict key becomes `tool_prefix` automatically
- URLs use `${ENV_VAR}` or `${ENV_VAR:-default}` syntax
- All constructor args (timeout, headers, etc.) pass through

Loaded via:

```python
from shared.config_loader import load_mcp_config

self._mcp_servers = load_mcp_config(__file__)
agent = Agent(model, toolsets=self._mcp_servers)
```

### 3. Configuration layering

```
Docker compose env → .env (per agent) → default in code
```

Every config value has a sensible default in code. `.env.example` documents all variables. Docker compose can override anything.

```python
# config.py pattern
AGENT_ID = os.getenv("AGENT_ID", "world_lore_researcher")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter:openai/gpt-4o-mini")  # Full provider:model
DAILY_TOKEN_BUDGET = _int_env("DAILY_TOKEN_BUDGET", 500_000)
```

`LLM_MODEL` carries the full pydantic-ai identifier including provider prefix. Agent code never hardcodes a provider — switching from OpenRouter to Ollama is a config change, not a code change. Provider-specific env vars (e.g., `OPENROUTER_API_KEY`) flow through the environment to the provider library; agent code does not read them.

### 4. Shared utilities via `shared/`

Cross-agent code lives in `shared/` at the repo root:

```python
from shared.prompt_loader import load_prompt      # Prompt loading
from shared.config_loader import load_mcp_config  # MCP config loading
```

For local dev, `conftest.py` at the agent root adds the repo root to `sys.path`. For Docker, the Dockerfile copies `shared/` into the container.

### 5. Structured JSON logging

Every agent emits structured JSON logs with correlation fields:

```python
from src.logging_config import setup_logging
setup_logging()  # Call once at process startup
```

Log fields: `agent_id`, `domain`, `timestamp`, `level`, `event`, `logger`, plus any extras.

### 6. Tests mirror source

One test file per source module. Naming: `test_{module}.py`.

- `monkeypatch.setenv` for env vars (not `@patch`) — because pydantic-ai providers read from `os.getenv` internally
- Integration tests gated behind `INTEGRATION_TESTS=true`
- Shared utility tests in `test_shared.py`
- Test file for every source file — no untested modules

---

## Constraints

These are hard rules. Push back if anyone suggests violating them.

1. **No prompt strings in Python** — all in `.md` files under `prompts/`
2. **No MCP server construction in Python** — all in `config/mcp_config.json`
3. **No Pydantic models outside `models.py`** — every `BaseModel` subclass lives in `models.py`. Agent output types, extraction wrappers, result containers — all in `models.py`. Dataclasses used as agent runtime deps (e.g., `ResearchContext`) stay in `agent.py`.
4. **No inline imports** — all imports at the top of the file
5. **No emojis in code**
6. **Every module has tests** — no untested source files
7. **Integration tests are gated** — never run in CI without explicit opt-in
8. **Each agent is self-contained** — own Dockerfile, .env, pyproject.toml, venv
9. **Shared code goes in `shared/`** — never duplicate utilities across agents
