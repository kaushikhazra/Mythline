# World Lore Researcher — Code Dry-Run Review

**Scope:** `a_world_lore_researcher/src/`
**Design:** `.claude/specs/world-lore-researcher/design.md`, `pipeline-fix.md`
**Reviewed:** 2026-02-22
**Reviewer:** Velasari (dry-run pass 1-9)

---

## BUGS (will cause incorrect behavior)

### B1 — Crash resume is broken: `_main_loop` resets checkpoint progress

**File:** `daemon.py:80-83`
**Pass:** 2 (Execution Path Trace)

`_pick_next_zone()` correctly detects an in-progress zone after crash (checks `zone_name` and `current_step > 0`). But `_main_loop` unconditionally resets `current_step=0` and `step_data={}` before calling `run_pipeline()`, destroying all accumulated progress.

**Example:** Daemon crashes at pipeline step 5. On restart, `_pick_next_zone` returns the in-progress zone. Then `_main_loop` resets `current_step` to 0 and empties `step_data`. The pipeline re-runs all 5 completed steps from scratch.

**Impact:** Checkpoint resume never works. Every crash restarts the zone from scratch, wasting all previously spent tokens and time. This defeats a core architectural feature.

**Fix:**

```python
zone = self._pick_next_zone(checkpoint)
...
if zone != checkpoint.zone_name or checkpoint.current_step == 0:
    # New zone — reset
    checkpoint.zone_name = zone
    checkpoint.current_step = 0
    checkpoint.step_data = {}
# else: resuming in-progress zone — keep current_step and step_data
```

---

### B2 — `_zone_discovery_agent` uses template with unformatted placeholders as system prompt

**File:** `agent.py:153-158`
**Pass:** 7 (Contract Violations)

`_zone_discovery_agent` is initialized with `system_prompt=load_prompt(__file__, "discover_zones")`. The `discover_zones.md` template contains `{zone_name}` and `{game_name}` placeholders. At init time these are loaded as literal text, so the system prompt sent to the LLM reads: `"Search for the zone '{zone_name}' in {game_name}"`.

Then `discover_connected_zones()` loads the SAME template, formats it with actual values, and sends it as the user prompt. The LLM gets the instruction twice — once broken (system), once correct (user).

**Impact:** LLM confusion. Likely still works because the user prompt has actual values, but the system prompt wastes context window tokens with malformed text.

**Fix:** Either (a) create a dedicated system prompt for zone discovery without placeholders, or (b) reuse `system_prompt.md`.

---

### B3 — `_shutdown()` doesn't protect channel/connection close

**File:** `daemon.py:154-157`
**Pass:** 3 (Error Path Trace)

If `self._channel.close()` throws (e.g., already closed, connection lost), `self._connection.close()` is never called.

**Impact:** RabbitMQ connection resource leak on error shutdown paths.

**Fix:**

```python
if self._channel:
    try:
        await self._channel.close()
    except Exception:
        logger.warning("channel_close_failed", exc_info=True)
if self._connection:
    try:
        await self._connection.close()
    except Exception:
        logger.warning("connection_close_failed", exc_info=True)
```

---

## GAPS (missing design implementation)

### G1 — No rate limiting on any external calls

**Files:** `pipeline.py`, `agent.py`, `mcp_client.py`
**Pass:** 1 (Design Conformance)
**Design ref:** Design → Rate Limiting

Design specifies `aiolimiter` token bucket at `RATE_LIMIT_REQUESTS_PER_MINUTE` for web search and crawler calls, a separate rate limiter for LLM calls, and `tenacity` retry with exponential backoff + jitter for all transient failures. None of this exists in the code.

---

### G2 — No per-step token budget checks

**File:** `pipeline.py`
**Pass:** 1 (Design Conformance)
**Design ref:** Design → Budget Checks

Design says "Before each LLM call: Pre-flight token estimation via `tokencost`. If call would exceed `PER_CYCLE_TOKEN_BUDGET` → stop pipeline." The code has `is_daily_budget_exhausted()` but only checks it in `daemon.py` before picking a zone — not before each LLM call. `add_tokens_used()` exists in `checkpoint.py` but is never called. `daily_tokens_used` is always 0.

---

### G3 — No validation response handling

**File:** `daemon.py`
**Pass:** 1 (Design Conformance)
**Design ref:** Design → Daemon Lifecycle, Error Handling → "Validator rejects package"

The daemon publishes research packages to the validator queue but never subscribes to its own RabbitMQ queue (`agent.world_lore_researcher`) to receive `ValidationResult` messages. No re-research cycle on rejection. No queue declaration at all.

---

### G4 — No user decision handling at zone forks

**Files:** `daemon.py`, `pipeline.py`
**Pass:** 1 (Design Conformance)
**Design ref:** Design → Research Pipeline Step 9

Design says "At forks (multiple next zones) → post `user_decision_required` to user channel." Code just appends all discovered zones to `progression_queue` without fork detection, user decision publishing, or response waiting.

---

### G5 — No RabbitMQ queue declaration or subscription

**File:** `daemon.py`
**Pass:** 1 (Design Conformance)
**Design ref:** Design → RabbitMQ Topology

`_connect_rabbitmq()` opens a connection and channel but never declares queues (`agent.world_lore_researcher`, `agent.world_lore_validator`, `user.decisions`) or subscribes to any queue. The daemon can only publish, never receive.

---

### G6 — `mcp_call()` has no exception handling or retry logic

**File:** `mcp_client.py:27-50`
**Pass:** 3 (Error Path Trace)
**Design ref:** Design → Error Handling

If Storage MCP is unreachable, `streamablehttp_client()` throws an unhandled exception. This propagates through `save_checkpoint()` and crashes the daemon. `load_checkpoint()` also throws. No retry, no circuit breaker. Daemon crash-loops if Storage MCP is temporarily down.

---

## WARNINGS (potential issues)

### W1 — Signal handler doesn't interrupt `asyncio.sleep()`

**File:** `daemon.py:70,77,103`
**Pass:** 6 (Concurrency & Async)

`_handle_signal()` sets `self._running = False`, but `asyncio.sleep()` is not interruptible. The daemon continues sleeping for up to `RESEARCH_CYCLE_DELAY_MINUTES` (5 min default) before checking `_running`.

**Risk:** Slow graceful shutdown — up to 5 minutes to respond to SIGTERM in Docker.

---

### W2 — `load_checkpoint()` failure before try/finally leaks RabbitMQ

**File:** `daemon.py:53-64`
**Pass:** 5 (Resource Management)

`_connect_rabbitmq()` runs at line 48, but `load_checkpoint()` at line 53 is before the `try/finally` at line 61. If `load_checkpoint()` throws, `_shutdown()` is never called and the RabbitMQ connection leaks.

**Risk:** Connection leak on startup crash.

---

### W3 — Completed zone can be re-researched on crash timing

**File:** `daemon.py:85-96`
**Pass:** 2 (Execution Path Trace)

Between `run_pipeline()` completing and the final `save_checkpoint()`, if the daemon crashes, the checkpoint on disk still shows the zone as in-progress. Combined with B1, the zone would be fully re-researched and the package re-sent to the validator.

**Risk:** Duplicate research packages, wasted tokens. Mitigated once B1 is fixed — resume would just re-run the last step.

---

### W4 — `StructuredJsonFormatter` creates temporary `LogRecord` on every call

**File:** `logging_config.py:58`
**Pass:** 8 (Code Quality)

`logging.LogRecord("", 0, "", 0, "", (), None).__dict__` is evaluated on every `format()` call to get default field names. This allocates a throwaway object per log line.

**Risk:** Performance overhead under high logging volume.

---

### W5 — Dead code: `web_search()`, `web_search_news()`, `crawl_urls()`

**File:** `mcp_client.py:57-107`
**Pass:** 2 (Execution Path Trace)

These functions are vestiges of the old direct-call pipeline. After the pipeline fix, the agent calls web search via MCP toolset and crawl4ai via the registered tool. These helpers are never called.

**Risk:** Code confusion, maintenance burden.

---

## STYLE (code quality, conventions)

### S1 — Pipeline steps 1-5 are near-identical

**File:** `pipeline.py:109-193`

Five functions differ only in their `instructions` string. Could be a single parametrized function or a data-driven loop. ~80 lines reducible to ~20.

---

### S2 — Magic number 5000 for content truncation

**File:** `agent.py:147`

Hardcoded truncation limit for content returned to the agent's context window. Should be a named constant.

---

### S3 — Magic number `[:10]` for raw content limit

**File:** `agent.py:208`

Hardcoded limit of 10 content blocks passed to extraction. Should be a named constant.

---

## SUMMARY

| Category | Count |
|----------|-------|
| Bugs | 3 |
| Gaps | 6 |
| Warnings | 5 |
| Style | 3 |

**Verdict:** FAIL — B1 breaks crash resume (a core architectural feature). G1-G6 represent significant missing design elements.

**Notes on gaps:** G3-G5 (validation handling, user decisions, queue subscription) are downstream features that depend on the World Lore Validator existing. G1-G2 (rate limiting, budget tracking) and G6 (MCP resilience) are infrastructure gaps within the researcher itself. These may be intentionally deferred but should be tracked.
