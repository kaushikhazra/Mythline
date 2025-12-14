# Plan: Make Crawler More Robust and Human-Like

## Problem

The current crawler at `src/libs/web/crawl.py` is getting blocked or returning partial content from warcraft.wiki.gg:
- Quest 2 (Fel Moss Corruption): Only 371 characters returned instead of full page
- Quest 3 (Melithar Staghelm): NPC page crawled but extraction returned empty

Root cause: Rapid successive requests without delays trigger anti-bot protection.

## Solution

Enhance the crawler with human-like behavior using Crawl4AI's built-in features.

## Changes

### File: `src/libs/web/crawl.py`

**Current code:**
```python
browser_conf = BrowserConfig(
    browser_type="chromium",
    headless=True,
    text_mode=True
)

config = CrawlerRunConfig(
    markdown_generator=md_generator,
    excluded_tags=["nav", "header", "footer", "aside"]
)
```

**Updated code:**
```python
import random

browser_conf = BrowserConfig(
    browser_type="chromium",
    headless=True,
    text_mode=False,  # Disable text_mode to get full content
    user_agent_mode="random",  # Rotate user agents
    viewport_width=1920,
    viewport_height=1080
)

config = CrawlerRunConfig(
    markdown_generator=md_generator,
    excluded_tags=["nav", "header", "footer", "aside"],
    wait_until="networkidle",  # Wait for all network requests to complete
    delay_before_return_html=random.uniform(1.0, 2.0),  # Random delay 1-2 seconds
    page_timeout=30000,  # 30 second timeout
    simulate_user=True,  # Enable human-like behavior
    scan_full_page=True  # Scroll to load all content
)
```

**Add delay between requests:**
```python
import asyncio

async def crawl_content(url: str, min_delay: float = 1.0, max_delay: float = 3.0) -> str:
    # Random delay before starting (human-like pacing)
    await asyncio.sleep(random.uniform(min_delay, max_delay))

    # ... existing crawl logic with updated config ...
```

### Optional: Add retry logic

```python
async def crawl_content(url: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        await asyncio.sleep(random.uniform(1.0, 3.0))

        content = await _do_crawl(url)

        # Check if we got meaningful content (more than 500 chars)
        if len(content) > 500:
            return content

        if attempt < retries:
            # Longer backoff before retry
            await asyncio.sleep(random.uniform(3.0, 5.0))

    return content  # Return whatever we got
```

## Summary of Changes

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| `text_mode` | `True` | `False` | May strip content |
| `user_agent_mode` | default | `"random"` | Avoid fingerprinting |
| `wait_until` | default | `"networkidle"` | Wait for dynamic content |
| `delay_before_return_html` | none | 1-2s random | Human-like pacing |
| `simulate_user` | none | `True` | Human behavior simulation |
| `scan_full_page` | none | `True` | Load lazy content |
| Pre-request delay | none | 1-3s random | Avoid rapid requests |

## Sources

- [Crawl4AI Browser/Crawler Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [Crawl4AI Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
