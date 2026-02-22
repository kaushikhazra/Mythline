# Crawl4AI MCP Server Research

**Date**: 2026-02-22
**Purpose**: Evaluate crawl4ai as a replacement for our custom `mcp_web_crawler` service (trafilatura + httpx) which cannot bypass anti-bot protection on Fandom/Wowhead.
**Decision Required**: Use crawl4ai as a Docker MCP service vs. as a Python library inside our own MCP service.

---

## 1. Official crawl4ai MCP Server

### Built-in MCP Support (Official)

Crawl4ai v0.8.0 ships with **built-in MCP server endpoints** in its Docker image. This is not a third-party wrapper -- it is part of the official `unclecode/crawl4ai` Docker image. When you run the Docker container, MCP endpoints are automatically available alongside the REST API.

**Built-in MCP endpoints:**
- SSE: `http://localhost:11235/mcp/sse`
- WebSocket: `ws://localhost:11235/mcp/ws`
- Schema reference: `http://localhost:11235/mcp/schema`

**Built-in MCP tools (7 total):**

| Tool | Purpose |
|------|---------|
| `md` | Generate markdown from web content |
| `html` | Extract preprocessed HTML |
| `screenshot` | Capture full-page PNG screenshots |
| `pdf` | Generate PDF documents |
| `execute_js` | Run JavaScript snippets on pages |
| `crawl` | Multi-URL crawling operations |
| `ask` | Query crawl4ai library context |

### Community MCP Wrappers

Several community forks exist that wrap crawl4ai as standalone MCP servers:

| Project | Transport | Tools | Notes |
|---------|-----------|-------|-------|
| `sadiuysal/crawl4ai-mcp-server` | stdio only | scrape, crawl, crawl_site, crawl_sitemap | Lightweight, Docker image at `uysalsadi/crawl4ai-mcp-server` |
| `sruckh/crawl-mcp` | stdio, StreamableHTTP, SSE | crawl_url, Google search, YouTube transcripts, file processing | Heavy -- 1.5-3GB images, many extra features |
| `stgmt/crawl4ai-mcp` | stdio, SSE, HTTP | crawl, md, html, screenshot, pdf, execute_js | Adds bearer token auth, remote endpoint routing |

**Key finding**: The community wrappers offer `scrape/crawl/crawl_site/crawl_sitemap` tools which are more aligned with our use case (simple URL-to-markdown extraction) than the official built-in tools which are oriented toward the full crawl4ai feature set.

---

## 2. Docker Deployment

### Image Details

- **Image**: `unclecode/crawl4ai:0.8.0` (also tagged as `latest`)
- **Architecture**: Multi-arch (linux/amd64, linux/arm64)
- **Port**: 11235
- **Shared memory**: `--shm-size=1g` required for Chromium

### Quick Start

```bash
docker pull unclecode/crawl4ai:0.8.0
docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --shm-size=1g \
  unclecode/crawl4ai:0.8.0
```

### Docker Compose (from official repo)

```yaml
services:
  crawl4ai:
    image: unclecode/crawl4ai:${TAG:-latest}
    ports:
      - "11235:11235"
    volumes:
      - /dev/shm:/dev/shm
    env_file:
      - .llm.env  # optional, for LLM-based extraction
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11235/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    user: appuser
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | For LLM-based extraction (optional) |
| `ANTHROPIC_API_KEY` | For LLM-based extraction (optional) |
| `LLM_PROVIDER` | Override default LLM provider (optional) |
| `LLM_TEMPERATURE` | LLM temperature (optional) |
| `LLM_BASE_URL` | Custom LLM endpoint (optional) |

**Note**: We do not need LLM keys for basic markdown extraction. They are only needed for the LLM extraction strategy.

### Available Endpoints

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:11235/crawl` | Standard crawl (POST) |
| `http://localhost:11235/crawl/stream` | Streaming crawl (POST) |
| `http://localhost:11235/html` | HTML extraction (POST) |
| `http://localhost:11235/screenshot` | Screenshot capture (POST) |
| `http://localhost:11235/pdf` | PDF generation (POST) |
| `http://localhost:11235/execute_js` | JS execution (POST) |
| `http://localhost:11235/crawl/job` | Async jobs with webhooks (POST) |
| `http://localhost:11235/playground` | Interactive web UI |
| `http://localhost:11235/monitor` | Real-time monitoring dashboard |
| `http://localhost:11235/health` | Health check |
| `http://localhost:11235/mcp/sse` | MCP SSE endpoint |
| `ws://localhost:11235/mcp/ws` | MCP WebSocket endpoint |
| `http://localhost:11235/mcp/schema` | MCP tool schemas |

### Build Arguments for Custom Builds

| Argument | Default | Options |
|----------|---------|---------|
| `INSTALL_TYPE` | `default` | default, all, torch, transformer |
| `ENABLE_GPU` | `false` | true, false |

---

## 3. MCP Tools Exposed

### Built-in MCP Tools (Official Docker Image)

The built-in MCP exposes 7 tools. Full schemas are available at `/mcp/schema`. Based on documentation:

**`md`** - Extract markdown from a URL
- Input: URL and options
- Output: Markdown content

**`html`** - Extract preprocessed HTML
- Input: URL and options
- Output: Cleaned HTML

**`screenshot`** - Capture full-page PNG
- Input: URL
- Output: Base64-encoded PNG

**`pdf`** - Generate PDF of page
- Input: URL
- Output: PDF data

**`execute_js`** - Run JavaScript on a page
- Input: URL, JavaScript code
- Output: Execution result

**`crawl`** - Multi-URL crawling
- Input: URLs, config options
- Output: List of crawl results

**`ask`** - Query crawl4ai context
- Input: Question string
- Output: Answer based on crawl4ai docs

### Community Wrapper Tools (sadiuysal/crawl4ai-mcp-server)

The community wrapper exposes 4 tools more aligned with our use case:

**`scrape`**
- Parameters: `url` (required), `output_dir` (optional)
- Returns: JSON with url, markdown content, metadata

**`crawl`**
- Parameters: `seed_url`, `max_depth` (default: 1), `max_pages` (default: 5), `adaptive` (default: false)
- Returns: JSON with list of page objects (URLs + markdown)

**`crawl_site`**
- Parameters: `seed_url`, `output_dir` (required), filtering options
- Returns: Metadata about completed crawl job (persists to disk)

**`crawl_sitemap`**
- Parameters: `sitemap_url`, `output_dir` (required), filtering options
- Returns: Metadata about completed crawl job

All tools support: URL filtering via regex (`include_patterns`, `exclude_patterns`), browser config overrides, timeout up to 600 seconds, and same-domain constraints.

---

## 4. Integration with Our Architecture

### The Critical Question: StreamableHTTP Transport

Our agents connect to MCP services via `pydantic_ai.mcp.MCPServerStreamableHTTP`, which uses the Streamable HTTP transport (endpoint pattern: `/mcp`). This is the modern MCP transport -- SSE is deprecated.

**What the built-in crawl4ai MCP exposes:**
- SSE at `/mcp/sse` (legacy transport)
- WebSocket at `/mcp/ws`

**What we need:**
- StreamableHTTP at `/mcp` (what `MCPServerStreamableHTTP` connects to)

### Compatibility Assessment

**The built-in crawl4ai MCP does NOT appear to expose a StreamableHTTP `/mcp` endpoint.** It exposes SSE and WebSocket. The SSE transport is deprecated in the MCP spec and `MCPServerStreamableHTTP` does NOT connect to SSE endpoints -- it uses a different wire protocol (Streamable HTTP).

**Pydantic AI options:**
- `MCPServerStreamableHTTP` -- connects to `/mcp` (Streamable HTTP)
- `MCPServerHTTP` -- connects to SSE endpoints (deprecated, removed in newer pydantic-ai)

**This is a blocking incompatibility for Option A (using crawl4ai's built-in MCP directly).** Our agents use `MCPServerStreamableHTTP` exclusively. The built-in crawl4ai MCP serves SSE/WebSocket, not StreamableHTTP.

### Workarounds for Direct MCP Integration

1. **Use pydantic-ai's SSE client** (`MCPServerHTTP`) -- but this is deprecated and may be removed
2. **Use crawl4ai's REST API directly** (skip MCP) -- but this breaks our MCP-everywhere architecture
3. **Use crawl4ai as a library inside our own MCP service** (Option B) -- preserves our architecture perfectly

### REST API Alternative (Non-MCP)

If we bypassed MCP and used the REST API directly, the crawl4ai Docker container exposes:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://crawl4ai:11235/crawl",
        json={
            "urls": ["https://wowpedia.fandom.com/wiki/Elwynn_Forest"],
            "browser_config": {"headless": True, "enable_stealth": True},
            "crawler_config": {"cache_mode": "bypass"}
        }
    )
    result = response.json()
```

This works but breaks the MCP pattern. Not recommended.

---

## 5. Anti-Bot Capabilities

### Browser Engine

Crawl4ai uses **Playwright** with headless Chromium as the default browser. This is fundamentally different from our current trafilatura + httpx approach, which makes bare HTTP requests with no browser at all.

### Stealth Features

**Basic stealth mode** (`enable_stealth=True` in BrowserConfig):
- Modifies browser fingerprints (navigator.webdriver, plugins, etc.)
- Uses playwright-stealth patches
- Good for basic bot detection

**Undetected Browser mode** (for advanced protection):
- Deep-level patches for sophisticated bot detection
- Targets Cloudflare, DataDome, and similar services
- Drop-in replacement with same API
- Slightly slower and higher resource usage
- Requires `headless=False` for best results (harder to detect)

```python
from crawl4ai import UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

adapter = UndetectedAdapter()
strategy = AsyncPlaywrightCrawlerStrategy(
    browser_config=browser_config,
    browser_adapter=adapter
)
```

### Additional Anti-Detection Features

| Feature | Description |
|---------|-------------|
| `user_agent_mode="random"` | Rotates user agents per request |
| `simulate_user=True` | Mimics human interaction patterns |
| Custom cookies | Pre-set cookies for session persistence |
| Proxy support | Full proxy configuration with auth |
| JavaScript execution | Execute JS to interact with pages |
| `scan_full_page=True` | Auto-scroll to trigger lazy loading |
| `remove_overlay_elements=True` | Strip cookie banners and modals |

### Will It Bypass Fandom/Wowhead?

**Probable yes for Fandom** -- Fandom uses basic Cloudflare protection. Playwright with stealth mode should handle this. The headless browser renders JavaScript (required for Fandom's dynamic content) and stealth patches hide bot signatures.

**Uncertain for Wowhead** -- Wowhead uses more aggressive protection. The undetected browser mode may work, but the crawl4ai maintainer acknowledged that anti-bot measures are not guaranteed against all WAF systems. Testing is required.

**vs. Current trafilatura approach**: Our current service uses bare HTTP (httpx) with no browser rendering at all. Fandom and Wowhead serve JavaScript-rendered content behind Cloudflare. httpx cannot execute JavaScript or bypass Cloudflare challenges. Crawl4ai with Playwright is a categorical improvement.

---

## 6. Configuration Options

### BrowserConfig (Global Settings)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `browser_type` | str | "chromium" | chromium, firefox, webkit |
| `headless` | bool | True | False improves stealth but needs display |
| `enable_stealth` | bool | False | Playwright-stealth patches |
| `user_agent` | str | Chrome default | Custom UA string |
| `user_agent_mode` | str | "" | "random" for rotation |
| `viewport_width` | int | 1080 | Browser window width |
| `viewport_height` | int | 600 | Browser window height |
| `proxy_config` | ProxyConfig | None | Proxy server, user, pass |
| `use_persistent_context` | bool | False | Preserve cookies across sessions |
| `javascript_enabled` | bool | True | Disable for static-only crawling |
| `text_mode` | bool | False | Disable images for speed |
| `light_mode` | bool | False | Reduce background features |
| `ignore_https_errors` | bool | False | Accept invalid certs |
| `cookies` | list | [] | Pre-set cookies |
| `extra_args` | list | [] | Additional browser CLI flags |

### CrawlerRunConfig (Per-Crawl Settings)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `cache_mode` | CacheMode | BYPASS | ENABLED, BYPASS, DISABLED |
| `word_count_threshold` | int | 200 | Min words per text block |
| `css_selector` | str | None | Retain only matching sections |
| `excluded_tags` | list | [] | Remove specific HTML tags |
| `wait_until` | str | "domcontentloaded" | networkidle, load, domcontentloaded |
| `page_timeout` | int | 60000 | Page operation timeout (ms) |
| `wait_for` | str | None | CSS/JS wait condition |
| `delay_before_return_html` | float | 0.1 | Extra pause before capture |
| `js_code` | str/list | None | Execute JS after page load |
| `scan_full_page` | bool | False | Auto-scroll for dynamic content |
| `process_iframes` | bool | False | Inline iframe content |
| `remove_overlay_elements` | bool | False | Strip modals/popups |
| `simulate_user` | bool | False | Mimic human interactions |
| `screenshot` | bool | False | Capture base64 screenshot |
| `pdf` | bool | False | Generate PDF output |
| `session_id` | str | None | Reuse browser sessions |
| `exclude_external_links` | bool | False | Remove off-domain links |
| `check_robots_txt` | bool | False | Respect robots.txt |

### Output Formats

- **Markdown**: `result.markdown.raw_markdown` (unfiltered) and `result.markdown.fit_markdown` (filtered)
- **HTML**: `result.html` (original) and `result.cleaned_html` (sanitized)
- **Structured JSON**: Via `extraction_strategy` (CSS-based or LLM-based)
- **Screenshot**: Base64 PNG via `screenshot=True`
- **PDF**: Via `pdf=True`

### Content Filtering Strategies

- **PruningContentFilter**: Removes low-quality content blocks based on threshold (0.0-1.0)
- **BM25ContentFilter**: Relevance-based filtering using BM25 scoring
- **JsonCssExtractionStrategy**: CSS selector-based structured data extraction
- **LLMExtractionStrategy**: LLM-powered extraction using Pydantic schemas (requires API key)

---

## 7. Resource Footprint

### Docker Image Size

The official documentation does not publish exact compressed image sizes. Based on the variant descriptions:

| Variant | Estimated Size | Build Time | Notes |
|---------|---------------|------------|-------|
| default (slim) | ~1.5-2 GB | 6-9 min | Recommended -- includes Chromium |
| all | ~2-3 GB | 8-12 min | Includes torch, transformers |
| GPU | ~3-4 GB | 10-15 min | CUDA support, AMD64 only |

**Why so large**: Includes Playwright + Chromium browser, Python runtime, and all dependencies. This is inherently heavy because it bundles a full browser engine.

### Runtime Memory

| Metric | Value |
|--------|-------|
| Minimum RAM | 2 GB (basic server) |
| Recommended RAM | 4 GB |
| Shared memory | 1 GB (`--shm-size=1g`) |
| Memory limit (compose) | 4 GB |
| Memory reservation (compose) | 1 GB |

### Startup Time

- Container start: 10-40 seconds (includes Chromium browser pool initialization)
- Health check start period: 40 seconds

### Impact on Our Stack

Our current Docker services:

| Service | Approx Memory |
|---------|--------------|
| SurrealDB | ~200-500 MB |
| RabbitMQ | ~100-200 MB |
| MCP Storage | ~100 MB |
| MCP Web Search | ~100 MB |
| MCP Web Crawler (current) | ~100 MB |
| World Lore Researcher | ~200 MB |

**Adding crawl4ai**: +2-4 GB RAM, +1.5-2 GB disk. Total stack memory would go from ~1-1.5 GB to ~3-5 GB. This is significant on a dev machine but manageable with 16+ GB RAM.

**Comparison with current mcp_web_crawler**: Our current service is ~100 MB (Python + trafilatura + httpx, no browser). Crawl4ai is 20-40x heavier because it bundles Chromium. The tradeoff is capability -- browser rendering vs. bare HTTP.

---

## 8. Alternative: Using crawl4ai as a Python Library

### Viability

**Highly viable.** Crawl4ai is available as a pip package (`pip install crawl4ai`) and provides a clean async Python API. We could keep our own `mcp_web_crawler` FastMCP service but replace trafilatura + httpx with crawl4ai's `AsyncWebCrawler`.

### Python Library API

```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Global browser config (once per service lifetime)
browser_config = BrowserConfig(
    headless=True,
    enable_stealth=True,
    user_agent_mode="random",
    text_mode=True,          # skip images for speed
)

# Per-crawl config
run_config = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    word_count_threshold=10,
    page_timeout=60000,
    wait_until="networkidle",
    remove_overlay_elements=True,
    scan_full_page=True,
)

async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(
        url="https://wowpedia.fandom.com/wiki/Elwynn_Forest",
        config=run_config
    )
    if result.success:
        markdown = result.markdown.raw_markdown
        # or filtered: result.markdown.fit_markdown
    else:
        error = result.error_message
```

### Batch Crawling

```python
urls = [
    "https://wowpedia.fandom.com/wiki/Elwynn_Forest",
    "https://wowpedia.fandom.com/wiki/Stormwind_City",
]

async for result in await crawler.arun_many(urls, config=run_config):
    if result.success:
        print(f"Crawled: {result.url}")
```

### What Our Refactored Service Would Look Like

```python
"""Web Crawler MCP Service -- crawl4ai-powered URL extraction for Mythline."""

import os
from mcp.server.fastmcp import FastMCP
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

MCP_WEB_CRAWLER_PORT = int(os.getenv("MCP_WEB_CRAWLER_PORT", "8007"))

server = FastMCP(name="Web Crawler Service", host="0.0.0.0", port=MCP_WEB_CRAWLER_PORT)

browser_config = BrowserConfig(
    headless=True,
    enable_stealth=True,
    user_agent_mode="random",
)

# Module-level crawler instance, managed by lifespan
_crawler: AsyncWebCrawler | None = None

async def get_crawler() -> AsyncWebCrawler:
    global _crawler
    if _crawler is None:
        _crawler = AsyncWebCrawler(config=browser_config)
        await _crawler.start()
    return _crawler

@server.tool()
async def crawl_url(url: str, include_links: bool = True, include_tables: bool = True) -> dict:
    """Fetch a URL and extract its main content as markdown."""
    crawler = await get_crawler()
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        page_timeout=60000,
        wait_until="networkidle",
        remove_overlay_elements=True,
    )
    result = await crawler.arun(url=url, config=run_config)
    if result.success:
        return {
            "url": result.url,
            "title": "",  # extract from markdown or metadata
            "content": result.markdown.raw_markdown,
            "error": None,
        }
    return {
        "url": url,
        "content": None,
        "error": result.error_message,
    }
```

### Dockerfile Changes

The current Dockerfile is tiny (python:3.12-slim + trafilatura). With crawl4ai, we need Playwright and Chromium:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libcups2 libxss1 \
    libxtst6 fonts-liberation libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .
RUN crawl4ai-setup  # installs Playwright browsers

COPY src/ src/

EXPOSE 8007

CMD ["python", "-m", "src.server"]
```

**Image size impact**: ~1.5-2 GB (up from ~200 MB), primarily due to Chromium.

### Setup Requirements

After installing crawl4ai, you must run `crawl4ai-setup` to install Playwright browsers:
```bash
pip install crawl4ai
crawl4ai-setup  # downloads and installs Chromium
```

---

## 9. Comparison: Option A vs Option B

### Option A: Use crawl4ai Docker Image as MCP Service

Replace `mcp_web_crawler` entirely with the `unclecode/crawl4ai` Docker container.

**Pros:**
- Zero custom code to maintain
- Full crawl4ai feature set (screenshots, PDF, JS execution, monitoring dashboard)
- Built-in browser pool management and monitoring
- Pre-built, well-tested Docker image
- Web playground for debugging

**Cons:**
- **Transport mismatch**: Built-in MCP exposes SSE/WebSocket, not StreamableHTTP. Our agents use `MCPServerStreamableHTTP` exclusively. This is a blocking incompatibility.
- Different tool interface (7 generic tools vs. our simple `crawl_url`/`crawl_urls`)
- Heavy resource footprint (4 GB RAM, 2 GB disk)
- Different port scheme (11235 vs. our 8007)
- Would need to change agent MCP config to point to different tools
- Overkill for our use case (we just need URL-to-markdown)

### Option B: Use crawl4ai as a Python Library Inside Our MCP Service

Keep our `mcp_web_crawler` FastMCP service but replace trafilatura + httpx with crawl4ai's `AsyncWebCrawler`.

**Pros:**
- **Preserves our MCP architecture perfectly** -- same StreamableHTTP transport, same `/mcp` endpoint, same tool names
- Zero changes needed in agent code or MCP config
- We control the tool interface (keep `crawl_url`/`crawl_urls` signatures)
- Only the crawler engine changes, not the service boundary
- Can fine-tune BrowserConfig and CrawlerRunConfig for our exact use case
- Can add Fandom/Wowhead-specific configurations
- Shared memory between MCP server and crawler (no network hop to separate container)

**Cons:**
- More custom Dockerfile (need Playwright + Chromium system deps)
- Image grows from ~200 MB to ~1.5-2 GB
- Must manage crawler lifecycle (startup, teardown)
- Browser pool managed by us, not crawl4ai's server

### Option C: Use crawl4ai Docker + REST API (Skip MCP)

Use crawl4ai Docker container but call its REST API directly instead of through MCP.

**Pros:**
- Full crawl4ai features
- No transport mismatch

**Cons:**
- Breaks our MCP-everywhere architecture
- Requires custom HTTP client code in each agent
- Loses tool discovery, schema validation, and other MCP benefits
- Special case in agent code -- every other service is MCP, this one is REST

---

## 10. Recommendation

**Option B: Use crawl4ai as a Python library** is the clear winner.

**Rationale:**

1. **No architecture changes.** Our agents connect to MCP services via `MCPServerStreamableHTTP` pointing to `/mcp` endpoints. Option B preserves this perfectly. Option A has a blocking transport mismatch.

2. **Minimal blast radius.** Only `mcp_web_crawler/src/server.py` and `mcp_web_crawler/Dockerfile` change. No agent code changes. No MCP config changes. No `docker-compose.yml` port changes.

3. **Right-sized.** We need URL-to-markdown extraction with browser rendering. crawl4ai's `AsyncWebCrawler` provides exactly this. The full Docker server (Option A) includes monitoring dashboards, web playgrounds, PDF generation, and other features we do not need.

4. **Anti-bot capability.** We get Playwright + stealth mode + undetected browser -- all the anti-bot features we need -- through the Python library. These features are not exclusive to the Docker server.

5. **Controllable.** We can create Fandom-specific and Wowhead-specific `CrawlerRunConfig` presets with appropriate wait conditions, stealth settings, and timeouts.

### Implementation Plan

1. Add `crawl4ai` to `mcp_web_crawler/pyproject.toml`
2. Update `mcp_web_crawler/Dockerfile` to include Playwright system dependencies and `crawl4ai-setup`
3. Rewrite `mcp_web_crawler/src/server.py` to use `AsyncWebCrawler` instead of trafilatura + httpx
4. Keep the same tool signatures (`crawl_url`, `crawl_urls`) for backward compatibility
5. Add `--shm-size=1g` to docker-compose for the crawler service
6. Test against Fandom and Wowhead URLs

### Required docker-compose.yml Changes

```yaml
mcp-web-crawler:
  build:
    context: ./mcp_web_crawler
  ports:
    - "${MCP_WEB_CRAWLER_PORT:-8007}:8007"
  environment:
    MCP_WEB_CRAWLER_PORT: "8007"
  shm_size: 1g                    # NEW: required for Chromium
  deploy:                         # NEW: memory limits
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 512M
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request,urllib.error;exec('try:\\n urllib.request.urlopen(\"http://localhost:8007/mcp\")\\nexcept urllib.error.HTTPError as e:\\n exit(0 if e.code==406 else 1)')"]
    interval: 15s
    timeout: 10s                  # INCREASED: browser startup is slower
    retries: 3
    start_period: 30s             # INCREASED: Chromium initialization
  restart: unless-stopped
```

---

## Sources

- [Crawl4AI Self-Hosting Documentation](https://docs.crawl4ai.com/core/self-hosting/)
- [Crawl4AI GitHub Repository](https://github.com/unclecode/crawl4ai)
- [Crawl4AI PyPI Package](https://pypi.org/project/Crawl4AI/)
- [Crawl4AI Docker Deployment README](https://github.com/unclecode/crawl4ai/blob/main/deploy/docker/README.md)
- [Crawl4AI Browser/Crawler Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [Crawl4AI Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Crawl4AI AsyncWebCrawler API](https://docs.crawl4ai.com/api/async-webcrawler/)
- [Crawl4AI Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
- [Crawl4AI WAF Bypass Discussion (Issue #136)](https://github.com/unclecode/crawl4ai/issues/136)
- [sadiuysal/crawl4ai-mcp-server](https://github.com/sadiuysal/crawl4ai-mcp-server)
- [sruckh/crawl-mcp](https://github.com/sruckh/crawl-mcp)
- [stgmt/crawl4ai-mcp](https://github.com/stgmt/crawl4ai-mcp)
- [Pydantic AI MCP Client Documentation](https://ai.pydantic.dev/mcp/client/)
- [Docker Hub: unclecode/crawl4ai](https://hub.docker.com/r/unclecode/crawl4ai)
