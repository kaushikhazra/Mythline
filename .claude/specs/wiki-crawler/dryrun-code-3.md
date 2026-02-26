# Code Dry-Run Report #3

**Scope**: `s_wiki_crawler/src/` (all source files) + `shared/crawl.py` + `docker-compose.yml`
**Design**: `.claude/specs/wiki-crawler/design.md`
**Reviewed**: 2026-02-26
**Context**: Post-fix review after dry-run #2 (1 bug fixed: body_preview decode)

---

## Verification of Dry-Run #2 Fix

| Finding | Status | Verification |
|---------|--------|-------------|
| B1 — `body_preview` decode re-raises `UnicodeDecodeError` | **Fixed** | `daemon.py`:142 now uses `message.body[:500].decode(errors="replace")`. Slice before decode, replacement characters for invalid bytes. Cannot raise. |

---

## Cumulative Fix Status (Dry-Run #1 + #2)

| # | Finding | Fixed In | Current Status |
|---|---------|----------|----------------|
| B1 | No per-page exception handling in `_crawl_zone` | DR#1 fix | `daemon.py`:236–285 — try-except wraps per-URL block |
| B2 | No exception handling in `_refresh_oldest_zone` | DR#1 fix | `daemon.py`:197–202 — try-except wraps `_crawl_zone` |
| B3 | Missing `UnicodeDecodeError` catch in `_process_seed` | DR#1 fix | `daemon.py`:139 — catches `UnicodeDecodeError` |
| B3+ | `body_preview` decode re-raises in error handler | DR#2 fix | `daemon.py`:142 — `decode(errors="replace")` |
| G1 | MCP call return values unchecked in `storage.py` | DR#1 fix | `storage.py`:139,154,166,249 — None checks + warning logs |
| G2 | No input sanitization on `zone_name`/`game` | DR#1 fix | `models.py`:22–28 — `field_validator` rejects traversal chars |
| S1 | Deferred import in daemon.py | DR#1 fix | `daemon.py`:45 — top-level import |

---

## Bugs (will cause incorrect behavior)

None found.

---

## Gaps (missing implementation)

None found.

---

## Warnings (potential issues)

### [W1] Synchronous file I/O in async context (carried from dry-run #1)
- **File**: `s_wiki_crawler/src/storage.py`:107, 120, 209, 219; `s_wiki_crawler/src/daemon.py`:319
- **Pass**: Pass 5 (Resource Management)
- **What**: `Path.write_text()`, `Path.read_text()`, and `Path.exists()` are synchronous calls that block the event loop.
- **Risk**: Acceptable for the current single-zone-at-a-time daemon (prefetch=1). Would need `asyncio.to_thread()` if concurrency is added later. Not actionable now.

### [W2] `logging_config.py` creates new `LogRecord` per log message for key filtering (carried from dry-run #1)
- **File**: `s_wiki_crawler/src/logging_config.py`:27
- **Pass**: Pass 8 (Code Quality)
- **What**: `logging.LogRecord("").__dict__` is called inside `format()` on every log event.
- **Risk**: Minor performance overhead under heavy logging. Not a correctness issue. Could be cached at class level.

---

## Style (code quality, conventions)

None found.

---

## Summary

| Bugs | Gaps | Warnings | Style |
|------|------|----------|-------|
| 0 | 0 | 2 | 0 |

**Verdict**: **PASS WITH WARNINGS** — All bugs and gaps from dry-runs #1 and #2 are resolved. The two remaining warnings (sync file I/O, LogRecord allocation) are architectural trade-offs acceptable for the current single-zone-at-a-time daemon design. No action needed.
