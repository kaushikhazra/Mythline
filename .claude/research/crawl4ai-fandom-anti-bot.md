# crawl4ai Fandom Anti-Bot Blocking — Research & Solution

**Date**: 2026-02-26
**Context**: Wiki-crawler E2E testing showed crawl4ai (headless Chromium) gets HTTP 500 on all wowpedia.fandom.com URLs. Simple HTTP fetch works perfectly. This research determines why and recommends a fix.
**Status**: Research complete

---

## The Problem

During E2E smoke testing of the wiki-crawler service, every crawl4ai request to wowpedia.fandom.com returned HTTP 500. After 46 failed pages across all categories, the zone crawl completed with 0 pages stored. Meanwhile, a plain HTTP fetch (WebFetch) to the same URLs returned full article content immediately.

**Current stack**: `daemon.py` → `crawler.py` → httpx POST to crawl4ai Docker `/crawl` → Playwright headless Chromium → Fandom servers → HTTP 500.

---

## 1. Why Headless Chromium Triggers Cloudflare but Plain HTTP Doesn't

The detection asymmetry is counterintuitive: a *less* browser-like client evades detection better than a *more* browser-like one. The reason is that Cloudflare's detection engines operate at different layers, and a headless browser exposes more attack surface.

### Detection Layers

| Layer | Plain HTTP (httpx) | Headless Chromium (crawl4ai) |
|-------|-------------------|------------------------------|
| TLS fingerprint (JA3/JA4) | OpenSSL — doesn't match any browser. Detectable but **only enforced on Enterprise plans**. | BoringSSL — matches real Chrome closely but with minor headless differences. |
| JavaScript execution | **Never happens.** JSD has nothing to inspect. | **Runs fully.** JSD detects `navigator.webdriver=true`, missing plugins, Playwright globals, CDP artifacts. |
| HTTP headers | Can be set to anything plausible. | `sec-ch-ua` may leak "HeadlessChrome". |
| Behavioral signals | None (single GET). | Click coordinates, mouse movement, typing patterns analyzable. |
| Canvas/WebGL fingerprint | N/A. | Different hash on headless Linux (software rendering). |

### The Key Insight

Cloudflare's **JavaScript Detections (JSD)** engine — active on **all plans including Free** — injects invisible JavaScript on every page load. This script probes:
- `navigator.webdriver` (true in automation)
- `navigator.plugins.length` (0 in headless)
- `window.__playwright__binding__` (present in Playwright)
- CDP serialization side effects (Chrome DevTools Protocol leaks)

A plain HTTP client never executes JavaScript, so JSD **never runs**. The only engine checking it is the heuristics engine, which passes clean IPs with plausible headers.

### Fandom's Cloudflare Configuration

Fandom uses Cloudflare but is not on Enterprise Bot Management. Their setup relies primarily on JSD and Bot Fight Mode — both JavaScript-dependent. This means:
- Headless browsers → challenged/blocked (JSD triggers)
- Plain HTTP with good headers → passes (no JSD to run)
- MediaWiki API requests → **never challenged** (designed for programmatic access)

**Sources**: [Cloudflare Bot Scores](https://developers.cloudflare.com/bots/concepts/bot-score/), [Cloudflare JSD](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/), [Cloudflare JA4 Signals](https://blog.cloudflare.com/ja4-signals/)

---

## 2. Fandom Has a MediaWiki API

This is the most important finding. Wowpedia runs on MediaWiki and exposes a **full-featured read API** at:

```
https://wowpedia.fandom.com/api.php
```

### Key Endpoints

| Endpoint | Returns | Use Case |
|----------|---------|----------|
| `action=parse&page={title}&prop=text\|links\|categories&format=json` | Rendered HTML + metadata | Primary content extraction |
| `action=query&titles={title}&prop=extracts&explaintext=true&format=json` | Plain text extract | Quick summaries |
| `action=query&list=categorymembers&cmtitle=Category:{name}&cmlimit=500&format=json` | Pages in a category | Zone page discovery |
| `action=query&list=search&srsearch={term}&format=json` | Search results | Alternative to DuckDuckGo for wiki content |
| `index.php?title={title}&action=render` | Clean HTML body (no UI chrome) | Lightweight HTML fetch |

### Example: Fetch Elwynn Forest as HTML

```python
import httpx

resp = httpx.get("https://wowpedia.fandom.com/api.php", params={
    "action": "parse",
    "page": "Elwynn_Forest",
    "prop": "text|links|categories",
    "format": "json",
})
data = resp.json()
html_content = data["parse"]["text"]["*"]
internal_links = [link["*"] for link in data["parse"]["links"]]
categories = [cat["*"] for cat in data["parse"]["categories"]]
```

### Why This is Superior to Crawling

1. **No Cloudflare challenges** — API endpoints serve JSON to any HTTP client
2. **Faster** — no browser startup, no page rendering, no JavaScript wait
3. **More reliable** — no bot score concerns, no detection cat-and-mouse
4. **Cleaner data** — structured JSON with just the content, not ads/nav/sidebar
5. **Intended access method** — MediaWiki explicitly provides APIs for programmatic access
6. **Free internal links** — `prop=links` returns all wiki links without regex extraction
7. **Category traversal** — `list=categorymembers` replaces DuckDuckGo search for discovering zone pages

### Rate Limits

No hard documented read limit, but best practice is ~1 request/second. Use `maxlag` parameter to back off when the server is under load.

### Python Library

**pymediawiki** (`pip install pymediawiki`) wraps the API:
```python
from mediawiki import MediaWiki
wowpedia = MediaWiki(url="https://wowpedia.fandom.com/api.php")
page = wowpedia.page("Elwynn Forest")
print(page.content)      # Full plain text
print(page.links)        # Internal links
print(page.categories)   # Categories
```

**Sources**: [MediaWiki API Tutorial](https://www.mediawiki.org/wiki/API:Tutorial), [MediaWiki API: Get Page Contents](https://www.mediawiki.org/wiki/API:Get_the_contents_of_a_page), [pymediawiki](https://pypi.org/project/pymediawiki/)

---

## 3. crawl4ai Has a Non-Browser Mode (But Not via Docker)

crawl4ai includes `AsyncHTTPCrawlerStrategy` — a lightweight aiohttp-based fetcher that bypasses Playwright entirely:

```python
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
from crawl4ai import HTTPCrawlerConfig, AsyncWebCrawler

strategy = AsyncHTTPCrawlerStrategy(
    browser_config=HTTPCrawlerConfig(
        method="GET",
        headers={"User-Agent": "MythlineBot/1.0"},
        follow_redirects=True,
    )
)
async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
    result = await crawler.arun("https://example.com")
    print(result.markdown)
```

**Critical limitation**: The Docker REST API does **not** expose this strategy. GitHub Issue #1452 tracks this as a missing feature with no timeline. Our wiki-crawler calls crawl4ai via Docker REST (`/crawl`), which only supports browser-based crawling.

**Implication**: We cannot fix this by configuring crawl4ai differently. We need a different approach for wiki sites.

**Source**: [Issue #1452 — Docker API Parity](https://github.com/unclecode/crawl4ai/issues/1452)

---

## 4. HTML-to-Markdown Library Comparison

Since the MediaWiki API returns HTML (via `action=parse`), we need to convert it to markdown. Options:

| Library | Article Extraction | Table Quality | License | Dependencies | Speed |
|---------|-------------------|---------------|---------|-------------|-------|
| **markdownify** | No — converts everything | Good (colspan, no rowspan) | MIT | 2 (bs4, six) | Slowest |
| **trafilatura** | Yes — strips boilerplate | Good | Apache 2.0 | 7 core | Fast |
| **html2text** | No — converts everything | Poor (flattened) | **GPL-3.0** | 0 | Moderate |
| **readability-lxml** | Yes — outputs HTML only | Preserves HTML | Apache 2.0 | 3 (lxml, cssselect, chardet) | Fast |
| **html-to-markdown** | No — converts everything | Best (Rust engine) | MIT | 0 (Rust binary) | 10-80x fastest |

### Recommendation: markdownify

For wiki content from the MediaWiki API, **markdownify** is the right choice because:

1. The API's `action=parse&prop=text` already returns **only the article content** — no nav, ads, or sidebar. Article extraction is unnecessary.
2. Wiki tables (infoboxes, data tables) are important for lore — trafilatura may strip them.
3. MIT license (no GPL concerns).
4. Subclassable — we can customize tag handling for wiki-specific elements.
5. Already used in the ecosystem (2.1k stars, active maintenance).

html2text is eliminated by GPL-3.0 license. trafilatura is overkill since the API pre-cleans the content. html-to-markdown (Rust) is fast but 9MB binary and no article extraction (unnecessary anyway with the API).

---

## 5. Recommended Architecture: Tiered Crawl Strategy

Replace the single crawl4ai path with a three-tier strategy. Higher tiers are tried first; lower tiers are fallbacks.

### Tier 1: MediaWiki API (wiki sites)

For any URL matching a known MediaWiki site (wowpedia.fandom.com, wowhead.com/wowpedia, warcraft.wiki.gg):

```
httpx GET → api.php?action=parse → JSON → markdownify → markdown
```

- No browser, no Cloudflare, structured data, internal links for free
- Category traversal replaces DuckDuckGo search for page discovery
- ~100ms per page vs ~30s+ for crawl4ai

### Tier 2: Plain HTTP + markdownify (static HTML sites)

For non-wiki URLs that serve server-rendered HTML (wowhead.com articles, game guide sites):

```
httpx GET → HTML → readability-lxml (extract article) → markdownify → markdown
```

- No browser needed for server-rendered pages
- readability-lxml strips boilerplate, markdownify converts to markdown
- Falls back to Tier 3 if the response requires JavaScript (detected by content analysis)

### Tier 3: crawl4ai Docker (JS-heavy sites)

For SPA sites or pages that require JavaScript rendering:

```
httpx POST → crawl4ai /crawl → Playwright headless → markdown
```

- Only used when Tier 1 and 2 fail or when a site is known to require JS
- Existing crawl4ai integration unchanged
- Block detection and circuit breaker from `shared/crawl.py` still apply

### Decision Flow

```
is_mediawiki_site(url)?
  ├── yes → Tier 1 (API)
  └── no → try Tier 2 (plain HTTP)
              ├── success + content validates → done
              └── fail or JS-required → Tier 3 (crawl4ai)
```

### Implementation Scope

| Component | Change |
|-----------|--------|
| `s_wiki_crawler/src/crawler.py` | Add `crawl_page_api()` for Tier 1, `crawl_page_http()` for Tier 2, rename existing `crawl_page()` to `crawl_page_browser()`. New `crawl_page()` dispatches by tier. |
| `s_wiki_crawler/pyproject.toml` | Add `markdownify`, `readability-lxml` dependencies |
| `s_wiki_crawler/src/config.py` | Add `MEDIAWIKI_SITES` config mapping domains to API URLs |
| `s_wiki_crawler/src/daemon.py` | No change — calls `crawl_page()` which handles dispatch internally |
| `shared/crawl.py` | No change — block detection still used for Tier 2/3 |
| Unit tests | Add tests for each tier and the dispatch logic |

### What Stays the Same

- `search_for_category()` — DuckDuckGo search still discovers URLs (Tier 1 API category traversal is additive)
- `select_urls()` — URL ranking/filtering unchanged
- `extract_connected_zones()` — regex extraction on markdown unchanged
- `store_page()` / `store_page_with_change_detection()` — storage layer unchanged
- `DomainThrottle` — rate limiting still applies to all tiers
- Graph structure — `crawl_zone`, `crawl_page`, edges all unchanged

---

## Relevance to This Project

This directly unblocks the wiki-crawler service. The E2E test showed 0/46 pages stored because every page went through crawl4ai (Tier 3 only), which gets blocked by Fandom's Cloudflare. Adding Tier 1 (MediaWiki API) would let those 46 pages succeed immediately.

The tiered strategy also benefits the World Lore Researcher agent, which uses crawl4ai via `/md` endpoint in `a_world_lore_researcher/src/mcp_client.py`. The same MediaWiki API approach could be applied there, but that's a separate change.

The wiki-crawler is the right place to implement this because its job is specifically to pre-cache wiki content — it should use the most reliable, fastest method available for each source type.

---

## Sources

- [Cloudflare Bot Score Documentation](https://developers.cloudflare.com/bots/concepts/bot-score/) — bot scoring system, 1-99 scale, four detection engines
- [Cloudflare JavaScript Detections](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/) — JSD engine, always-on for Free plans
- [Cloudflare JA4 Signals](https://blog.cloudflare.com/ja4-signals/) — TLS fingerprinting, JA3→JA4 evolution
- [Cloudflare JA3/JA4 Fingerprint Docs](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/) — fingerprint configuration
- [Castle.io: Headless Chrome Detection](https://blog.castle.io/how-to-detect-headless-chrome-bots-instrumented-with-playwright/) — CDP detection, navigator.webdriver, Playwright globals
- [WebScraper: Cloudflare Turnstile Mouse Event Detection](https://webscraper.io/blog/google-patches-100-precise-cloudflare-turnstile-bot-check) — 100% precise CDP mouse coordinate detection
- [crawl4ai Issue #1452 — Docker API Parity](https://github.com/unclecode/crawl4ai/issues/1452) — HTTP strategy not available via REST API
- [crawl4ai HTTP Strategy Docs](https://docs.crawl4ai.com/assets/llm.txt/txt/http_based_crawler_strategy.txt) — AsyncHTTPCrawlerStrategy API
- [crawl4ai Anti-Bot & Fallback Docs](https://docs.crawl4ai.com/advanced/anti-bot-and-fallback/) — fallback_fetch_function, detection escalation
- [crawl4ai Discussion #981](https://github.com/unclecode/crawl4ai/discussions/981) — Cloudflare blocking with no resolution
- [MediaWiki API Tutorial](https://www.mediawiki.org/wiki/API:Tutorial) — comprehensive API guide
- [MediaWiki API: Get Page Contents](https://www.mediawiki.org/wiki/API:Get_the_contents_of_a_page) — action=parse, action=query
- [pymediawiki](https://pypi.org/project/pymediawiki/) — Python wrapper for MediaWiki API
- [markdownify on PyPI](https://pypi.org/project/markdownify/) — HTML-to-markdown, MIT, subclassable
- [trafilatura on GitHub](https://github.com/adbar/trafilatura) — article extraction, 5.3k stars
- [html-to-markdown on PyPI](https://pypi.org/project/html-to-markdown/) — Rust-powered, 150-280 MB/s
