# Wiki Crawler Service — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Service lives at `s_wiki_crawler/` with `s_` prefix | It's a deterministic service daemon, not an LLM agent (`a_`). No prompts, no MCP toolsets, no agent.py. Follows agent folder structure for consistency (daemon.py, config.py, models.py) but without LLM-specific files. _(WC-1)_ |
| D2 | Crawler tables prefixed `crawl_zone`, `crawl_page`, `crawl_domain` | Storage MCP already has `zone`, `npc`, `faction` etc. for WLR lore data. The crawler's metadata records are distinct from lore content — `crawl_zone` tracks crawl state, WLR's `zone` tracks lore data. Prefixing avoids table collision. _(WC-5)_ |
| D3 | Extend Storage MCP VALID_TABLES and VALID_RELATIONS — no new data access layer | The existing Storage MCP CRUD tools (`create_record`, `get_record`, `query_records`) and graph tools (`create_relation`, `traverse`) are generic. Adding new table/relation names is sufficient. No new MCP tools needed. _(WC-5, KISS)_ |
| D4 | 100% LLM-free — all decisions are deterministic | URL selection uses domain tier ranking. Block detection uses multi-signal pattern matching. Zone discovery uses regex/link extraction. No LLM calls anywhere in the service. This is the core architectural insight — separating deterministic crawling from intelligent extraction. _(WC-3)_ |
| D5 | Extract `DomainThrottle`, `detect_blocked_content`, `CrawlVerdict` to `shared/crawl.py` | These are crawl infrastructure, not WLR-specific. Both WLR and wiki crawler need them. WLR's `mcp_client.py` imports from shared instead of defining inline. _(DRY)_ |
| D6 | Use crawl4ai REST `/crawl` endpoint (upgrade from `/md`) | `/crawl` supports `BrowserConfig` (stealth mode, custom UA), `CrawlerRunConfig` (simulate_user, css_selector, link extraction via `score_links`), and batch URLs. The `/md` endpoint is a simplified wrapper that lacks these controls. _(WC-3)_ |
| D7 | Crawler both consumes from and publishes to the same RabbitMQ queue | Discovered connected zones go back into the same job queue. This creates natural wave expansion without a separate queue. Priority field in CrawlJob lets seeds outrank discovered zones. _(WC-6)_ |
| D8 | Filesystem for content, SurrealDB for metadata only | Wiki page content is large (10KB-500KB per page). Filesystem is cheap, inspectable, and decoupled from the database. SurrealDB stores only metadata and graph relationships — file paths, content hashes, crawl timestamps. _(WC-4, WC-5)_ |
| D9 | `sources.yml` is shared between WLR and wiki crawler via copy, not symlink | Docker COPY doesn't follow symlinks cleanly. Each service gets its own copy of `sources.yml` in its `config/` folder. If tier definitions change, both must be updated (grep for consistency). _(Docker-first)_ |
| D10 | Connected zone discovery via regex patterns on markdown, not LLM | Zone overview pages have predictable structure: "Adjacent zones", "Subzones", navigation templates. Regex extraction from markdown headings and link patterns is sufficient and deterministic. _(D4, WC-6)_ |

---

## 1. Data Models

### 1.1 RabbitMQ Job Message

```python
# models.py

class CrawlJob(BaseModel):
    """Incoming crawl request from the job queue."""
    zone_name: str             # Zone slug e.g., "elwynn_forest"
    game: str = "wow"          # Game identifier
    priority: int = 0          # Higher = process sooner (seeds > discovered)
```

Messages are plain JSON on the queue. No MessageEnvelope wrapper — this service has no agent-to-agent communication. The dead-letter queue receives rejected messages with the original body intact.

### 1.2 Crawl Scope Configuration

```python
# models.py

class CrawlScopeCategory(BaseModel):
    """One category in the crawl scope definition."""
    search_queries: list[str]          # Templates with {zone} and {game} placeholders
    preferred_domains: list[str]       # Priority order (highest first)
    max_pages: int = 10                # Max pages to crawl per category
    include_patterns: list[str] = []   # URL path patterns to include (fnmatch)
    exclude_patterns: list[str] = []   # URL path patterns to exclude (fnmatch)

class CrawlScope(BaseModel):
    """Root of crawl_scope.yml — defines what to crawl per zone."""
    categories: dict[str, CrawlScopeCategory]
```

**Example `config/crawl_scope.yml`:**

```yaml
categories:
  zone_overview:
    search_queries:
      - "site:wowpedia.fandom.com {zone} zone"
      - "{zone} zone {game} wiki overview"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 5
    include_patterns:
      - "*/wiki/*"
    exclude_patterns:
      - "*/Special:*"
      - "*/User:*"
      - "*/Talk:*"
      - "*/File:*"

  npcs:
    search_queries:
      - "site:wowpedia.fandom.com {zone} NPCs notable characters"
      - "{zone} NPCs {game} wiki"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 10
    exclude_patterns:
      - "*/Special:*"
      - "*/User:*"

  factions:
    search_queries:
      - "site:wowpedia.fandom.com {zone} factions organizations"
      - "{zone} factions {game} wiki"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 8

  lore:
    search_queries:
      - "site:wowpedia.fandom.com {zone} lore history"
      - "{zone} lore mythology {game} wiki"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 8

  quests:
    search_queries:
      - "site:wowpedia.fandom.com {zone} quests quest chains"
      - "{zone} quests {game} wiki"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 10

  narrative_items:
    search_queries:
      - "site:wowpedia.fandom.com {zone} items artifacts legendary"
      - "{zone} notable items {game} wiki"
    preferred_domains:
      - wowpedia.fandom.com
      - warcraft.wiki.gg
    max_pages: 6
```

Categories map to WLR research topics: `zone_overview`, `npcs`, `factions`, `lore`, `narrative_items`. The `quests` category is additional scope for future Quest Lore Researcher.

### 1.3 Page Metadata Sidecar

```python
# models.py

class PageMetadata(BaseModel):
    """Sidecar metadata for a cached markdown file (.meta.json)."""
    url: str
    domain: str
    crawled_at: datetime
    content_hash: str          # SHA-256 hex digest of the markdown content
    http_status: int
    content_length: int        # Bytes
```

Written alongside each `.md` file. Enables change detection on refresh without reading the full content.

### 1.4 Graph Records (SurrealDB)

```python
# models.py

class CrawlZoneRecord(BaseModel):
    """Zone crawl state — tracks what's been crawled, not lore content."""
    name: str                          # Zone slug
    game: str                          # "wow"
    status: str                        # "pending" | "crawling" | "complete"
    crawled_at: datetime | None = None # Last successful crawl completion
    page_count: int = 0                # Total pages crawled for this zone

class CrawlPageRecord(BaseModel):
    """Individual crawled page metadata."""
    url: str
    title: str
    page_type: str                     # Category from crawl_scope.yml
    domain: str
    file_path: str                     # Relative to CRAWL_CACHE_ROOT
    content_hash: str                  # SHA-256
    crawled_at: datetime
    content_length: int
    http_status: int

class CrawlDomainRecord(BaseModel):
    """Source domain health tracking."""
    name: str                          # Domain hostname
    tier: str                          # From sources.yml (official, primary, etc.)
    consecutive_failures: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None
```

### 1.5 Internal Pipeline Types

```python
# models.py

class SearchResult(BaseModel):
    """A single URL from web search results."""
    url: str
    title: str
    domain: str
    tier: str                  # Source tier from sources.yml
    tier_weight: float         # Numeric weight for ranking

class CrawlResult(BaseModel):
    """Result of crawling a single URL."""
    url: str
    domain: str
    title: str
    content: str | None        # Markdown content (None if failed)
    links: list[str]           # Internal links extracted from the page
    http_status: int
    content_hash: str          # SHA-256 of content (empty string if failed)
    error: str | None = None   # Error message if failed
```

---

## 2. Crawl Pipeline

### 2.1 Per-Zone Flow

For each zone received from the queue, the crawler executes this pipeline:

```
CrawlJob arrives
  |
  v
Check freshness (graph query: crawl_zone status + crawled_at)
  |-- Fresh and complete -> skip, ack message
  |-- Stale or missing -> continue
  v
Set crawl_zone status = "crawling"
  |
  v
For each category in crawl_scope.yml:
  |
  +-> 2.2 Search Phase
  |     DuckDuckGo via Web Search MCP
  |     Query templates with {zone} and {game} filled in
  |     Collect URLs from search results
  |
  +-> 2.3 URL Selection
  |     Rank by domain tier (official > primary > secondary)
  |     Filter by include/exclude patterns
  |     Deduplicate (skip URLs already crawled for this zone)
  |     Cap at max_pages per category
  |
  +-> 2.4 Crawl Phase
  |     For each selected URL:
  |       Check circuit breaker for domain
  |       Throttle (per-domain rate limit)
  |       POST to crawl4ai /crawl endpoint
  |       Validate content (multi-signal block detection)
  |       Extract internal links for sub-page discovery
  |
  +-> 2.5 Store Phase
  |     Write markdown to filesystem
  |     Write .meta.json sidecar
  |     Create/update crawl_page in graph
  |     Create has_page edge (crawl_zone -> crawl_page)
  |     Create from_domain edge (crawl_page -> crawl_domain)
  |
  +-> 2.6 Link Discovery (optional)
        Internal links from crawled pages
        Filter to same wiki domain
        Add to this category's URL pool (respects max_pages cap)
  |
  v
2.7 Connected Zone Discovery
  Extract zone names from zone_overview content
  Create connected_to edges in graph
  Publish newly discovered zones to queue
  |
  v
Set crawl_zone status = "complete", update page_count
Ack message
```

### 2.2 Search Phase

```python
# crawler.py

async def search_for_category(
    zone_name: str,
    game: str,
    category: CrawlScopeCategory,
) -> list[SearchResult]:
    """Execute search queries for a category and collect results.

    Calls Web Search MCP (DuckDuckGo) for each query template.
    Results are deduplicated by URL and enriched with domain tier info.
    """
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for query_template in category.search_queries:
        query = query_template.format(
            zone=zone_name.replace("_", " "),
            game=game,
        )

        search_results = await mcp_call(
            MCP_WEB_SEARCH_URL,
            "search",
            {"query": query},
        )

        if not search_results:
            continue

        for item in search_results:
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            domain = urlparse(url).netloc
            tier, weight = get_domain_tier(domain)

            results.append(SearchResult(
                url=url,
                title=item.get("title", ""),
                domain=domain,
                tier=tier,
                tier_weight=weight,
            ))

    return results
```

### 2.3 URL Selection

```python
# crawler.py

def select_urls(
    search_results: list[SearchResult],
    category: CrawlScopeCategory,
    already_crawled: set[str],
) -> list[SearchResult]:
    """Rank, filter, and cap URLs for crawling.

    Priority: preferred_domains first (in order), then by tier weight.
    Excludes URLs matching exclude_patterns, includes only include_patterns
    (if any are defined). Skips already-crawled URLs.
    """
    filtered = []
    for result in search_results:
        if result.url in already_crawled:
            continue
        if not _matches_patterns(result.url, category.include_patterns, category.exclude_patterns):
            continue
        filtered.append(result)

    # Sort: preferred domains first (by position), then by tier weight
    def sort_key(r: SearchResult) -> tuple[int, float]:
        try:
            preferred_idx = category.preferred_domains.index(r.domain)
        except ValueError:
            preferred_idx = len(category.preferred_domains)
        return (preferred_idx, -r.tier_weight)

    filtered.sort(key=sort_key)
    return filtered[:category.max_pages]
```

### 2.4 Crawl Phase — crawl4ai `/crawl` Endpoint

Upgrade from the current `/md` endpoint to `/crawl` for full control:

```python
# crawler.py

async def crawl_page(url: str, throttle: DomainThrottle) -> CrawlResult:
    """Crawl a single URL via crawl4ai /crawl endpoint.

    1. Check circuit breaker
    2. Throttle per-domain
    3. POST to /crawl with browser stealth config
    4. Validate content (block detection)
    5. Extract internal links
    """
    domain = urlparse(url).netloc

    if throttle.is_tripped(domain):
        return CrawlResult(
            url=url, domain=domain, title="", content=None,
            links=[], http_status=0, content_hash="",
            error=f"Circuit breaker open for {domain}",
        )

    for attempt in range(MAX_BLOCK_RETRIES + 1):
        await throttle.wait(domain)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{CRAWL4AI_URL}/crawl",
                    json={
                        "urls": [url],
                        "browser_config": {
                            "headless": True,
                            "stealth_mode": True,
                            "user_agent_mode": "random",
                            "text_mode": True,
                        },
                        "crawler_config": {
                            "simulate_user": True,
                            "cache_mode": "bypass",
                            "page_timeout": 60000,
                            "wait_until": "networkidle",
                            "remove_overlay_elements": True,
                            "scan_full_page": True,
                            "score_links": True,
                        },
                    },
                )

            if response.status_code != 200:
                return CrawlResult(
                    url=url, domain=domain, title="", content=None,
                    links=[], http_status=response.status_code,
                    content_hash="", error=f"HTTP {response.status_code}",
                )

            data = response.json()
            result_data = data.get("results", [{}])[0]
            markdown = result_data.get("markdown", "")
            title = result_data.get("metadata", {}).get("title", "")
            links = _extract_internal_links(result_data, domain)

            if not markdown:
                return CrawlResult(
                    url=url, domain=domain, title=title, content=None,
                    links=links, http_status=200, content_hash="",
                    error="No content extracted",
                )

            # Block detection
            verdict = detect_blocked_content(markdown)
            if verdict.is_blocked:
                throttle.report_blocked(domain)
                if attempt < MAX_BLOCK_RETRIES:
                    continue
                return CrawlResult(
                    url=url, domain=domain, title=title, content=None,
                    links=[], http_status=200, content_hash="",
                    error=f"Blocked: {verdict.reason}",
                )

            throttle.report_success(domain)
            content_hash = hashlib.sha256(markdown.encode()).hexdigest()

            return CrawlResult(
                url=url, domain=domain, title=title, content=markdown,
                links=links, http_status=200, content_hash=content_hash,
            )

        except httpx.HTTPError as exc:
            return CrawlResult(
                url=url, domain=domain, title="", content=None,
                links=[], http_status=0, content_hash="",
                error=str(exc),
            )

    return CrawlResult(
        url=url, domain=domain, title="", content=None,
        links=[], http_status=0, content_hash="",
        error="Max retries exceeded",
    )
```

### 2.5 Store Phase

```python
# storage.py

async def store_page(
    crawl_result: CrawlResult,
    zone_name: str,
    game: str,
    category: str,
) -> str | None:
    """Store crawled content on filesystem and update graph.

    Returns the relative file path, or None if nothing to store.
    """
    if not crawl_result.content:
        return None

    # 1. Filesystem write
    page_slug = _url_to_slug(crawl_result.url)
    relative_path = f"{game}/{zone_name}/{category}/{page_slug}.md"
    full_path = Path(CRAWL_CACHE_ROOT) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(crawl_result.content, encoding="utf-8")

    # 2. Sidecar metadata
    metadata = PageMetadata(
        url=crawl_result.url,
        domain=crawl_result.domain,
        crawled_at=datetime.now(timezone.utc),
        content_hash=crawl_result.content_hash,
        http_status=crawl_result.http_status,
        content_length=len(crawl_result.content.encode("utf-8")),
    )
    sidecar_path = full_path.with_suffix(".meta.json")
    sidecar_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

    # 3. Graph: create/update crawl_page record
    page_id = _url_to_record_id(crawl_result.url)
    await mcp_call(MCP_STORAGE_URL, "create_record", {
        "table": "crawl_page",
        "record_id": page_id,
        "data": json.dumps({
            "url": crawl_result.url,
            "title": crawl_result.title,
            "page_type": category,
            "domain": crawl_result.domain,
            "file_path": relative_path,
            "content_hash": crawl_result.content_hash,
            "crawled_at": metadata.crawled_at.isoformat(),
            "content_length": metadata.content_length,
            "http_status": crawl_result.http_status,
        }),
    })

    # 4. Graph: has_page edge (zone -> page)
    await mcp_call(MCP_STORAGE_URL, "create_relation", {
        "relation_type": "has_page",
        "from_record": f"crawl_zone:{zone_name}",
        "to_record": f"crawl_page:{page_id}",
        "properties": json.dumps({
            "page_type": category,
            "discovery_method": "search",
        }),
    })

    # 5. Graph: from_domain edge (page -> domain)
    domain_id = crawl_result.domain.replace(".", "_")
    await mcp_call(MCP_STORAGE_URL, "create_relation", {
        "relation_type": "from_domain",
        "from_record": f"crawl_page:{page_id}",
        "to_record": f"crawl_domain:{domain_id}",
    })

    return relative_path
```

### 2.6 Link Discovery

After crawling a page, internal links are extracted and added to the category's URL pool:

```python
# crawler.py

def _extract_internal_links(crawl_result_data: dict, source_domain: str) -> list[str]:
    """Extract internal wiki links from crawl4ai result.

    Filters to same-domain links, excludes Special/User/Talk pages.
    """
    links = crawl_result_data.get("links", {})
    internal = links.get("internal", [])

    valid_links = []
    for link_info in internal:
        url = link_info.get("href", "")
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != source_domain:
            continue
        # Exclude wiki meta pages
        path = parsed.path.lower()
        if any(seg in path for seg in ["/special:", "/user:", "/talk:", "/file:", "/template:"]):
            continue
        valid_links.append(url)

    return valid_links
```

### 2.7 Connected Zone Discovery

Deterministic extraction from zone overview markdown content:

```python
# crawler.py

# Patterns for adjacent/connected zone sections in wiki markdown
_ZONE_SECTION_PATTERNS = [
    re.compile(r"#{2,3}\s*(?:adjacent|neighboring|connected|nearby)\s+zones?", re.IGNORECASE),
    re.compile(r"#{2,3}\s*subzones?", re.IGNORECASE),
    re.compile(r"#{2,3}\s*(?:borders?|boundaries)", re.IGNORECASE),
]

# Wiki link pattern: [Zone Name](/wiki/Zone_Name) or [[Zone Name]]
_WIKI_LINK_RE = re.compile(r"\[([^\]]+)\]\(/wiki/([^)]+)\)")
_WIKITEXT_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_connected_zones(overview_content: str, source_zone: str) -> list[str]:
    """Extract connected zone names from a zone overview page.

    Looks for "Adjacent zones", "Subzones", "Borders" sections and
    extracts zone names from wiki links within those sections.
    Best-effort — returns empty list if no sections found.
    """
    connected: list[str] = []
    lines = overview_content.split("\n")

    in_zone_section = False
    for line in lines:
        # Check if we're entering a zone section
        for pattern in _ZONE_SECTION_PATTERNS:
            if pattern.search(line):
                in_zone_section = True
                break

        # Check if we've hit the next section (exit)
        if in_zone_section and line.startswith("## ") and not any(p.search(line) for p in _ZONE_SECTION_PATTERNS):
            in_zone_section = False

        if not in_zone_section:
            continue

        # Extract zone names from wiki links
        for match in _WIKI_LINK_RE.finditer(line):
            zone_slug = _normalize_zone_slug(match.group(2))
            if zone_slug and zone_slug != source_zone:
                connected.append(zone_slug)

        for match in _WIKITEXT_LINK_RE.finditer(line):
            zone_slug = _normalize_zone_slug(match.group(1))
            if zone_slug and zone_slug != source_zone:
                connected.append(zone_slug)

    return list(dict.fromkeys(connected))  # Deduplicate, preserve order
```

---

## 3. SurrealDB Graph Schema

### 3.1 Tables

Three new tables added to Storage MCP:

**`crawl_zone`** — Zone crawl state tracking

```sql
DEFINE TABLE crawl_zone SCHEMAFULL;
DEFINE FIELD name ON crawl_zone TYPE string;
DEFINE FIELD game ON crawl_zone TYPE string;
DEFINE FIELD status ON crawl_zone TYPE string
    ASSERT $value IN ["pending", "crawling", "complete"];
DEFINE FIELD crawled_at ON crawl_zone TYPE option<datetime>;
DEFINE FIELD page_count ON crawl_zone TYPE int DEFAULT 0;
DEFINE FIELD updated_at ON crawl_zone TYPE option<datetime>;
DEFINE INDEX idx_crawl_zone_status ON crawl_zone FIELDS status;
DEFINE INDEX idx_crawl_zone_crawled_at ON crawl_zone FIELDS crawled_at;
```

**`crawl_page`** — Individual page metadata

```sql
DEFINE TABLE crawl_page SCHEMAFULL;
DEFINE FIELD url ON crawl_page TYPE string;
DEFINE FIELD title ON crawl_page TYPE string;
DEFINE FIELD page_type ON crawl_page TYPE string;
DEFINE FIELD domain ON crawl_page TYPE string;
DEFINE FIELD file_path ON crawl_page TYPE string;
DEFINE FIELD content_hash ON crawl_page TYPE string;
DEFINE FIELD crawled_at ON crawl_page TYPE datetime;
DEFINE FIELD content_length ON crawl_page TYPE int;
DEFINE FIELD http_status ON crawl_page TYPE int;
DEFINE FIELD updated_at ON crawl_page TYPE option<datetime>;
DEFINE INDEX idx_crawl_page_type ON crawl_page FIELDS page_type;
DEFINE INDEX idx_crawl_page_domain ON crawl_page FIELDS domain;
DEFINE INDEX idx_crawl_page_url ON crawl_page FIELDS url UNIQUE;
```

**`crawl_domain`** — Source domain health

```sql
DEFINE TABLE crawl_domain SCHEMAFULL;
DEFINE FIELD name ON crawl_domain TYPE string;
DEFINE FIELD tier ON crawl_domain TYPE string;
DEFINE FIELD consecutive_failures ON crawl_domain TYPE int DEFAULT 0;
DEFINE FIELD last_success ON crawl_domain TYPE option<datetime>;
DEFINE FIELD last_failure ON crawl_domain TYPE option<datetime>;
DEFINE FIELD updated_at ON crawl_domain TYPE option<datetime>;
```

### 3.2 Graph Edges

```sql
-- Zone owns pages (with edge properties)
DEFINE TABLE has_page SCHEMAFULL TYPE RELATION
    FROM crawl_zone TO crawl_page;
DEFINE FIELD page_type ON has_page TYPE string;
DEFINE FIELD discovery_method ON has_page TYPE string
    ASSERT $value IN ["search", "link_extraction", "seed"];

-- Zone adjacency (discovered from content)
DEFINE TABLE connected_to SCHEMAFULL TYPE RELATION
    FROM crawl_zone TO crawl_zone;

-- Internal wiki links between pages
DEFINE TABLE links_to SCHEMAFULL TYPE RELATION
    FROM crawl_page TO crawl_page;

-- Page-to-domain relationship
DEFINE TABLE from_domain SCHEMAFULL TYPE RELATION
    FROM crawl_page TO crawl_domain;
```

Note: `connected_to` reuses the same relation name that exists in the WLR's lore graph (`zone -> CONNECTS_TO -> zone`). This is intentional — both represent zone adjacency. In SurrealDB, the relation table is shared but the record types (`crawl_zone` vs `zone`) disambiguate. We define a new `connected_to` relation table specifically typed `FROM crawl_zone TO crawl_zone`.

### 3.3 Key Graph Queries

**All pages of a category for a zone:**
```sql
SELECT ->has_page[WHERE page_type = 'npcs']->crawl_page.* FROM crawl_zone:elwynn_forest
```

**All stale pages (older than N days):**
```sql
SELECT * FROM crawl_page WHERE crawled_at < time::now() - 7d
```

**Connected zones from a zone:**
```sql
SELECT ->connected_to->crawl_zone.name FROM crawl_zone:elwynn_forest
```

**Domain health status:**
```sql
SELECT * FROM crawl_domain WHERE consecutive_failures >= 3
```

**All file paths for a zone (for WLR to read):**
```sql
SELECT ->has_page->crawl_page.{file_path, page_type, content_hash} FROM crawl_zone:elwynn_forest
```

**Oldest zone for refresh:**
```sql
SELECT * FROM crawl_zone WHERE status = 'complete' ORDER BY crawled_at ASC LIMIT 1
```

### 3.4 Storage MCP Extensions

```python
# mcp_storage/src/server.py — additions

VALID_TABLES = {
    "zone", "npc", "faction", "lore", "narrative_item",
    "crawl_zone", "crawl_page", "crawl_domain",                    # NEW
}

VALID_RELATIONS = {
    "connects_to", "belongs_to", "located_in", "relates_to",
    "child_of", "stance_toward", "found_in", "about",
    "has_page", "connected_to", "links_to", "from_domain",         # NEW
}
```

Schema initialization (`mcp_storage/src/schema.py`) adds the table and relation definitions from 3.1 and 3.2 above.

No new MCP tools are needed. The existing generic tools handle all operations:
- `create_record` / `update_record` / `get_record` / `query_records` for CRUD
- `create_relation` / `traverse` for graph operations

---

## 4. Daemon Lifecycle

### 4.1 Startup

```
1. Load config (env vars + crawl_scope.yml + sources.yml)
2. Validate config (crawl_scope categories exist, source tiers valid)
3. Connect to RabbitMQ with exponential backoff
4. Declare queue: CRAWL_JOB_QUEUE with DLQ binding
5. Test Storage MCP connectivity (mcp_call to get_record)
6. Test crawl4ai connectivity (HTTP GET to health endpoint)
7. Initialize DomainThrottle (from shared/crawl.py)
8. Set prefetch = 1 (process one zone at a time)
9. Register signal handlers (SIGTERM, SIGINT)
10. Log daemon_started, begin consuming
```

### 4.2 Main Loop — Two Modes

```
                    ┌─────────────────────┐
                    │   Check Job Queue    │
                    │  (non-blocking get)  │
                    └────────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │  Message found? │
                    └────────┬────────┘
                        yes/ \no
                           /   \
              ┌───────────┐     ┌─────────────┐
              │  Mode A:  │     │  Mode B:     │
              │  Process  │     │  Refresh     │
              │  Seed     │     │  (one zone)  │
              └─────┬─────┘     └──────┬──────┘
                    │                  │
                    └────────┬─────────┘
                             │
                        Back to top
```

**Mode A — Seed Processing** (priority):

```python
# daemon.py

async def _process_seed(self, message: aio_pika.IncomingMessage) -> None:
    """Process a crawl job from the queue."""
    try:
        body = json.loads(message.body.decode())
        job = CrawlJob.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Malformed message rejected to DLQ", extra={
            "error": str(exc), "body": message.body.decode()[:500],
        })
        await message.reject(requeue=False)  # -> DLQ
        return

    # Check freshness
    zone_record = await self._get_zone_record(job.zone_name)
    if zone_record and zone_record["status"] == "complete":
        crawled_at = datetime.fromisoformat(zone_record["crawled_at"])
        age_hours = (datetime.now(timezone.utc) - crawled_at).total_seconds() / 3600
        if age_hours < REFRESH_INTERVAL_HOURS:
            logger.info("Zone fresh, skipping", extra={
                "zone": job.zone_name, "age_hours": round(age_hours, 1),
            })
            await message.ack()
            return

    # Execute crawl
    await self._crawl_zone(job.zone_name, job.game)
    await message.ack()
```

**Mode B — Refresh** (when queue is empty):

```python
# daemon.py

async def _refresh_oldest_zone(self) -> bool:
    """Find and refresh the oldest stale zone. Returns True if work was done."""
    # Query graph for oldest complete zone past refresh interval
    result = await mcp_call(MCP_STORAGE_URL, "query_records", {
        "table": "crawl_zone",
        "filter_expr": f"status = 'complete' AND crawled_at < time::now() - {REFRESH_INTERVAL_HOURS}h",
        "limit": 1,
    })

    if not result or (isinstance(result, list) and len(result) == 0):
        return False

    zone = result[0] if isinstance(result, list) else result
    zone_name = zone["name"]
    game = zone["game"]

    logger.info("Refresh cycle starting", extra={"zone": zone_name})
    await self._crawl_zone(zone_name, game, is_refresh=True)
    return True
```

### 4.3 Zone Crawl Execution

```python
# daemon.py

async def _crawl_zone(
    self,
    zone_name: str,
    game: str,
    is_refresh: bool = False,
) -> None:
    """Execute the full crawl pipeline for a zone."""
    logger.info("zone_crawl_started", extra={
        "zone": zone_name, "game": game, "is_refresh": is_refresh,
    })
    start = time.monotonic()

    # Set zone status to crawling
    await self._upsert_zone_record(zone_name, game, status="crawling")

    pages_stored = 0
    pages_failed = 0
    already_crawled: set[str] = set()

    for category_name, category_config in self.crawl_scope.categories.items():
        # 1. Search
        search_results = await search_for_category(zone_name, game, category_config)

        # 2. Select URLs
        selected = select_urls(search_results, category_config, already_crawled)

        # 3. Crawl + store each URL
        for search_result in selected:
            crawl_result = await crawl_page(search_result.url, self.throttle)
            already_crawled.add(search_result.url)

            if crawl_result.content:
                file_path = await store_page(
                    crawl_result, zone_name, game, category_name,
                )
                if file_path:
                    pages_stored += 1

                    # Store inter-page links in graph
                    for link_url in crawl_result.links:
                        await self._create_page_link(crawl_result.url, link_url)

                # Link-discovered sub-pages (add to selection pool)
                for link_url in crawl_result.links:
                    if link_url not in already_crawled and len(already_crawled) < category_config.max_pages:
                        sub_result = await crawl_page(link_url, self.throttle)
                        already_crawled.add(link_url)
                        if sub_result.content:
                            await store_page(sub_result, zone_name, game, category_name)
                            pages_stored += 1
            else:
                pages_failed += 1
                logger.warning("page_crawl_failed", extra={
                    "zone": zone_name, "url": search_result.url,
                    "error": crawl_result.error,
                })

    # Connected zone discovery (from zone_overview pages)
    await self._discover_and_publish_connected_zones(zone_name, game)

    # Update zone record
    await self._upsert_zone_record(
        zone_name, game, status="complete", page_count=pages_stored,
    )

    duration = time.monotonic() - start
    logger.info("zone_crawl_completed", extra={
        "zone": zone_name, "pages_stored": pages_stored,
        "pages_failed": pages_failed, "duration_s": round(duration, 1),
    })
```

### 4.4 Connected Zone Publishing

```python
# daemon.py

async def _discover_and_publish_connected_zones(
    self,
    zone_name: str,
    game: str,
) -> None:
    """Extract connected zones from overview content and publish to queue."""
    # Read zone overview files from filesystem
    overview_dir = Path(CRAWL_CACHE_ROOT) / game / zone_name / "zone_overview"
    if not overview_dir.exists():
        return

    all_connected: list[str] = []
    for md_file in overview_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        connected = extract_connected_zones(content, zone_name)
        all_connected.extend(connected)

    # Deduplicate
    unique_zones = list(dict.fromkeys(all_connected))

    for connected_zone in unique_zones:
        # Check if already in graph (deduplication)
        existing = await mcp_call(MCP_STORAGE_URL, "get_record", {
            "table": "crawl_zone",
            "record_id": connected_zone,
        })

        # Create connected_to edge regardless
        await mcp_call(MCP_STORAGE_URL, "create_relation", {
            "relation_type": "connected_to",
            "from_record": f"crawl_zone:{zone_name}",
            "to_record": f"crawl_zone:{connected_zone}",
        })

        if not existing:
            # New zone — create pending record and publish to queue
            await mcp_call(MCP_STORAGE_URL, "create_record", {
                "table": "crawl_zone",
                "record_id": connected_zone,
                "data": json.dumps({
                    "name": connected_zone,
                    "game": game,
                    "status": "pending",
                    "page_count": 0,
                }),
            })

            # Publish crawl job (lower priority than manual seeds)
            job = CrawlJob(zone_name=connected_zone, game=game, priority=-1)
            await self._publish_job(job)

            logger.info("connected_zone_discovered", extra={
                "source_zone": zone_name, "target_zone": connected_zone,
            })
```

### 4.5 Refresh Mode — Change Detection

During refresh cycles, compare content hashes before overwriting:

```python
# storage.py

async def store_page_with_change_detection(
    crawl_result: CrawlResult,
    zone_name: str,
    game: str,
    category: str,
) -> tuple[str | None, bool]:
    """Store crawled content with change detection.

    Returns (file_path, changed). On refresh, compares content hash
    against existing sidecar. Only overwrites if content changed.
    """
    if not crawl_result.content:
        return None, False

    page_slug = _url_to_slug(crawl_result.url)
    relative_path = f"{game}/{zone_name}/{category}/{page_slug}.md"
    full_path = Path(CRAWL_CACHE_ROOT) / relative_path
    sidecar_path = full_path.with_suffix(".meta.json")

    changed = True
    if sidecar_path.exists():
        existing = PageMetadata.model_validate_json(sidecar_path.read_text())
        if existing.content_hash == crawl_result.content_hash:
            # Content unchanged — update only crawled_at timestamp
            existing.crawled_at = datetime.now(timezone.utc)
            sidecar_path.write_text(existing.model_dump_json(indent=2), encoding="utf-8")
            changed = False

    if changed:
        # Write new content + full sidecar update
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(crawl_result.content, encoding="utf-8")

        metadata = PageMetadata(
            url=crawl_result.url,
            domain=crawl_result.domain,
            crawled_at=datetime.now(timezone.utc),
            content_hash=crawl_result.content_hash,
            http_status=crawl_result.http_status,
            content_length=len(crawl_result.content.encode("utf-8")),
        )
        sidecar_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

        logger.info("content_changed", extra={
            "url": crawl_result.url,
            "old_hash": existing.content_hash if sidecar_path.exists() else "none",
            "new_hash": crawl_result.content_hash,
        })

    # Update graph timestamp regardless
    page_id = _url_to_record_id(crawl_result.url)
    await mcp_call(MCP_STORAGE_URL, "update_record", {
        "table": "crawl_page",
        "record_id": page_id,
        "data": json.dumps({
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": crawl_result.content_hash,
        }),
    })

    return relative_path, changed
```

### 4.6 RabbitMQ Topology

```
Exchange: (default direct exchange)

Queue: s.wiki_crawler.jobs
  - Durable: true
  - Arguments:
    x-dead-letter-exchange: ""
    x-dead-letter-routing-key: s.wiki_crawler.jobs.dlq
    x-message-ttl: 86400000  (24h for stuck messages)

Queue: s.wiki_crawler.jobs.dlq
  - Durable: true
  - Purpose: Receives malformed/rejected messages for inspection
```

The service uses a single queue for both input and output (discovered zones published back). Priority ordering is handled by RabbitMQ's priority queue feature:

```python
# daemon.py — queue declaration

await channel.declare_queue(
    CRAWL_JOB_QUEUE,
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": f"{CRAWL_JOB_QUEUE}.dlq",
        "x-max-priority": 10,
    },
)
```

### 4.7 Shutdown

```python
# daemon.py

async def _shutdown(self) -> None:
    """Graceful shutdown — finish current page, close connections."""
    logger.info("daemon_shutdown", extra={"reason": "signal"})
    self._running = False
    # Current zone processing completes (page-level granularity)
    # RabbitMQ connection closes (unacked message redelivered on restart)
```

---

## 5. Error Handling

| Scenario | Strategy | Requirement |
|----------|----------|-------------|
| Malformed RabbitMQ message | Reject to DLQ with logged reason | WC-1 |
| Duplicate zone (fresh) | Skip, ack message, log | WC-1 |
| Web search returns no results | Log, skip category, continue | WC-3 |
| crawl4ai page failure | Log, skip page, continue with remaining | WC-3 |
| HTTP 429 from crawl4ai | Backoff + retry once, then skip | WC-3 |
| Block page detected | Backoff + retry once, then skip | WC-3 |
| Circuit breaker tripped | Refuse domain immediately, skip page | WC-3 |
| Filesystem write failure | Log error, skip page, continue | WC-4 |
| Storage MCP unavailable | Retry with backoff, fail zone if persistent | WC-5 |
| Connected zone extraction fails | Best-effort — empty list, continue | WC-6 |
| RabbitMQ disconnect | Reconnect with exponential backoff | WC-1 |
| Daemon crash mid-zone | Unacked message redelivered on restart, zone re-crawled | WC-1 |

**Fail-forward principle:** No single page failure stops the zone crawl. Failed pages are logged and skipped. The zone completes with whatever pages succeeded.

---

## 6. Structured Logging

All events as JSON with base fields: `service_id` ("wiki_crawler"), `timestamp`, `level`, `event`.

| Event | Level | Additional Fields |
|-------|-------|-------------------|
| `daemon_started` | info | config summary (queue, cache root, refresh interval) |
| `zone_crawl_started` | info | zone, game, is_refresh |
| `zone_crawl_completed` | info | zone, pages_stored, pages_failed, duration_s |
| `page_crawl_success` | debug | url, domain, content_length, content_hash |
| `page_crawl_failed` | warn | url, domain, error, attempt_count |
| `block_detected` | warn | url, domain, detection_reason |
| `circuit_breaker_tripped` | warn | domain, consecutive_failures |
| `connected_zone_discovered` | info | source_zone, target_zone |
| `refresh_cycle_started` | info | zone |
| `content_changed` | info | url, old_hash, new_hash |
| `message_rejected` | warn | error, body_preview |
| `daemon_shutdown` | info | reason |

---

## 7. Docker Integration

### 7.1 Service Definition

```yaml
# docker-compose.yml addition

  wiki-crawler:
    build:
      context: .
      dockerfile: s_wiki_crawler/Dockerfile
    env_file: ./s_wiki_crawler/.env
    environment:
      - RABBITMQ_URL=amqp://mythline:mythline@rabbitmq:5672/
      - MCP_STORAGE_URL=http://mcp-storage:8005/mcp
      - MCP_WEB_SEARCH_URL=http://mcp-web-search:8006/mcp
      - CRAWL4AI_URL=http://crawl4ai:11235
      - CRAWL_CACHE_ROOT=/data/cache
    volumes:
      - wiki_cache:/data/cache
    depends_on:
      rabbitmq:
        condition: service_healthy
      mcp-storage:
        condition: service_healthy
      mcp-web-search:
        condition: service_healthy
      crawl4ai:
        condition: service_healthy
    restart: unless-stopped

volumes:
  wiki_cache:
    driver: local
```

### 7.2 Dockerfile

```dockerfile
# s_wiki_crawler/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install shared utilities
COPY shared/ /app/shared/

# Install dependencies
COPY s_wiki_crawler/pyproject.toml s_wiki_crawler/uv.lock ./
RUN pip install uv && uv sync

# Copy service code
COPY s_wiki_crawler/ .

CMD ["python", "-m", "src.daemon"]
```

### 7.3 Service Folder Structure

```
s_wiki_crawler/
├── Dockerfile
├── .env.example
├── pyproject.toml
├── conftest.py                    # Adds repo root to sys.path
├── config/
│   ├── crawl_scope.yml            # Category definitions + search templates
│   └── sources.yml                # Source tier definitions (copy from WLR)
├── src/
│   ├── __init__.py
│   ├── config.py                  # Env vars + YAML config loaders
│   ├── models.py                  # All Pydantic models (CrawlJob, PageMetadata, etc.)
│   ├── daemon.py                  # Main loop, RabbitMQ, lifecycle
│   ├── crawler.py                 # Search, URL selection, crawl4ai calls, link extraction
│   ├── storage.py                 # Filesystem writes + graph operations
│   └── logging_config.py          # Structured JSON logging
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_models.py
    ├── test_crawler.py
    ├── test_storage.py
    └── test_daemon.py
```

Key differences from agent blueprint:
- No `prompts/` directory (no LLM, no prompts)
- No `agent.py` (no pydantic-ai agent)
- No `config/mcp_config.json` (calls MCP directly via shared helpers, not via toolsets)
- Has `crawler.py` and `storage.py` instead

---

## 8. Configuration

### 8.1 Environment Variables

```python
# config.py

SERVICE_ID = "wiki_crawler"
GAME_NAME = os.getenv("GAME_NAME", "wow")

# RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://mythline:mythline@rabbitmq:5672/")
CRAWL_JOB_QUEUE = os.getenv("CRAWL_JOB_QUEUE", "s.wiki_crawler.jobs")

# MCP Services
MCP_STORAGE_URL = os.getenv("MCP_STORAGE_URL", "http://mcp-storage:8005/mcp")
MCP_WEB_SEARCH_URL = os.getenv("MCP_WEB_SEARCH_URL", "http://mcp-web-search:8006/mcp")

# crawl4ai
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:11235")

# Filesystem
CRAWL_CACHE_ROOT = os.getenv("CRAWL_CACHE_ROOT", "./cache")

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30"))
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))

# Refresh
REFRESH_INTERVAL_HOURS = int(os.getenv("REFRESH_INTERVAL_HOURS", "168"))

# Crawl limits
MAX_PAGES_PER_CATEGORY = int(os.getenv("MAX_PAGES_PER_CATEGORY", "10"))
MAX_BLOCK_RETRIES = 1
```

### 8.2 Config Loaders

```python
# config.py

def load_crawl_scope() -> CrawlScope:
    """Load and validate crawl_scope.yml."""
    config_path = Path(__file__).parent.parent / "config" / "crawl_scope.yml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return CrawlScope.model_validate(raw)

def load_sources_config() -> dict:
    """Load source tier definitions from sources.yml."""
    config_path = Path(__file__).parent.parent / "config" / "sources.yml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))

def get_domain_tier(domain: str) -> tuple[str, float]:
    """Return (tier_name, weight) for a domain. Unknown domains get lowest tier."""
    sources = load_sources_config()
    for tier_name, tier_data in sources["source_tiers"].items():
        if domain in tier_data.get("domains", []):
            return tier_name, tier_data.get("weight", 0.5)
    return "unknown", 0.3
```

---

## Shared Utilities — `shared/crawl.py`

Extracted from `a_world_lore_researcher/src/mcp_client.py`:

```python
# shared/crawl.py

# Exports:
#   CrawlVerdict           — dataclass (is_blocked, reason)
#   detect_blocked_content  — multi-signal block detection (3 stages)
#   DomainThrottle         — per-domain rate limiter with backoff + circuit breaker
```

The WLR's `mcp_client.py` imports from `shared.crawl` instead of defining these inline. Both services use the same detection logic and throttle implementation.

---

## Files Changed

### New

| File | Purpose |
|------|---------|
| `s_wiki_crawler/` | Entire service directory (Dockerfile, config, src, tests) |
| `s_wiki_crawler/src/daemon.py` | Main loop, RabbitMQ lifecycle, zone crawl orchestration _(WC-1, WC-7)_ |
| `s_wiki_crawler/src/crawler.py` | Search, URL selection, crawl4ai calls, block detection, link extraction _(WC-2, WC-3)_ |
| `s_wiki_crawler/src/storage.py` | Filesystem writes, sidecar metadata, graph operations _(WC-4, WC-5)_ |
| `s_wiki_crawler/src/models.py` | All Pydantic models: CrawlJob, CrawlScope*, PageMetadata, graph records _(WC-1 through WC-5)_ |
| `s_wiki_crawler/src/config.py` | Env vars, YAML loaders, domain tier lookup _(WC-2)_ |
| `s_wiki_crawler/src/logging_config.py` | Structured JSON logging setup _(WC-8)_ |
| `s_wiki_crawler/config/crawl_scope.yml` | Category definitions and search templates _(WC-2)_ |
| `s_wiki_crawler/config/sources.yml` | Source tier definitions (copy from WLR) _(WC-2)_ |
| `s_wiki_crawler/tests/` | Unit tests for all source modules |
| `shared/crawl.py` | Extracted: DomainThrottle, detect_blocked_content, CrawlVerdict _(D5)_ |

### Modified

| File | Change |
|------|--------|
| `mcp_storage/src/server.py` | Add `crawl_zone`, `crawl_page`, `crawl_domain` to VALID_TABLES. Add `has_page`, `connected_to`, `links_to`, `from_domain` to VALID_RELATIONS. _(WC-5, D3)_ |
| `mcp_storage/src/schema.py` | Add schema initialization for new crawl tables and relation tables. _(WC-5)_ |
| `docker-compose.yml` | Add `wiki-crawler` service definition + `wiki_cache` volume. _(D1)_ |
| `a_world_lore_researcher/src/mcp_client.py` | Import `DomainThrottle`, `detect_blocked_content`, `CrawlVerdict` from `shared.crawl` instead of defining inline. Remove the moved code. _(D5)_ |

### Unchanged

| File | Reason |
|------|--------|
| `a_world_lore_researcher/src/agent.py` | No changes — WLR integration is out of scope |
| `mcp_web_search/` | No changes — existing DuckDuckGo search tools work as-is |
| `shared/prompt_loader.py` | Not used by wiki crawler (no prompts) |
| `shared/config_loader.py` | Not used by wiki crawler (no MCP toolsets) |

---

## Future Work (Out of Scope)

- **WLR integration** — Modifying the WLR to read from cached files instead of live crawling. Requires a separate spec after validating crawl quality.
- **Multi-game support** — Config is game-agnostic by design, but only WoW configs will be built in this spec.
- **UI/dashboard** — No web interface. Structured logs are the monitoring surface.
- **Embedding generation** — No vector embeddings on crawled content. That's the WLR's or Storage MCP's job.
- **Parallel zone crawling** — Zones are processed sequentially. Parallel zone processing is a future optimization.
- **LLM-assisted zone discovery** — Current regex extraction is best-effort. An LLM could improve discovery accuracy but defeats the deterministic design goal.
