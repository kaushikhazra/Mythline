# Code Dry-Run Report #1

**Scope**: `s_wiki_crawler/src/` (all source files) + `shared/crawl.py` + `docker-compose.yml`
**Design**: `.claude/specs/wiki-crawler/design.md`
**Reviewed**: 2026-02-26

---

## Bugs (will cause incorrect behavior)

### [B1] `_crawl_zone` has no per-page exception handling — single page failure crashes entire zone
- **File**: `s_wiki_crawler/src/daemon.py`:231–264
- **Pass**: Pass 3 (Error Path Trace)
- **What**: The inner loop over `selected` URLs calls `store_page` / `store_page_with_change_detection` without any try-except. If any page-level operation raises (e.g., corrupt `.meta.json` sidecar during refresh, filesystem permission error, unexpected MCP response shape), the exception propagates out of `_crawl_zone`, killing the entire zone crawl.
- **Impact**: Violates the design's "Fail-forward principle: No single page failure stops the zone crawl. Failed pages are logged and skipped." In Mode A, the message is rejected to DLQ. In Mode B (refresh), the daemon crashes (see B2).
- **Fix**: Wrap the per-URL block in a try-except inside the `for search_result in selected:` loop:
  ```python
  for search_result in selected:
      try:
          crawl_result = await crawl_page(search_result.url, self.throttle)
          already_crawled.add(search_result.url)
          # ... store + link discovery ...
      except Exception as exc:
          pages_failed += 1
          logger.error("page_processing_error", extra={
              "zone": zone_name, "url": search_result.url, "error": str(exc),
          }, exc_info=True)
          already_crawled.add(search_result.url)
  ```

### [B2] `_refresh_oldest_zone` has no exception handling — daemon crashes on refresh failure
- **File**: `s_wiki_crawler/src/daemon.py`:197
- **Pass**: Pass 3 (Error Path Trace)
- **What**: `_refresh_oldest_zone` calls `self._crawl_zone(zone_name, game, is_refresh=True)` without try-except. Any exception propagates into the main loop (`run()`), which also lacks a try-except around the Mode B branch. The daemon terminates ungracefully.
- **Impact**: A single refresh failure (network blip, corrupt sidecar, MCP timeout) kills the daemon permanently. Compare with `_process_seed` which correctly catches exceptions and rejects to DLQ.
- **Fix**: Wrap `_crawl_zone` call in `_refresh_oldest_zone`:
  ```python
  try:
      await self._crawl_zone(zone_name, game, is_refresh=True)
  except Exception as exc:
      logger.error("refresh_crawl_error", extra={
          "zone": zone_name, "error": str(exc),
      }, exc_info=True)
  return True
  ```

### [B3] `_process_seed` doesn't catch `UnicodeDecodeError` from malformed message bodies
- **File**: `s_wiki_crawler/src/daemon.py`:137
- **Pass**: Pass 3 (Error Path Trace)
- **What**: `message.body.decode()` can raise `UnicodeDecodeError` if the message body is not valid UTF-8. The except clause only catches `(json.JSONDecodeError, ValidationError)`. A `UnicodeDecodeError` propagates out of `_process_seed` into the main loop and crashes the daemon.
- **Impact**: A single malformed binary message kills the daemon. Low probability (all publishers use JSON), but RabbitMQ queues can receive messages from any publisher.
- **Fix**: Add `UnicodeDecodeError` to the except tuple:
  ```python
  except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
  ```

---

## Gaps (missing implementation)

### [G1] MCP call return values not checked in storage.py — graph operations silently fail
- **File**: `s_wiki_crawler/src/storage.py`:124, 141, 153, 229
- **Pass**: Pass 7 (Contract Violations)
- **What**: `store_page` makes 3 MCP calls (`create_record`, `create_relation` x2) and ignores all return values. `store_page_with_change_detection` makes 1 MCP call (`update_record`) and ignores it. If Storage MCP is down or returns an error, `mcp_call` returns `None` and the code continues silently. Filesystem content is written but graph metadata is missing.
- **Design ref**: Error handling table — "Storage MCP unavailable: Retry with backoff, fail zone if persistent"
- **Risk**: Graph becomes inconsistent with filesystem. WLR or other consumers querying the graph won't find pages that exist on disk. Silent data loss.
- **Fix**: At minimum, log when MCP calls return `None`:
  ```python
  result = await mcp_call(MCP_STORAGE_URL, "create_record", {...})
  if result is None:
      logger.warning("graph_write_failed", extra={"table": "crawl_page", "url": crawl_result.url})
  ```

### [G2] No input sanitization on `zone_name` — path traversal possible
- **File**: `s_wiki_crawler/src/storage.py`:104
- **Pass**: Pass 9 (Security)
- **What**: `zone_name` from the RabbitMQ message is used directly in the file path: `f"{game}/{zone_name}/{category}/{page_slug}.md"`. If `zone_name` contains `../`, it creates a path traversal. E.g., `zone_name = "../../../tmp/pwned"` writes outside `CRAWL_CACHE_ROOT`.
- **Design ref**: No explicit input validation section. CrawlJob model has `zone_name: str` with no constraints.
- **Risk**: In Docker (default deployment), impact is contained to the container filesystem. Outside Docker or with host-mounted volumes, files could be written anywhere the process has access.
- **Fix**: Validate `zone_name` in `CrawlJob` model or at the `store_page` boundary:
  ```python
  # Option A: Pydantic validator in CrawlJob
  @field_validator("zone_name")
  @classmethod
  def validate_zone_name(cls, v: str) -> str:
      if ".." in v or "/" in v or "\\" in v:
          raise ValueError(f"Invalid zone_name: {v}")
      return v

  # Option B: Check in store_page
  full_path = (Path(CRAWL_CACHE_ROOT) / relative_path).resolve()
  if not str(full_path).startswith(str(Path(CRAWL_CACHE_ROOT).resolve())):
      raise ValueError(f"Path traversal detected: {relative_path}")
  ```

---

## Warnings (potential issues)

### [W1] Synchronous file I/O in async context
- **File**: `s_wiki_crawler/src/storage.py`:107, 120, 197, 207, 217; `s_wiki_crawler/src/daemon.py`:305
- **Pass**: Pass 5 (Resource Management)
- **What**: `Path.write_text()`, `Path.read_text()`, and `Path.exists()` are synchronous calls that block the event loop. Wiki pages range 10KB–500KB.
- **Risk**: At 500KB file writes, the event loop is blocked for a few milliseconds — acceptable for a single-zone-at-a-time daemon. Would become a problem if concurrency is added later. Not actionable now.

### [W2] `logging_config.py` creates new `LogRecord` per log message for key filtering
- **File**: `s_wiki_crawler/src/logging_config.py`:27
- **Pass**: Pass 8 (Code Quality)
- **What**: `logging.LogRecord("").__dict__` is called inside `format()` on every log event to determine which keys are "extra" fields. This creates and discards a `LogRecord` object per log line.
- **Risk**: Minor performance overhead under heavy logging. Not a correctness issue.
- **Fix**: Cache the default keys at class level:
  ```python
  _DEFAULT_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
  ```

### [W3] `_url_to_slug` prefix stripping is case-sensitive for path but case-insensitive for comparison
- **File**: `s_wiki_crawler/src/storage.py`:46–48
- **Pass**: Pass 4 (Input Validation)
- **What**: `path.lower().startswith(prefix)` does a case-insensitive check, but then `path = path[len(prefix):]` slices the original (possibly mixed-case) path. This is correct behavior — preserving original casing for the slug before lowercasing later — but the two-step approach could confuse maintainers.
- **Risk**: None — the slug is lowercased at line 60. Purely a readability observation.

---

## Style (code quality, conventions)

### [S1] Deferred import in `_create_page_link` is unnecessary
- **File**: `s_wiki_crawler/src/daemon.py`:385
- **What**: `from src.storage import _url_to_record_id` is imported inside the method body. There is no circular import risk (daemon → storage → crawler, daemon → crawler — no cycle). Move to top-level imports.

---

## Summary

| Bugs | Gaps | Warnings | Style |
|------|------|----------|-------|
| 3 | 2 | 3 | 1 |

**Verdict**: **FAIL** — B1 (per-page exception handling) and B2 (refresh exception handling) violate the design's fail-forward principle and can crash the daemon. B3 and G2 are lower risk but real. All are straightforward to fix.
