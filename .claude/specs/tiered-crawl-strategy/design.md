# Tiered Crawl Strategy — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Three tier-specific functions, one dispatcher — not a class hierarchy | Each tier has radically different I/O (JSON API vs. HTML GET vs. browser POST). A dispatch function with three plain async functions is simpler than an abstract base class. _(KISS, WC-9)_ |
| D2 | Tier field added to `CrawlResult` model, not a separate return type | All callers (daemon.py, storage.py) already consume `CrawlResult`. Adding a `tier` field preserves backward compatibility. _(WC-9, WC-12)_ |
| D3 | MediaWiki site mapping in `sources.yml`, not a separate config file | `sources.yml` already maps domains to tiers. Adding `mediawiki_api` as a property of domains keeps all domain intelligence in one place. _(WC-13, KISS)_ |
| D4 | Direct httpx calls to `api.php`, not pymediawiki library | pymediawiki is a 500+ line wrapper around simple GET requests. We need exactly one endpoint (`action=parse`). httpx is already a dependency. _(WC-10, Reuse before build — but don't add deps for one function)_ |
| D5 | markdownify for both Tier 1 and Tier 2 conversion | Same library, same output format, consistent markdown across tiers. readability-lxml only used in Tier 2 for article extraction (pre-processing step before markdownify). _(WC-14)_ |
| D6 | Fallback is tier-sequential, not parallel | Trying Tier 1 → Tier 2 → Tier 3 in sequence is simple and fast (Tier 1 fails in <1s if the API returns an error). Parallel would waste resources and complicate error aggregation. _(WC-9)_ |
| D7 | `_url_to_wiki_title()` extracts page title from URL path — no URL→title API call | MediaWiki URLs follow `/wiki/{Title}` convention. Parsing the path is deterministic and instant. No extra API round-trip. _(D4, WC-10)_ |
| D8 | Tier 2 uses readability-lxml for extraction, not BeautifulSoup CSS selectors | readability-lxml is site-agnostic (Mozilla's algorithm). BS4+CSS selectors would need per-site maintenance. readability handles unknown sites without configuration. _(WC-11)_ |

---

## 1. Tier Dispatcher

### 1.1 Dispatch Flow

```
crawl_page(url, throttle)
  │
  ├─ domain = urlparse(url).netloc
  ├─ check circuit breaker → if tripped, return error CrawlResult
  │
  ├─ api_url = get_mediawiki_api(domain)
  │   ├─ if api_url → crawl_page_api(url, api_url, throttle)
  │   │               ├─ success → return CrawlResult(tier="api")
  │   │               └─ fail → log, fall through to Tier 2
  │   └─ no match → skip to Tier 2
  │
  ├─ crawl_page_http(url, throttle)
  │   ├─ success + content valid → return CrawlResult(tier="http")
  │   └─ fail/empty/blocked → log, fall through to Tier 3
  │
  └─ crawl_page_browser(url, throttle)
      ├─ success → return CrawlResult(tier="browser")
      └─ fail → return error CrawlResult(tier="browser")
```

### 1.2 Dispatcher Function Signature

```python
# crawler.py — replaces existing crawl_page()

async def crawl_page(
    url: str,
    throttle: DomainThrottle,
    *,
    crawl4ai_url: str | None = None,
) -> CrawlResult:
    """Crawl a URL using the best available tier.

    Dispatch: MediaWiki API (Tier 1) → plain HTTP (Tier 2) → crawl4ai (Tier 3).
    Falls through tiers on failure. Circuit breaker checked once at entry.
    """
```

The function signature is unchanged from the current `crawl_page()`. The `crawl4ai_url` kwarg is passed through to Tier 3. Callers in `daemon.py` require no changes. _(WC-9)_

### 1.3 Tier Selection Logic

```python
def get_mediawiki_api(domain: str) -> str | None:
    """Return the api.php URL for a domain, or None if not a MediaWiki site."""
    sources = load_sources_config()
    return sources.get("mediawiki_sites", {}).get(domain)
```

This is a config lookup, not a heuristic. Only domains explicitly configured as MediaWiki sites route to Tier 1. _(WC-13)_

---

## 2. Tier 1 — MediaWiki API

### 2.1 Function Signature

```python
async def crawl_page_api(
    url: str,
    api_url: str,
    throttle: DomainThrottle,
) -> CrawlResult | None:
    """Fetch page via MediaWiki Action API. Returns None on failure (triggers fallback)."""
```

Returns `CrawlResult` on success, `None` on failure (so the dispatcher knows to fall through).

### 2.2 URL → Page Title Extraction

```python
def _url_to_wiki_title(url: str) -> str | None:
    """Extract MediaWiki page title from a URL.

    Handles:
      /wiki/Elwynn_Forest         → "Elwynn_Forest"
      /wiki/Category:Zones        → "Category:Zones"
      /w/index.php?title=Hogger   → "Hogger"
    Returns None if the URL path doesn't match wiki conventions.
    """
    parsed = urlparse(url)

    # Standard /wiki/Title format
    if "/wiki/" in parsed.path:
        return unquote(parsed.path.split("/wiki/", 1)[1])

    # MediaWiki /w/index.php?title=Title format
    params = parse_qs(parsed.query)
    if "title" in params:
        return params["title"][0]

    return None
```

### 2.3 API Call and Response Parsing

```python
# Inside crawl_page_api():

title = _url_to_wiki_title(url)
if not title:
    return None  # Can't extract title — fall back

await throttle.wait(domain)

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(api_url, params={
        "action": "parse",
        "page": title,
        "prop": "text|links|categories",
        "format": "json",
        "disabletoc": "true",       # No table of contents in HTML
        "disableeditsection": "true", # No [edit] links
    })

if response.status_code != 200:
    return None

data = response.json()

# API error (missing page, invalid title, etc.)
if "error" in data:
    logger.warning("mediawiki_api_error", extra={
        "url": url, "error": data["error"].get("info", "unknown"),
    })
    return None

parse_data = data["parse"]
html_content = parse_data["text"]["*"]
page_title = parse_data.get("title", title)
```

### 2.4 Link Extraction from API Response

The MediaWiki API returns structured link data — no regex needed:

```python
# Internal links from API response
api_links = parse_data.get("links", [])
links = []
for link_info in api_links:
    # Each link is {"ns": 0, "*": "Hogger"} where ns=0 is main namespace
    ns = link_info.get("ns", -1)
    link_title = link_info.get("*", "")
    if ns == 0 and link_title:  # Main namespace only
        # Convert title back to URL
        link_url = f"https://{domain}/wiki/{quote(link_title.replace(' ', '_'))}"
        links.append(link_url)
```

Excludes non-main namespaces (User, Talk, Template, Category) automatically via `ns == 0`. _(WC-10)_

### 2.5 Categories from API Response

```python
categories = [
    cat["*"] for cat in parse_data.get("categories", [])
    if isinstance(cat, dict) and "*" in cat
]
```

Categories are available for metadata but not currently stored in the graph. Available for future use.

---

## 3. Tier 2 — Plain HTTP

### 3.1 Function Signature

```python
async def crawl_page_http(
    url: str,
    throttle: DomainThrottle,
) -> CrawlResult | None:
    """Fetch page via plain HTTP GET + readability extraction. Returns None on failure."""
```

### 3.2 Fetch and Extract

```python
await throttle.wait(domain)

async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
    response = await client.get(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MythlineBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })

if response.status_code != 200:
    return None

content_type = response.headers.get("content-type", "")
if "text/html" not in content_type:
    return None  # Not an HTML page — can't extract

# Article extraction via readability-lxml
from readability import Document
doc = Document(response.text)
article_html = doc.summary()
page_title = doc.title()
```

### 3.3 Link Extraction from HTML

Tier 2 must extract links from the raw HTML (before readability strips them — readability may remove nav links):

```python
from urllib.parse import urljoin

def _extract_links_from_html(html: str, base_url: str, source_domain: str) -> list[str]:
    """Extract same-domain links from raw HTML using regex.

    Uses a simple <a href="..."> regex rather than a full HTML parser
    to avoid importing BeautifulSoup as a dependency.
    """
    _HREF_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
    _EXCLUDED = {"/special:", "/user:", "/talk:", "/file:", "/template:", "/category:"}
    links = []
    for match in _HREF_RE.finditer(html):
        href = urljoin(base_url, match.group(1))
        parsed = urlparse(href)
        if parsed.netloc != source_domain:
            continue
        if any(seg in parsed.path.lower() for seg in _EXCLUDED):
            continue
        links.append(href)
    return list(dict.fromkeys(links))  # Deduplicate, preserve order
```

Links are extracted from `response.text` (full HTML), not from `article_html` (extracted body).

### 3.4 Content Validation

After extraction and conversion, the content is validated with `detect_blocked_content()`:

```python
# After markdownify conversion
verdict = detect_blocked_content(markdown)
if verdict.is_blocked:
    throttle.report_blocked(domain)
    return None  # Blocked — fall through to Tier 3
```

---

## 4. HTML-to-Markdown Conversion

### 4.1 Shared Conversion Function

Both Tier 1 and Tier 2 produce HTML that needs markdown conversion. A single function handles both:

```python
# crawler.py

def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown using markdownify.

    Used by Tier 1 (MediaWiki API HTML) and Tier 2 (readability-extracted HTML).
    Strips scripts, styles, and normalizes whitespace.
    """
    from markdownify import markdownify as md

    markdown = md(
        html,
        heading_style="ATX",
        strip=["script", "style", "img"],
        convert=["p", "h1", "h2", "h3", "h4", "h5", "h6",
                 "ul", "ol", "li", "table", "thead", "tbody",
                 "tr", "th", "td", "a", "strong", "em", "code",
                 "pre", "blockquote", "br", "hr", "dl", "dt", "dd"],
    )

    # Normalize excessive blank lines
    import re
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown
```

### 4.2 Image Handling

Images are stripped (`strip=["img"]`) per WC-14. The crawler stores content only — no media. This also avoids broken image references in markdown.

### 4.3 Table Handling

markdownify converts HTML tables to pipe-style markdown. Wiki infoboxes using `<table>` tags are converted. `colspan` is supported; `rowspan` is flattened (a known markdownify limitation that does not affect data correctness — just visual alignment).

---

## 5. CrawlResult Model Extension

### 5.1 New `tier` Field

```python
# models.py

class CrawlResult(BaseModel):
    """Result of crawling a single URL."""

    url: str
    domain: str
    title: str
    content: str | None = Field(default=None, description="Markdown content")
    links: list[str] = Field(default_factory=list, description="Internal links extracted")
    http_status: int = 0
    content_hash: str = Field(default="", description="SHA-256 of content")
    error: str | None = None
    tier: str = Field(default="browser", description="Crawl tier used: api, http, or browser")
```

Default is `"browser"` for backward compatibility — existing Tier 3 code doesn't need to change. _(WC-9, WC-12)_

### 5.2 Valid Tier Values

| Value | Meaning |
|-------|---------|
| `"api"` | Tier 1 — MediaWiki Action API |
| `"http"` | Tier 2 — Plain HTTP + readability |
| `"browser"` | Tier 3 — crawl4ai headless Chromium |

---

## 6. Configuration Schema

### 6.1 Extended `sources.yml`

```yaml
# config/sources.yml — existing content unchanged, new section added

game: wow
game_name: World of Warcraft

source_tiers:
  official:
    description: Official Blizzard sources
    domains:
      - worldofwarcraft.blizzard.com
      - wowpedia.fandom.com
      - news.blizzard.com
    weight: 1.0

  primary:
    description: Major community wikis and databases
    domains:
      - warcraft.wiki.gg
      - wow.tools
    weight: 0.8

  secondary:
    description: Community guides and lore analysis
    domains:
      - icy-veins.com
      - nobbel87.com
      - wow.gamepedia.com
    weight: 0.6

  tertiary:
    description: General gaming sources
    domains:
      - reddit.com/r/wow
      - reddit.com/r/warcraftlore
      - mmo-champion.com
    weight: 0.4

# NEW: MediaWiki API endpoints for Tier 1 crawling
mediawiki_sites:
  wowpedia.fandom.com: https://wowpedia.fandom.com/api.php
  warcraft.wiki.gg: https://warcraft.wiki.gg/api.php
  wow.gamepedia.com: https://wow.gamepedia.com/api.php
```

### 6.2 Config Loader Addition

```python
# config.py — new function

def get_mediawiki_api(domain: str) -> str | None:
    """Return the api.php URL for a MediaWiki domain, or None."""
    sources = load_sources_config()
    return sources.get("mediawiki_sites", {}).get(domain)
```

No new environment variables. No new config files. _(WC-13)_

---

## 7. Error Handling

### 7.1 Per-Tier Error Semantics

| Tier | Failure Mode | Behavior |
|------|-------------|----------|
| **Tier 1** | API returns `{"error": ...}` | Log warning, return `None` → fall to Tier 2 |
| **Tier 1** | Non-200 HTTP status | Log warning, return `None` → fall to Tier 2 |
| **Tier 1** | Title extraction fails | Return `None` → fall to Tier 2 |
| **Tier 1** | Empty HTML in response | Return `None` → fall to Tier 2 |
| **Tier 1** | Network error (httpx) | Log warning, return `None` → fall to Tier 2 |
| **Tier 2** | Non-200 HTTP status | Return `None` → fall to Tier 3 |
| **Tier 2** | Non-HTML content type | Return `None` → fall to Tier 3 |
| **Tier 2** | Block detected in content | Report to throttle, return `None` → fall to Tier 3 |
| **Tier 2** | Empty after readability extraction | Return `None` → fall to Tier 3 |
| **Tier 2** | Network error (httpx) | Log warning, return `None` → fall to Tier 3 |
| **Tier 3** | Any failure | Existing behavior — return error `CrawlResult` (no further fallback) |

### 7.2 Fallback Logging

Each tier fallback is logged at INFO level with the reason:

```python
logger.info("tier1_fallback", extra={
    "url": url, "reason": "api_error", "detail": "missingtitle",
})
```

This enables debugging tier selection issues from structured logs. _(WC-8 extension)_

### 7.3 DomainThrottle Integration

- **Tier 1**: Calls `throttle.wait(domain)` before the API request. Calls `throttle.report_success(domain)` on success. Does NOT call `report_blocked()` on API errors (API errors are not rate-limit blocks).
- **Tier 2**: Calls `throttle.wait(domain)` before the HTTP request. Calls `report_blocked()` if block detection triggers. Calls `report_success()` on success.
- **Tier 3**: Unchanged — existing throttle integration preserved.

Circuit breaker is checked once at dispatcher entry, applies to all tiers for that domain.

---

## 8. Files Changed

| File | Change |
|------|--------|
| `s_wiki_crawler/src/crawler.py` | Refactor: rename existing `crawl_page()` to `crawl_page_browser()`. Add `crawl_page_api()`, `crawl_page_http()`, `_html_to_markdown()`, `_url_to_wiki_title()`, `_extract_links_from_html()`. New `crawl_page()` dispatches across tiers. |
| `s_wiki_crawler/src/models.py` | Add `tier: str = "browser"` field to `CrawlResult`. |
| `s_wiki_crawler/src/config.py` | Add `get_mediawiki_api()` function. |
| `s_wiki_crawler/config/sources.yml` | Add `mediawiki_sites` mapping section. |
| `s_wiki_crawler/pyproject.toml` | Add `markdownify>=0.14,<2` and `readability-lxml>=0.8,<1` to dependencies. |
| `s_wiki_crawler/tests/test_crawler.py` | Add tests for dispatcher, Tier 1, Tier 2, `_url_to_wiki_title()`, `_html_to_markdown()`, `_extract_links_from_html()`, fallback chain. |
| `s_wiki_crawler/tests/test_models.py` | Add test for `CrawlResult.tier` field default and values. |
| `s_wiki_crawler/tests/test_config.py` | Add test for `get_mediawiki_api()`. |

### Files NOT Changed

| File | Reason |
|------|--------|
| `s_wiki_crawler/src/daemon.py` | Calls `crawl_page()` — signature unchanged. No modification needed. |
| `s_wiki_crawler/src/storage.py` | Receives `CrawlResult` — new `tier` field is ignored by storage. No modification needed. |
| `shared/crawl.py` | Block detection and throttle are consumed by all tiers. No changes to shared code. |
| `s_wiki_crawler/Dockerfile` | `uv sync` picks up new deps from pyproject.toml automatically. No Dockerfile changes. |

---

## Future Work (Out of Scope)

- **MediaWiki category traversal for page discovery** — `api.php?list=categorymembers` could replace DuckDuckGo search for wiki pages. Deferred: current search works, and this would change the search pipeline (WC-2/WC-3).
- **WLR tiered crawling** — applying the same tiers to `a_world_lore_researcher/src/mcp_client.py`. Separate spec.
- **Tier preference overrides per domain** — allowing `sources.yml` to force a specific tier for a domain (e.g., `tier3_only: true` for known JS sites). Not needed until we encounter JS-heavy sources.
- **Async parallel tier attempts** — trying multiple tiers concurrently and taking the first success. Adds complexity for marginal gain (Tier 1 fails in <1s).
