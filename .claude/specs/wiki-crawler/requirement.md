# Wiki Crawler Service — Requirements

## Overview

Deterministic web crawler service that pre-caches game wiki pages for downstream LLM extraction agents. The fundamental insight: LLMs should never talk to the internet directly. Web crawling is unreliable, rate-limited, and adversarial (CAPTCHAs, bot detection). The crawler handles all of that as a standalone deterministic service, producing a clean, cached corpus that agents read locally.

The service runs as a Docker daemon. It receives zone names via RabbitMQ, crawls the relevant wiki pages according to a YML-defined scope, stores the raw markdown on the filesystem, and builds a metadata graph in SurrealDB that indexes what was crawled, when, and how it relates to zones and page categories. Connected zones discovered during crawling are published back to the queue for wave-based expansion.

This spec covers the crawl pipeline only — from seed to graph. No LLM extraction, no WLR integration. The goal is to evaluate crawl quality and data correctness before connecting any agent.

---

## User Stories

### WC-1: RabbitMQ Seed Processing

**As a** system operator,
**I want to** submit zone names to a RabbitMQ queue and have the crawler pick them up,
**so that** crawl targets are dynamic and driven by other services — not hardcoded.

**Acceptance Criteria:**
- Consumes zone crawl requests from a configurable RabbitMQ queue (`CRAWL_JOB_QUEUE`)
- Message format: JSON with `zone_name` (slug), `game` (default: "wow"), and optional `priority`
- Acknowledges messages only after the full crawl-store-graph cycle completes for that zone
- Rejects malformed messages to a dead-letter queue with a logged reason
- Handles duplicate zone names gracefully — if a zone is already fully crawled and fresh, skips it (or re-crawls if the refresh interval has elapsed)
- Runs as a long-lived daemon inside a Docker container

### WC-2: YML-Defined Crawl Scope

**As a** system operator,
**I want to** define what pages to crawl per zone in a YAML config file,
**so that** crawl scope is configurable, game-agnostic, and auditable without code changes.

**Acceptance Criteria:**
- Crawl scope defined in `config/crawl_scope.yml`
- Each scope entry defines a page category (e.g., `zone_overview`, `npcs`, `factions`, `lore`, `items`, `quests`)
- Each category specifies:
  - Search query templates with `{zone}` and `{game}` placeholders (e.g., `"site:wowpedia.fandom.com {zone} NPCs"`)
  - Preferred domains in priority order (aligned with `sources.yml` tiers)
  - Maximum pages to crawl per category
  - Optional URL patterns to include/exclude
- The config file is game-agnostic — changing it adapts the crawler to a different MMORPG
- Categories map to the WLR's existing research topics (zone_overview, npc, faction, lore, narrative_items)

### WC-3: Deterministic Page Crawling

**As the** system,
**I want to** crawl wiki pages deterministically using crawl4ai,
**so that** page fetching is reliable, rate-limited, and independent of any LLM decisions.

**Acceptance Criteria:**
- For each category in the crawl scope:
  1. Executes DuckDuckGo searches using the query templates (via Web Search MCP)
  2. Selects URLs from search results, preferring higher-tier domains
  3. Crawls selected URLs via crawl4ai's `/crawl` endpoint with `simulate_user: true` and anti-bot browser config
  4. Extracts internal links from crawled pages for sub-page discovery (e.g., zone page links to NPC pages)
- Per-domain rate limiting — minimum interval between requests to the same domain (reuses `RATE_LIMIT_REQUESTS_PER_MINUTE` config)
- Per-domain circuit breaker — after N consecutive failures on a domain, stops attempting it for that zone
- Multi-signal block detection — detects CAPTCHA/rate-limit pages before storing (definitive phrase matching + weighted soft signals + structural analysis)
- Blocked content is never stored — only validated, clean markdown is persisted
- Fail-forward — if a page fails after retries, logs the failure, skips it, and continues with remaining pages

### WC-4: Filesystem Content Storage

**As the** system,
**I want to** store crawled markdown on the filesystem in a structured directory layout,
**so that** content is cheap to store, easy to inspect, and decoupled from the database.

**Acceptance Criteria:**
- Content root at a configurable path (`CRAWL_CACHE_ROOT`, default: `./cache`)
- Directory layout: `{root}/{game}/{zone_slug}/{category}/{page_slug}.md`
  - Example: `cache/wow/elwynn_forest/npcs/hogger.md`
  - Example: `cache/wow/elwynn_forest/zone_overview/elwynn_forest.md`
- Page slug derived from the URL path (sanitized, kebab-case)
- Each markdown file is the raw crawl output — no transformation or summarization
- Alongside each `.md` file, a `.meta.json` sidecar with: `url`, `domain`, `crawled_at`, `content_hash` (SHA-256), `http_status`, `content_length`
- Content hash enables change detection on refresh cycles without re-reading the full file
- Old content is not deleted on refresh — the file is overwritten with new content and the sidecar updated

### WC-5: SurrealDB Graph Metadata

**As the** system,
**I want to** build a metadata graph in SurrealDB that indexes all crawled content,
**so that** downstream agents can discover and query cached content by zone, category, and freshness without scanning the filesystem.

**Acceptance Criteria:**
- Three record types: `zone`, `page`, `domain`
- `zone` records: `name`, `game`, `status` (pending/crawling/complete), `crawled_at`, `page_count`
- `page` records: `url`, `title`, `page_type` (category), `domain`, `file_path` (relative to cache root), `content_hash`, `crawled_at`, `content_length`, `http_status`
- `domain` records: `name`, `tier` (from sources.yml), `consecutive_failures`, `last_success`, `last_failure`
- Graph edges:
  - `zone -> has_page -> page` with edge properties: `page_type`, `discovery_method` (search/link_extraction/seed)
  - `zone -> connected_to -> zone` discovered from crawled page content
  - `page -> links_to -> page` for internal wiki links found during crawling
  - `page -> from_domain -> domain` for domain-level health tracking
- Graph queries must support:
  - "All NPC pages for zone X": `SELECT ->has_page[WHERE page_type = 'npc']->page.* FROM zone:X`
  - "All stale pages (older than N days)": `SELECT ->has_page[WHERE crawled_at < time::now() - 7d]->page.* FROM zone`
  - "Connected zones from zone X": `SELECT ->connected_to->zone.name FROM zone:X`
- All graph writes happen via the Storage MCP (not direct SurrealDB access)

### WC-6: Connected Zone Discovery

**As the** system,
**I want to** discover zones connected to the current zone during crawling and publish them back to the queue,
**so that** the crawl corpus expands outward from seed zones without manual intervention.

**Acceptance Criteria:**
- After crawling a zone's overview page, extracts connected/adjacent zone names from the content
- Connected zones are identified from wiki links, "adjacent zones" sections, and zone navigation templates
- Creates `zone -> connected_to -> zone` edges in the graph for discovered connections
- Publishes each newly discovered zone back to the crawl job queue (same queue as WC-1)
- Does not re-publish zones that are already in the graph (deduplication)
- Discovery is best-effort — if the overview page doesn't mention connected zones, nothing is published

### WC-7: Round-Robin Refresh

**As a** system operator,
**I want to** the crawler to periodically re-visit previously crawled zones and detect content changes,
**so that** the cached corpus stays current without manual re-crawling.

**Acceptance Criteria:**
- After processing all pending seeds in the queue, the crawler enters refresh mode
- In refresh mode, queries the graph for the oldest-crawled zone and re-crawls it
- Round-robin order: zones are refreshed in order of `crawled_at` (oldest first)
- Change detection: compares new content hash against stored `content_hash` — only overwrites if different
- Updated pages get a new `crawled_at` timestamp in both the sidecar and the graph
- Unchanged pages get only `crawled_at` updated (freshness confirmed, no content write)
- Configurable minimum refresh interval (`REFRESH_INTERVAL_HOURS`, default: 168 = 7 days) — zones newer than this are skipped
- Refresh mode pauses immediately when a new seed arrives in the queue (seeds take priority)

### WC-8: Structured Logging

**As a** system operator,
**I want to** all crawl activity logged as structured JSON events,
**so that** I can monitor the crawler's progress and diagnose issues.

**Acceptance Criteria:**
- Every log event includes: `service_id` ("wiki_crawler"), `timestamp`, `level`, `event`
- Key events logged:
  - Zone crawl started/completed (zone name, page count, duration)
  - Page crawl success (URL, domain, content length, content hash)
  - Page crawl failure (URL, domain, error reason, attempt count)
  - Block detected (URL, domain, detection reason, backoff duration)
  - Circuit breaker tripped (domain, consecutive failure count)
  - Connected zone discovered (source zone, target zone)
  - Refresh cycle started/completed (zones checked, pages updated)
  - Content change detected (URL, old hash, new hash)
- Structured JSON format matching the project's logging conventions

---

## Infrastructure Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| crawl4ai Docker | Exists | `unclecode/crawl4ai:latest` on port 11235. Upgrade from `/md` to `/crawl` endpoint. |
| RabbitMQ | Exists | For seed queue + connected zone publishing |
| SurrealDB | Exists | Graph metadata storage (via Storage MCP or direct) |
| Storage MCP | Exists | SurrealDB access layer — may need new graph-specific tools |
| Web Search MCP | Exists | DuckDuckGo search for URL discovery |
| Filesystem volume | To be configured | Docker volume for `CRAWL_CACHE_ROOT` |

---

## Configuration Summary

### Environment Variables

```
CRAWL_JOB_QUEUE=s.wiki_crawler.jobs          # RabbitMQ queue for seed zones
CRAWL_CACHE_ROOT=./cache                      # Filesystem root for cached content
RABBITMQ_URL=amqp://mythline:mythline@rabbitmq:5672/
SURREALDB_URL=ws://surrealdb:8000/rpc
MCP_WEB_SEARCH_URL=http://mcp-web-search:8006/mcp
CRAWL4AI_URL=http://crawl4ai:11235
RATE_LIMIT_REQUESTS_PER_MINUTE=30             # Per-domain throttle
CIRCUIT_BREAKER_THRESHOLD=3                   # Consecutive failures before tripping
REFRESH_INTERVAL_HOURS=168                    # Min hours before re-crawling a zone
MAX_PAGES_PER_CATEGORY=10                     # Default max pages per scope category
GAME_NAME=wow                                 # Default game
```

### Config Files

```
config/crawl_scope.yml        # Page categories, search templates, domain priorities
config/sources.yml            # Source tier definitions (shared with WLR)
```

---

## Out of Scope

- **LLM-based extraction** — this service crawls and stores only. No structured data extraction.
- **WLR integration** — no changes to the World Lore Researcher in this spec. That comes after we validate crawl quality.
- **Multi-game support** — WoW is the only target. Config is game-agnostic by design, but only WoW configs will be built.
- **UI/dashboard** — no web interface for the crawler. Structured logs are the monitoring surface.
- **Embedding generation** — no vector embeddings on crawled content. That's the WLR's job (or Storage MCP's).
