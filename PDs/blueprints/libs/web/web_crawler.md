# Library: web_crawler

Extract clean markdown content from web pages.

## Overview

**Location:** `src/libs/web/crawl.py`

**Use when:** Extracting web content for research agents, MCP web tools.

## Import

```python
from src.libs.web.crawl import crawl_content
```

## Function

### async crawl_content(url: str) -> str
Crawl web page and return clean markdown.

**Features:**
- Headless Chromium browser
- Removes navigation, ads, links
- Returns cleaned markdown text

**Usage:**
```python
# Async context
content = await crawl_content('https://example.com')

# From sync code
import asyncio
content = asyncio.run(crawl_content('https://example.com'))
```

## Cleaning Features
- Removes markdown links: `[text](url)` → `text`
- Removes bare URLs
- Removes reference-style links
- Cleans extra whitespace
- Excludes: nav, header, footer, aside tags

## Configuration
```python
BrowserConfig:
    browser_type: "chromium"
    headless: True
    text_mode: True
```

## Dependencies
- `crawl4ai` - Web crawling library
- `re` - Regex for cleanup

## Examples in Codebase
- MCP web_crawler server
- MCP web_search server (crawls top results)
