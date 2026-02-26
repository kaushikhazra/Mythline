# Tiered Crawl Strategy — Requirements

## Overview

The wiki-crawler service currently uses a single crawl path: every URL goes through crawl4ai's headless Chromium browser via the Docker REST API. E2E testing revealed that Cloudflare's JavaScript Detections engine blocks crawl4ai on Fandom/wowpedia (HTTP 500 on all 46 pages), while plain HTTP requests to the same URLs succeed instantly. Wowpedia pages are server-rendered HTML that don't require JavaScript — and better yet, Fandom exposes a MediaWiki API (`api.php`) that returns structured JSON with no Cloudflare challenge.

This spec replaces the single crawl4ai path with a three-tier dispatch strategy: MediaWiki API for wiki sites (fastest, most reliable), plain HTTP with article extraction for static HTML sites, and crawl4ai as a fallback for JavaScript-heavy sites. The dispatcher selects the tier by domain, with automatic fallback if a higher tier fails.

This extends the existing wiki-crawler service (spec: `wiki-crawler`). The existing user stories WC-1 through WC-8 remain unchanged. New stories continue from WC-9.

---

## User Stories

### WC-9: Tier Dispatcher

**As the** wiki-crawler daemon,
**I want to** select the crawl method per-URL based on domain,
**so that** each site is crawled using the most reliable and efficient method available.

**Acceptance Criteria:**
- The `crawl_page()` function dispatches to one of three tier-specific functions based on the URL's domain
- Tier selection is driven by a domain-to-tier mapping in configuration (not hardcoded)
- Dispatch order: Tier 1 (MediaWiki API) → Tier 2 (plain HTTP) → Tier 3 (crawl4ai browser)
- If a tier fails (network error, empty content, block detected), the dispatcher falls back to the next tier
- Fallback is logged with the reason the higher tier failed
- The final `CrawlResult` includes which tier was used (for observability)
- All existing callers of `crawl_page()` work without modification — the dispatcher is internal

### WC-10: Tier 1 — MediaWiki API Crawl

**As the** wiki-crawler daemon,
**I want to** fetch wiki page content via the MediaWiki Action API (`api.php`),
**so that** wiki sites are crawled without triggering Cloudflare anti-bot detection, with structured metadata for free.

**Acceptance Criteria:**
- For URLs matching a configured MediaWiki site, extracts the page title from the URL path
- Calls `api.php?action=parse&page={title}&prop=text|links|categories&format=json` via httpx GET
- Converts the returned HTML (`data["parse"]["text"]["*"]`) to markdown using markdownify
- Extracts internal wiki links from `data["parse"]["links"]` (structured, no regex needed)
- Extracts page categories from `data["parse"]["categories"]`
- Returns a `CrawlResult` with `content` (markdown), `links` (list of URLs), and `title`
- Respects per-domain rate limiting (same `DomainThrottle` as other tiers)
- Handles API errors: invalid page title (returns `{"error": {...}}`), missing page, server errors
- Does NOT use crawl4ai or a headless browser — plain HTTP only

### WC-11: Tier 2 — Plain HTTP Crawl

**As the** wiki-crawler daemon,
**I want to** fetch static HTML pages via plain HTTP and extract the article content,
**so that** server-rendered sites are crawled without a browser, faster and more reliably than crawl4ai.

**Acceptance Criteria:**
- For URLs not matching a MediaWiki site, attempts a plain httpx GET with reasonable headers (User-Agent, Accept)
- Extracts the article body using readability-lxml (strips navigation, ads, sidebar)
- Converts the extracted HTML to markdown using markdownify
- Validates the resulting content: non-empty, passes block detection (`detect_blocked_content`)
- If content is empty or blocked, falls back to Tier 3
- Extracts internal links from anchor tags in the extracted HTML
- Returns a `CrawlResult` consistent with Tier 1 and Tier 3 outputs
- Respects per-domain rate limiting

### WC-12: Tier 3 — crawl4ai Browser Crawl (Existing)

**As the** wiki-crawler daemon,
**I want to** fall back to crawl4ai's headless browser for sites that require JavaScript rendering,
**so that** JS-heavy or SPA sites can still be crawled when Tier 1 and Tier 2 fail.

**Acceptance Criteria:**
- The existing `crawl_page()` crawl4ai logic (POST to `/crawl` with browser config) becomes Tier 3
- No functional changes to the crawl4ai integration — same stealth config, same block detection, same retry logic
- Tier 3 is only reached when Tier 1 and Tier 2 both fail or when the domain is configured as `tier3_only`
- Existing block detection, circuit breaker, and DomainThrottle behavior are preserved
- `CrawlResult` includes `tier="browser"` to distinguish from Tier 1/2 results

### WC-13: MediaWiki Site Configuration

**As a** system operator,
**I want to** configure which domains are MediaWiki sites with their API base URLs,
**so that** the tier dispatcher knows which URLs to route to Tier 1 without hardcoding.

**Acceptance Criteria:**
- MediaWiki site mappings defined in `config/sources.yml` (extends existing file)
- Each mapping specifies: domain name → API base URL
- Initial mappings for WoW:
  - `wowpedia.fandom.com` → `https://wowpedia.fandom.com/api.php`
  - `warcraft.wiki.gg` → `https://warcraft.wiki.gg/api.php`
  - `wow.gamepedia.com` → `https://wow.gamepedia.com/api.php`
- The dispatcher checks the URL's domain against this mapping to decide Tier 1 eligibility
- New MediaWiki sites can be added by editing the config file — no code changes required

### WC-14: Content Conversion Quality

**As the** wiki-crawler daemon,
**I want to** convert HTML to clean markdown that preserves wiki structure,
**so that** downstream LLM extraction agents receive well-formatted content.

**Acceptance Criteria:**
- Headings preserved as ATX-style markdown (`# H1`, `## H2`, etc.)
- Wiki tables converted to pipe-style markdown tables (including infoboxes)
- Internal links preserved as markdown links
- Images stripped (content-only — no media references)
- Navigation elements, table of contents, edit links, and page chrome stripped
- Script and style tags stripped
- Output is valid markdown that renders correctly
- The same markdownify conversion is used for both Tier 1 and Tier 2 (consistent output format)

---

## Infrastructure Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| crawl4ai Docker | Exists | Retained as Tier 3 fallback. No changes. |
| RabbitMQ | Exists | No changes — seed processing unchanged. |
| SurrealDB / Storage MCP | Exists | No changes — graph writes unchanged. |
| Web Search MCP | Exists | No changes — URL discovery unchanged. |
| httpx | Exists | Already a dependency. Used for Tier 1 and Tier 2 HTTP requests. |
| markdownify | **New** | `pip install markdownify`. HTML-to-markdown conversion. MIT license. |
| readability-lxml | **New** | `pip install readability-lxml`. Article extraction for Tier 2. Apache 2.0 license. |

---

## Configuration Summary

### New Entries in `config/sources.yml`

```yaml
mediawiki_sites:
  wowpedia.fandom.com: https://wowpedia.fandom.com/api.php
  warcraft.wiki.gg: https://warcraft.wiki.gg/api.php
  wow.gamepedia.com: https://wow.gamepedia.com/api.php
```

### Existing Environment Variables (No Changes)

All existing wiki-crawler env vars (`CRAWL4AI_URL`, `RATE_LIMIT_REQUESTS_PER_MINUTE`, etc.) are preserved. No new env vars required — tier configuration lives in the YAML file.

### New Python Dependencies

```
markdownify>=0.14,<2          # HTML → Markdown conversion
readability-lxml>=0.8,<1      # Article body extraction (Tier 2)
```

---

## Out of Scope

- **WLR integration** — the WLR agent's `mcp_client.py` also calls crawl4ai. Applying tiers there is a separate spec.
- **MediaWiki category traversal as URL discovery** — using `list=categorymembers` to replace/supplement DuckDuckGo search is a potential enhancement but not part of this spec. The existing search pipeline (WC-2, WC-3) remains unchanged.
- **pymediawiki library** — direct httpx calls to `api.php` are simpler and avoid an extra dependency. pymediawiki is not needed.
- **crawl4ai AsyncHTTPCrawlerStrategy** — this exists in the Python SDK but is not available via the Docker REST API (Issue #1452). Not usable in our architecture.
- **Proxy rotation or CAPTCHA solving** — not needed. Tier 1 and 2 bypass Cloudflare entirely. Tier 3 retains existing stealth config.
- **Multi-game API support** — only WoW MediaWiki sites configured initially. The config is extensible but we won't build mappings for other games yet.
