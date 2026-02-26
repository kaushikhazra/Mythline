# Tiered Crawl Strategy — Tasks

## 1. Foundation: Config, Model, Dependencies

- [x] Velasari adds `tier: str = Field(default="browser")` to `CrawlResult` in `models.py` — _WC-9, WC-12_
- [x] Velasari adds `get_mediawiki_api(domain)` function to `config.py` using `load_sources_config()` — _WC-13_
- [x] Velasari adds `mediawiki_sites` section to `config/sources.yml` with 3 WoW wiki mappings — _WC-13_
- [x] Velasari adds `markdownify>=0.14,<2` and `readability-lxml>=0.8,<1` to `pyproject.toml` — _WC-10, WC-11_
- [x] Velasari adds tests: `CrawlResult.tier` default/values in `test_models.py`, `get_mediawiki_api()` in `test_config.py` — _WC-9, WC-13_

## 2. Helper Functions

- [x] Velasari implements `_url_to_wiki_title(url)` in `crawler.py` — extracts page title from `/wiki/` paths and `index.php?title=` — _WC-10_
- [x] Velasari implements `_html_to_markdown(html)` in `crawler.py` — markdownify with ATX headings, strips scripts/styles/images — _WC-14_
- [x] Velasari implements `_extract_links_from_html(html, base_url, source_domain)` in `crawler.py` — regex link extraction with domain filtering — _WC-11_
- [x] Velasari adds tests for all three helpers in `test_crawler.py` — _WC-10, WC-11, WC-14_

## 3. Tier 1 — MediaWiki API Crawl

- [x] Velasari implements `crawl_page_api(url, api_url, throttle)` in `crawler.py` — _WC-10_
  - [x] Extracts title via `_url_to_wiki_title()`, calls api.php with `action=parse`
  - [x] Converts HTML to markdown via `_html_to_markdown()`
  - [x] Extracts links from structured API response (ns==0 main namespace)
  - [x] Returns `CrawlResult(tier="api")` on success, `None` on failure
- [x] Velasari adds tests: success, API error, missing page, network error, empty HTML — _WC-10_

## 4. Tier 2 — Plain HTTP Crawl

- [x] Velasari implements `crawl_page_http(url, throttle)` in `crawler.py` — _WC-11_
  - [x] httpx GET with browser-like headers, readability-lxml extraction
  - [x] Markdown conversion via `_html_to_markdown()`
  - [x] Link extraction from raw HTML via `_extract_links_from_html()`
  - [x] Block detection via `detect_blocked_content()`
  - [x] Returns `CrawlResult(tier="http")` on success, `None` on failure
- [x] Velasari adds tests: success, non-200, non-HTML, blocked, empty, network error — _WC-11_

## 5. Dispatcher + Tier 3 Rename

- [x] Velasari renames existing `crawl_page()` to `crawl_page_browser()`, adds `tier="browser"` to all CrawlResult returns — _WC-12_
- [x] Velasari implements new `crawl_page()` dispatcher in `crawler.py` — _WC-9_
  - [x] Checks circuit breaker at entry
  - [x] Routes to Tier 1 if `get_mediawiki_api(domain)` returns a URL
  - [x] Falls through to Tier 2 on Tier 1 failure
  - [x] Falls through to Tier 3 on Tier 2 failure
  - [x] Logs fallback reason at each tier transition
- [x] Velasari updates existing `crawl_page` tests to use `crawl_page_browser` — _WC-12_
- [x] Velasari adds dispatcher tests: tier routing, fallback chain, circuit breaker — _WC-9_
