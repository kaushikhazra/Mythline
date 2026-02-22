# Research: Autonomous AI Agent Daemon Processes in Python

**Date:** 2026-02-21
**Purpose:** Evaluate libraries, frameworks, and patterns for running 10 AI agents as continuous background daemons with research-validate-store cycles.

---

## 1. Python Daemon Libraries

### 1.1 python-daemon (PEP 3143)

- **What:** Reference implementation of PEP 3143 for creating well-behaved Unix daemon processes
- **Status:** Mature but Unix-only. No Windows support
- **Verdict:** NOT RECOMMENDED for Mythline. Windows is the primary dev environment, and python-daemon is Unix-only. Also, it's a low-level primitive -- you'd still need to build scheduling, health monitoring, and recovery on top

### 1.2 daemonize

- **What:** Lightweight library to daemonize Python processes
- **Status:** Similar Unix-only limitation
- **Verdict:** Same issues as python-daemon. Too low-level

### 1.3 Supervisord (v4.3.0)

- **What:** Process control system for Unix-like OSes. Starts, monitors, and auto-restarts child processes
- **Key features:**
  - Config-driven (INI file per process)
  - Auto-restart on crash (configurable restart policies)
  - Process groups (start/stop all agents together or individually)
  - Web UI for monitoring (port 9001 by default)
  - Log management (stdout/stderr capture per process)
  - Event notifications (process state changes)
- **Architecture:** supervisord is the parent process of each managed process. Gets notified of child death via SIGCHLD and performs the appropriate restart action
- **Limitation:** Unix/Linux only. Does NOT run natively on Windows
- **Verdict:** Excellent for production Linux deployment, but not for Windows dev. Could use for deployment target

### 1.4 PM2

- **What:** Production process manager, originally for Node.js but supports Python
- **Key features:**
  - Auto-restart crashed processes
  - Built-in log management and rotation
  - Startup script generation (auto-start on boot)
  - Real-time monitoring dashboard (pm2 monit)
  - Cluster mode for load balancing
  - Graceful shutdown support
  - JSON/YAML ecosystem file for multi-process config
- **Python support:** `pm2 start script.py --interpreter python`
- **Cross-platform:** Works on Windows, Linux, macOS
- **Verdict:** STRONG CANDIDATE. Cross-platform, excellent monitoring, easy config. Requires Node.js runtime installed but that's already needed for the frontend

### 1.5 systemd

- **What:** Linux init system with service management
- **Key features:** Start/stop/restart, auto-restart policies, resource limits, dependency ordering
- **Limitation:** Linux only, requires root access for service files
- **Verdict:** Good for production Linux deployment alongside supervisord. Not for dev

### Summary: Process Management Recommendation

| Tool | Windows | Linux | Auto-restart | Monitoring | Complexity |
|------|---------|-------|-------------|------------|------------|
| python-daemon | No | Yes | No | No | Low |
| Supervisord | No | Yes | Yes | Web UI | Medium |
| PM2 | Yes | Yes | Yes | CLI+Web | Medium |
| systemd | No | Yes | Yes | journalctl | Low |

**Primary recommendation: PM2** for development + production (cross-platform)
**Production alternative: Supervisord or systemd** for Linux-only deployment

---

## 2. Task Scheduling Libraries

### 2.1 APScheduler (Advanced Python Scheduler)

- **Version:** 4.x (major rewrite, async-first) / 3.x (stable, widely used)
- **What:** In-process task scheduling with cron, interval, and date triggers
- **Key features:**
  - BlockingScheduler (standalone daemon) and BackgroundScheduler (within app)
  - Persistent job stores: SQLAlchemy, Redis, MongoDB, ZooKeeper
  - AsyncIOScheduler for async/await support
  - Configurable misfire grace time
  - Job coalescing (skip missed runs)
  - Thread-safe
- **APScheduler 4 changes:**
  - Concepts split into Task (callable), Schedule (trigger), Job (execution instance)
  - Combined scheduler types into single `Scheduler` class
  - Native async support throughout
  - Persistent storage survives process/node restarts
- **Fit for use case:** Each agent runs on an interval trigger with configurable delay. Persistent storage means agents resume where they left off after restart
- **Verdict:** STRONG CANDIDATE. Lightweight, no external dependencies (no broker needed), async-native in v4. Perfect for in-process scheduling of agent cycles

### 2.2 Celery + Celery Beat

- **What:** Distributed task queue with scheduler component
- **Key features:**
  - Distributed workers across machines
  - Multiple broker support (Redis, RabbitMQ)
  - Robust retry semantics with backoff
  - Rate limiting built-in
  - Task routing and priority
  - Result backend for task outcomes
  - Celery Beat for periodic scheduling
- **Complexity:** Requires message broker (Redis or RabbitMQ), separate worker processes, Beat scheduler process
- **Fit for use case:** Overkill for 10 agents on a single machine. Designed for distributed systems across multiple machines/nodes
- **Verdict:** NOT RECOMMENDED. Too much infrastructure overhead for 10 in-process agents. The broker, worker, and beat components add unnecessary complexity. Would only make sense if scaling to 100+ agents across multiple machines

### 2.3 schedule (Daniel Bader)

- **What:** Minimalist job scheduler ("cron for Python")
- **Key features:**
  - Simple, human-readable API: `schedule.every(10).minutes.do(job)`
  - Lightweight, no dependencies
  - In-process, single-thread
- **Limitations:**
  - No persistence (jobs lost on restart)
  - No async support
  - No built-in retry/error handling
  - Must run `schedule.run_pending()` in a loop
- **Verdict:** TOO SIMPLE. No persistence, no async, no error handling. Fine for scripts but not for production daemon agents

### Summary: Scheduling Recommendation

**Primary recommendation: APScheduler 4.x** -- Async-native, persistent job stores, configurable triggers, no external broker needed. Each agent's research-validate-store cycle becomes an interval-triggered task with configurable delay.

**Alternative for scale:** Celery if ever needing distributed workers across machines (unlikely for 10 agents).

---

## 3. Rate Limiting & Retry Libraries

### 3.1 Tenacity (Retry + Backoff)

- **What:** General-purpose retrying library for Python
- **Key features:**
  - Decorator-based: `@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))`
  - Exponential backoff with jitter: `min(initial * 2^n + random.uniform(0, jitter), maximum)`
  - Configurable stop conditions (max attempts, max delay, custom)
  - Configurable wait strategies (fixed, random, exponential, combined)
  - Full async support via `AsyncRetrying`
  - Retry on specific exceptions: `retry=retry_if_exception_type(RateLimitError)`
  - Before/after retry callbacks for logging
  - Statistics tracking (attempt count, total time)
- **LLM API usage pattern:**
  ```python
  @retry(
      wait=wait_random_exponential(min=1, max=60),
      stop=stop_after_attempt(6),
      retry=retry_if_exception_type((RateLimitError, APITimeoutError))
  )
  async def call_llm(prompt: str) -> str:
      return await client.chat.completions.create(...)
  ```
- **Verdict:** ESSENTIAL. Must-have for any LLM-calling code. Already the industry standard for LLM retry logic

### 3.2 aiolimiter

- **What:** Async rate limiter using token bucket algorithm
- **Key features:**
  - `AsyncLimiter(max_rate, time_period)` -- e.g., 10 requests per minute
  - Async context manager: `async with limiter: await call_api()`
  - Lightweight, pure Python, no dependencies
- **Fit for use case:** Control how many LLM API calls per minute across all 10 agents sharing a rate limit
- **Verdict:** RECOMMENDED as a complement to tenacity. Tenacity handles retry-after-failure; aiolimiter prevents hitting the limit in the first place

### 3.3 ratelimit

- **What:** Simple decorator-based rate limiter
- **Key features:**
  - `@limits(calls=15, period=900)` -- 15 calls per 15 minutes
  - Raises `RateLimitException` when exceeded
- **Limitation:** Synchronous only, no async support
- **Verdict:** NOT RECOMMENDED. No async support, and aiolimiter is better for async workloads

### 3.4 PyBreaker / aiobreaker (Circuit Breaker)

- **What:** Circuit breaker pattern implementation
- **Key features:**
  - Closed state: requests pass through normally
  - Open state: requests immediately fail (fast-fail) after N consecutive failures
  - Half-open state: after timeout, allow one test request
  - Configurable failure threshold, recovery timeout
  - aiobreaker: async fork of pybreaker (native asyncio)
- **Fit for use case:** If the LLM API is consistently failing (outage), stop hammering it. Let agents back off entirely and resume when the API recovers
- **Note:** aiobreaker maintenance is inactive (no new releases in 12+ months). pybreaker is more actively maintained
- **Verdict:** NICE TO HAVE. Adds resilience layer on top of tenacity. Prevents wasting tokens/money during API outages

### Summary: Resilience Stack Recommendation

**Layer 1 - Prevention:** aiolimiter -- Proactive rate limiting (don't exceed limits)
**Layer 2 - Recovery:** tenacity -- Exponential backoff retry on failures
**Layer 3 - Protection:** pybreaker -- Circuit breaker for sustained API outages

All three layers compose well together:
```python
# Pseudocode: All three layers
limiter = AsyncLimiter(10, 60)  # 10 requests per minute
breaker = CircuitBreaker(fail_max=5, reset_timeout=300)

@breaker
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def call_llm(prompt):
    async with limiter:
        return await client.chat.completions.create(...)
```

---

## 4. Token Budget Management

### 4.1 Tokenator

- **What:** Python library to monitor and calculate LLM token usage
- **Install:** `pip install tokenator`
- **Key features:**
  - Drop-in wrapper around existing LLM clients (3 lines of code to integrate)
  - Supports OpenAI, Anthropic, Google Gemini SDKs
  - Also supports OpenAI-compatible providers (Perplexity, DeepSeek, xAI -- and by extension, OpenRouter)
  - Usage queries by time period: `usage.last_hour()`, `usage.last_day()`, `usage.between(start, end)`
  - SQLite storage (zero config, local, no server needed)
  - Thread-safe
  - Async client support
  - Streaming support (with `stream_options={"include_usage": True}`)
  - Privacy-focused: no data sent externally
- **Usage:**
  ```python
  from openai import OpenAI
  from tokenator import tokenator_openai
  client = tokenator_openai(OpenAI(api_key="key"))
  # All calls through this client are automatically tracked
  ```
- **Verdict:** STRONG CANDIDATE. Lightweight, zero-config, fits perfectly with OpenRouter-based architecture. Can query usage per agent, per time window, to enforce budgets

### 4.2 TokenCost

- **What:** Calculate USD cost of LLM API calls before sending
- **Install:** `pip install tokencost`
- **Key features:**
  - Cost estimation for 400+ models
  - Token counting before sending (pre-flight cost check)
  - Uses TikToken (OpenAI's official tokenizer)
  - Anthropic Claude 3+ uses beta token counting API
- **Usage:**
  ```python
  from tokencost import calculate_prompt_cost
  cost = calculate_prompt_cost(messages, model="gpt-4o")
  if cost > budget_remaining:
      skip_this_cycle()
  ```
- **Verdict:** COMPLEMENTARY. Use alongside tokenator. TokenCost estimates cost BEFORE calling; Tokenator tracks actual usage AFTER calling. Together they provide both pre-flight budget checks and post-flight tracking

### 4.3 LiteLLM (LLM Gateway/Proxy)

- **What:** Python SDK + Proxy Server for calling 100+ LLMs through a unified OpenAI-compatible API
- **Key features:**
  - Virtual key management with per-key budgets
  - TPM (tokens per minute) and RPM (requests per minute) limits
  - Budget tracking per key/user/team
  - Load balancing across model deployments
  - Fallback routing (if one model fails, try another)
  - Rate limit enforcement (429 before reaching provider)
  - Distributed rate limiting via Redis
  - Cost tracking with Langfuse/LangSmith integration
- **Architecture options:**
  - SDK mode: Import as Python library, use directly
  - Proxy mode: Run as HTTP gateway, all agents call through it
- **Fit for use case:** Run LiteLLM proxy as a gateway. All 10 agents call through it. The proxy enforces per-agent budgets, rate limits, and provides centralized cost tracking
- **Verdict:** STRONG CANDIDATE for centralized LLM management. However, adds another service to run. Consider whether the overhead is justified for 10 agents vs. simpler tokenator + aiolimiter approach

### 4.4 Custom Budget Manager (Build-It Pattern)

Given Mythline's OpenRouter-based architecture, a custom budget manager might be simpler:
```python
class TokenBudgetManager:
    def __init__(self, daily_budget_tokens: int, agents: list):
        self.daily_budget = daily_budget_tokens
        self.used_today = 0
        self.per_agent_budget = daily_budget_tokens // len(agents)

    async def can_spend(self, agent_id: str, estimated_tokens: int) -> bool:
        return self.agent_usage[agent_id] + estimated_tokens <= self.per_agent_budget

    async def record_usage(self, agent_id: str, tokens_used: int):
        self.agent_usage[agent_id] += tokens_used
        self.used_today += tokens_used
```

### Summary: Token Budget Recommendation

**Minimum viable:** Tokenator (tracking) + aiolimiter (rate limiting) + custom budget check
**Production-grade:** LiteLLM proxy as centralized gateway with built-in budget/rate enforcement
**Cost estimation:** TokenCost for pre-flight cost checks before expensive operations

---

## 5. Agent-Specific Daemon Frameworks

### 5.1 Temporal (Durable Execution)

- **What:** Distributed workflow orchestration engine with durable execution
- **Key features for AI agents:**
  - **Crash recovery:** Workflows resume exactly where they left off after failures
  - **State persistence:** Execution history stored in database (Cassandra/MySQL/PostgreSQL)
  - **Automatic retries:** Activities retry with configurable policies
  - **Long-running workflows:** Can run for days/months
  - **Horizontal scalability:** Workers across machines
  - **Observability:** Built-in execution visibility
  - **Token savings:** Workflows recover from point of failure instead of rerunning LLM calls
- **Pydantic AI Integration:**
  - `TemporalAgent` wrapper available (pydantic-ai has official Temporal support)
  - Separates Workflows (deterministic agent logic) from Activities (LLM calls, tool usage)
  - Model interactions and tool execution offloaded to Temporal activities
  - Pre-register model instances or use provider factories
  - Custom activity configuration (timeouts, retry policies)
- **Learning curve:** ~1 month for team to become productive
- **Infrastructure:** Requires Temporal Server (self-hosted or Temporal Cloud)
- **Verdict:** MOST ROBUST option. The Pydantic AI integration is a huge plus since Mythline already uses Pydantic AI. However, significant infrastructure overhead and learning curve. Best suited when you truly need durable execution guarantees (expensive LLM calls that must not be lost)

### 5.2 CrewAI

- **What:** Framework for orchestrating role-playing, autonomous AI agents
- **Key features:**
  - Two-layer architecture: Crews (agent collaboration) + Flows (event-driven orchestration)
  - Autonomous decision-making
  - Manager-level agents can reassign tasks dynamically
  - Sequential, parallel, and conditional task execution
  - Built for production: reliability, observability, cost control
- **Limitation:** Designed for task-oriented collaboration (crew solves a problem together), not for daemon-style continuous background processing. No built-in daemon/scheduling concept
- **Verdict:** NOT A FIT. CrewAI is for task-oriented multi-agent collaboration, not for long-running daemon processes. Different paradigm than what's needed

### 5.3 LangGraph

- **What:** Framework for building stateful, multi-step agent applications as graphs
- **Key features:**
  - Graph-based agent orchestration (nodes + edges)
  - State management between steps
  - Checkpointing and persistence
  - Human-in-the-loop support
  - Reached v1.0 in October 2025
- **Limitation:** Focused on single-invocation agent graphs, not on daemon scheduling. Would need external scheduling to run graphs periodically
- **Verdict:** NOT A FIT for the daemon use case. Good for agent logic but doesn't solve the daemon/scheduling/process management problem

### 5.4 AutoGPT

- **What:** Autonomous AI agent that can operate with minimal human intervention
- **Key features:**
  - Continuous operation toward goals
  - Breaks down goals into subtasks
  - Self-evaluating and self-adjusting
- **Limitation:** General-purpose autonomous agent, not a framework for building daemon systems
- **Verdict:** NOT A FIT. Different paradigm (single autonomous agent, not 10 scheduled daemon agents)

### Summary: Framework Recommendation

**For durable execution:** Temporal + Pydantic AI integration. Worth the investment if LLM calls are expensive and must not be lost on crashes
**For daemon scheduling:** APScheduler (not an agent framework, but solves the actual scheduling problem)
**NOT useful for daemons:** CrewAI, LangGraph, AutoGPT -- these solve agent collaboration/orchestration, not daemon process management

---

## 6. Health Monitoring & Self-Healing

### 6.1 Heartbeat Pattern

- **What:** Each agent periodically sends a heartbeat signal. A monitor watches for missed heartbeats
- **Implementation options:**
  - Shared memory (multiprocessing.Value with timestamps)
  - File-based (each agent writes timestamp to a file)
  - Redis pub/sub (if Redis is available)
  - UDP heartbeat (lightweight network signal)
- **Detection:** If heartbeat missed for N seconds, assume stalled/crashed. Trigger restart
- **Fit for use case:** Each of the 10 agents updates its heartbeat at the start of each cycle. A supervisor coroutine checks all heartbeats every 30 seconds

### 6.2 Process Watchdog Patterns

- **External watchdog:** Separate process monitors agent processes, restarts crashed ones
- **Self-healing loop:** Agent wraps its own main loop in try/except with restart logic
- **Parent-child:** Main process spawns agent processes, monitors via `is_alive()`, respawns on death
- **Combined approach (recommended):**
  ```python
  # Agent self-healing (inner layer)
  async def agent_loop():
      while True:
          try:
              await research_validate_store_cycle()
              await asyncio.sleep(configured_delay)
          except Exception as e:
              log_error(e)
              await asyncio.sleep(backoff_delay)

  # Supervisor (outer layer)
  async def supervisor():
      while True:
          for agent in agents:
              if agent.is_stalled():
                  await agent.restart()
          await asyncio.sleep(30)
  ```

### 6.3 Health Check Endpoints

- **Pattern:** Each agent exposes health status via a shared data structure or HTTP endpoint
- **Metrics to track:**
  - Last successful cycle timestamp
  - Current state (idle, researching, validating, storing)
  - Error count (rolling window)
  - Consecutive failure count
  - Token usage (current cycle, daily total)
  - Average cycle duration
- **Implementation:** FastAPI health endpoint (already using FastAPI for web backend) that aggregates all agent statuses

### 6.4 Graceful Shutdown

- **Pattern:** Handle SIGTERM/SIGINT signals to complete current cycle before stopping
- **Implementation:**
  ```python
  shutdown_event = asyncio.Event()

  def signal_handler(sig, frame):
      shutdown_event.set()

  async def agent_loop():
      while not shutdown_event.is_set():
          await run_cycle()
          await asyncio.sleep(delay)
      await cleanup()
  ```

---

## 7. Recommended Architecture

### 7.1 Option A: Lightweight (APScheduler + asyncio)

**Best for:** Getting started quickly, simple deployment, single-machine

```
[Main Process]
  |
  +-- APScheduler (interval triggers per agent)
  |     |
  |     +-- Agent 1: research -> validate -> store (every 5 min)
  |     +-- Agent 2: research -> validate -> store (every 10 min)
  |     +-- ...
  |     +-- Agent 10: research -> validate -> store (every 15 min)
  |
  +-- Supervisor Coroutine (health monitor, every 30s)
  |
  +-- Budget Manager (shared token budget enforcement)
  |
  +-- FastAPI Health Endpoint (status dashboard)

Resilience: tenacity (retry) + aiolimiter (rate limit) + pybreaker (circuit breaker)
Tracking: tokenator (usage) + tokencost (pre-flight cost)
Process Manager: PM2 (manages the main process, auto-restart)
```

**Pros:**
- Simple, single process
- No external infrastructure (no broker, no Temporal server)
- APScheduler persistence means agents resume after restart
- All agents share a single event loop (efficient for I/O-bound LLM calls)
- Easy to debug (single process, single log stream)

**Cons:**
- Single point of failure (one process crash kills all agents)
- No durable execution (if crash mid-LLM-call, that call is lost)
- GIL limits CPU-bound work (not an issue for I/O-bound LLM agents)

### 7.2 Option B: Multi-Process (APScheduler + multiprocessing)

**Best for:** Isolation between agents, crash containment

```
[Supervisor Process]
  |
  +-- Agent Process 1 (own APScheduler, own event loop)
  +-- Agent Process 2
  +-- ...
  +-- Agent Process 10
  |
  +-- Health Monitor (checks heartbeats, restarts crashed agents)
  +-- Budget Manager (shared via Redis or multiprocessing.Manager)

Process Manager: PM2 or Supervisord (manages supervisor process)
```

**Pros:**
- Agent crash doesn't kill other agents
- Independent restart per agent
- Better resource isolation

**Cons:**
- More complex shared state management
- Higher memory usage (Python process per agent)
- Needs IPC for budget management (Redis or shared memory)

### 7.3 Option C: Temporal + Pydantic AI (Durable Execution)

**Best for:** Mission-critical operations where LLM calls are expensive and must not be lost

```
[Temporal Server (self-hosted or Cloud)]
  |
  +-- Worker Process
  |     +-- Agent 1 Workflow (scheduled, durable)
  |     +-- Agent 2 Workflow
  |     +-- ...
  |     +-- Agent 10 Workflow
  |
  +-- Temporal Web UI (monitoring, debugging)

Each workflow:
  1. Schedule trigger -> Start workflow
  2. Activity: Research (LLM calls, retried on failure)
  3. Activity: Validate (LLM calls, retried on failure)
  4. Activity: Store (database writes, retried on failure)
  5. Sleep -> Wait for next cycle
```

**Pros:**
- Durable execution (survives any crash, resumes exactly where it left off)
- Built-in retry, timeout, and failure handling
- Excellent observability (Temporal Web UI)
- Token savings (no re-running LLM calls after recovery)
- Pydantic AI has official integration
- Scalable to many workers

**Cons:**
- Significant infrastructure (Temporal Server + database)
- Steep learning curve (~1 month)
- Overkill for research agents that can safely re-run cycles
- More complex deployment

---

## 8. Final Recommendations

### For Mythline's Use Case (10 Research Agents)

**RECOMMENDED: Option A (Lightweight)** with these specific libraries:

| Concern | Library | Why |
|---------|---------|-----|
| Scheduling | APScheduler 4.x | Async-native, persistent jobs, interval triggers |
| Process management | PM2 | Cross-platform (Windows dev + Linux prod), auto-restart |
| Retry/backoff | tenacity | Industry standard, async support, exponential backoff with jitter |
| Rate limiting | aiolimiter | Token bucket, async, lightweight |
| Circuit breaker | pybreaker | Protect against sustained API outages |
| Token tracking | tokenator | Drop-in wrapper, SQLite storage, per-agent tracking |
| Cost estimation | tokencost | Pre-flight cost checks before expensive LLM calls |
| Health monitoring | Custom | FastAPI endpoint aggregating agent heartbeats and stats |

**Why not Temporal?** The research agents can safely re-run a failed cycle. If a crash happens mid-LLM-call, the worst case is re-doing one research cycle (a few API calls). The durable execution guarantee doesn't justify the infrastructure overhead. Temporal becomes worthwhile when a single failed operation costs significant money or is irreversible.

**Why not Celery?** 10 agents on one machine don't need distributed task queues. The broker and worker infrastructure adds complexity with no benefit at this scale.

**Why not CrewAI/LangGraph?** These solve agent collaboration, not daemon scheduling. They'd be used INSIDE an agent's logic, not for managing the agent lifecycle.

### Upgrade Path

If Mythline grows beyond 10 agents or needs multi-machine deployment:
1. Add Redis for shared state and rate limiting
2. Switch from APScheduler to Celery Beat for distributed scheduling
3. Consider Temporal for mission-critical workflows (video production pipeline)
4. Consider LiteLLM proxy for centralized LLM management

### Key Design Patterns

1. **Agent lifecycle:** Each agent is a class with `start()`, `stop()`, `run_cycle()`, `health_check()` methods
2. **Configurable delays:** Per-agent delay stored in config, adjustable without restart
3. **Exponential backoff:** On failure, delay doubles (with jitter) up to a max, resets on success
4. **Token budget:** Daily per-agent budget, checked before each cycle, tracked after each call
5. **Graceful shutdown:** Signal handlers complete current cycle before stopping
6. **Health dashboard:** FastAPI endpoint exposing all agent statuses as JSON

---

## Sources

- [Supervisord Documentation](https://www.supervisord.org/running.html)
- [PM2 vs Supervisord Comparison](https://stackshare.io/stackups/pm2-vs-supervisord)
- [PM2 Python Process Management](https://pm2.io/blog/2018/09/19/Manage-Python-Processes)
- [APScheduler GitHub](https://github.com/agronholm/apscheduler)
- [APScheduler User Guide](https://apscheduler.readthedocs.io/en/stable/userguide.html)
- [Scheduling Tasks: APScheduler vs Celery Beat](https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat)
- [Python Job Scheduling 2026 Overview](https://research.aimultiple.com/python-job-scheduling/)
- [Tenacity GitHub](https://github.com/jd/tenacity)
- [Tenacity Retries: Exponential Backoff Decorators 2026](https://johal.in/tenacity-retries-exponential-backoff-decorators-2026/)
- [OpenAI Rate Limits Cookbook](https://cookbook.openai.com/examples/how_to_handle_rate_limits)
- [ratelimit PyPI](https://pypi.org/project/ratelimit/)
- [Tokenator GitHub](https://github.com/ujjwalm29/tokenator)
- [TokenCost GitHub](https://github.com/AgentOps-AI/tokencost)
- [LiteLLM Budgets and Rate Limits](https://docs.litellm.ai/docs/proxy/users)
- [LiteLLM Rate Limit Tiers](https://docs.litellm.ai/docs/proxy/rate_limit_tiers)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [Langfuse Token and Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [Portkey Budget Limits](https://portkey.ai/blog/budget-limits-and-alerts-in-llm-apps/)
- [Pydantic AI Temporal Integration](https://ai.pydantic.dev/durable_execution/temporal/)
- [Temporal Python SDK GitHub](https://github.com/temporalio/sdk-python)
- [Temporal + OpenAI Integration](https://www.infoq.com/news/2025/09/temporal-aiagent/)
- [Building Production-Grade AI Agents with PydanticAI + Temporal](https://medium.com/@simoncalabrese94/pydanticai-temporal-codeact-c7c5fadb1a99)
- [Celery vs Temporal Comparison](https://pedrobuzzi.hashnode.dev/celery-vs-temporalio)
- [Top AI Agent Frameworks 2026](https://www.shakudo.io/blog/top-9-ai-agent-frameworks)
- [Agentic Frameworks in 2026: What Actually Works](https://zircon.tech/blog/agentic-frameworks-in-2026-what-actually-works-in-production/)
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [PyBreaker GitHub](https://github.com/danielfm/pybreaker)
- [aiobreaker GitHub](https://github.com/arlyon/aiobreaker)
- [circuitbreaker PyPI](https://pypi.org/project/circuitbreaker/)
- [Python Asyncio for LLM Concurrency](https://www.newline.co/@zaoyang/python-asyncio-for-llm-concurrency-best-practices--bc079176)
- [Process Watchdog GitHub](https://github.com/diffstorm/processWatchdog)
- [Python Process Watchdog Pattern](https://github.com/i404788/process-watchdog)
- [Python Multiprocessing Shared State](https://hevalhazalkurt.com/blog/advanced-shared-state-management-in-python-multiprocessing/)
