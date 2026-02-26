# Code Dry-Run Report #2

**Scope**: `s_wiki_crawler/src/` (all source files) + `shared/crawl.py` + `docker-compose.yml`
**Design**: `.claude/specs/wiki-crawler/design.md`
**Reviewed**: 2026-02-26
**Context**: Post-fix review after dry-run #1 (3 bugs, 2 gaps fixed)

---

## Verification of Dry-Run #1 Fixes

| Finding | Status | Verification |
|---------|--------|-------------|
| B1 — No per-page exception handling in `_crawl_zone` | **Fixed** | `daemon.py`:236–285 wraps the per-URL block in try-except. `pages_failed` incremented, `already_crawled` updated, error logged with `exc_info=True`. |
| B2 — No exception handling in `_refresh_oldest_zone` | **Fixed** | `daemon.py`:197–202 wraps `_crawl_zone` in try-except. Exception logged, method returns `True` (work was attempted). |
| B3 — Missing `UnicodeDecodeError` catch in `_process_seed` | **Fixed** | `daemon.py`:139 now catches `(json.JSONDecodeError, ValidationError, UnicodeDecodeError)`. |
| G1 — MCP call return values unchecked in `storage.py` | **Fixed** | `storage.py`:139–142, 154–157, 166–169, 249–252 all check `result is None` and log warnings with operation, table/relation, and URL context. |
| G2 — No input sanitization on `zone_name` | **Fixed** | `models.py`:22–28 adds `field_validator` on both `zone_name` and `game` rejecting `..`, `/`, `\`, `\x00`. Tests added in `test_models.py` (6 new tests). |
| S1 — Deferred import in daemon.py | **Fixed** | `daemon.py`:45 imports `_url_to_record_id` at top-level alongside `store_page` and `store_page_with_change_detection`. |

---

## Bugs (will cause incorrect behavior)

### [B1] `_process_seed` error handler re-raises `UnicodeDecodeError` when generating `body_preview`
- **File**: `s_wiki_crawler/src/daemon.py`:142
- **Pass**: Pass 3 (Error Path Trace)
- **What**: The except block at line 139 catches `UnicodeDecodeError` (the B3 fix), but the error logging at line 142 calls `message.body.decode()[:500]` to produce a `body_preview`. If the exception was a `UnicodeDecodeError` from line 137, this second `.decode()` call will also raise `UnicodeDecodeError` — uncaught this time. The exception escapes `_process_seed`, propagates into the main loop, and crashes the daemon. The message is never rejected (left unacked).
- **Impact**: A single non-UTF-8 message crashes the daemon — the exact scenario B3 was supposed to prevent. The fix for B3 is incomplete without fixing this secondary decode.
- **Fix**: Use `errors="replace"` for the preview decode:
  ```python
  except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
      logger.warning("message_rejected", extra={
          "error": str(exc),
          "body_preview": message.body[:500].decode(errors="replace"),
      })
  ```

---

## Gaps (missing implementation)

None found.

---

## Warnings (potential issues)

### [W1] Synchronous file I/O in async context (carried from dry-run #1)
- **File**: `s_wiki_crawler/src/storage.py`:107, 120, 209, 219; `s_wiki_crawler/src/daemon.py`:319
- **Pass**: Pass 5 (Resource Management)
- **What**: `Path.write_text()`, `Path.read_text()`, and `Path.exists()` are synchronous calls that block the event loop.
- **Risk**: Acceptable for the current single-zone-at-a-time daemon. Would need `asyncio.to_thread()` if concurrency is added later. Not actionable now.

### [W2] `logging_config.py` creates new `LogRecord` per log message for key filtering (carried from dry-run #1)
- **File**: `s_wiki_crawler/src/logging_config.py`:27
- **Pass**: Pass 8 (Code Quality)
- **What**: `logging.LogRecord("").__dict__` is called inside `format()` on every log event to determine which keys are "extra" fields.
- **Risk**: Minor performance overhead under heavy logging. Not a correctness issue.
- **Fix**: Cache the default keys at class level:
  ```python
  _DEFAULT_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
  ```

---

## Style (code quality, conventions)

None found.

---

## Summary

| Bugs | Gaps | Warnings | Style |
|------|------|----------|-------|
| 1 | 0 | 2 | 0 |

**Verdict**: **FAIL** — B1 is a regression introduced by the incomplete B3 fix from dry-run #1. A non-UTF-8 message still crashes the daemon because the error handler itself calls `.decode()` without error handling. Single-line fix.

**Dry-run #1 fixes**: All 6 verified as correctly implemented.
