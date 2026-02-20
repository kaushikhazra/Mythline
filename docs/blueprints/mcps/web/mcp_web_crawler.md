# MCP Web Crawler Server Blueprint

This blueprint provides a comprehensive MCP server for crawling and extracting content from individual URLs.

## Overview

The Web Crawler MCP server provides tools for fetching and extracting content from specific URLs. It converts web pages to clean markdown format, making content easy to process and analyze.

## Structure

```
src/mcp_servers/mcp_web_crawler/
├── __init__.py
└── server.py

start_web_crawler.bat (at project root)
```

## Implementation

### `server.py`

```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_CRAWLER_PORT', 8001))
server = FastMCP(name="Web Crawler MCP", port=port)

@server.tool()
async def crawl(url: str) -> str:
    """Crawls content from a given URL and returns it as markdown.

    Args:
        url (str): The URL to crawl content from

    Returns:
        str: The crawled content in markdown format
    """
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    print(f"Crawled {len(content)} characters from {url}")

    return content

if __name__=='__main__':
    server.run(transport='streamable-http')
```

### `__init__.py`

```python
from .server import server

__all__ = ['server']
```

### `start_web_crawler.bat` (at project root)

```batch
@echo off
echo Starting Web Crawler MCP Server...
python -m src.mcp_servers.mcp_web_crawler.server
```

This file should be placed at the root of the project for easy access.

## Configuration

### Environment Variables

Add to `.env`:

```
MCP_WEB_CRAWLER_PORT=8001
```

### Agent Configuration

Add to agent's `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "web-crawler": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

## Features

### Markdown Conversion

The server:
1. Fetches URL content
2. Extracts main content
3. Converts to markdown
4. Removes unnecessary elements
5. Returns clean, formatted text

### Content Statistics

- Tracks content length
- Reports characters crawled
- Provides progress feedback

### Async Processing

- Non-blocking I/O operations
- Efficient for multiple requests
- Handles timeouts gracefully

## Usage in Agents

### Agent Integration

Load the MCP server in the agent's `__init__` method:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

class ContentAgent:
    AGENT_ID = "content_agent"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )
```

### Using the Tool

The `crawl` tool is automatically available to the agent. Instruct the agent about this capability in the system prompt.

**System Prompt Example:**
```markdown
You have access to the following tools:
- crawl: Fetches and extracts content from a URL as markdown

Use crawl when you need to read content from specific web pages.
```

The agent will automatically use the tool when given URLs to fetch.

## Dependencies

### Required Libraries

```python
from src.libs.web.crawl import crawl_content
```

### Crawl Content Function

The `crawl_content()` function:
- Accepts URL string
- Returns markdown string
- Handles HTTP/HTTPS
- Manages errors automatically

## Best Practices

### URL Validation

```python
from urllib.parse import urlparse

@server.tool()
async def crawl(url: str) -> str:
    """Crawls content with URL validation."""
    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return "Error: Invalid URL format"

    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    print(f"Crawled {len(content)} characters from {url}")

    return content
```

### Error Handling

```python
@server.tool()
async def crawl(url: str) -> str:
    """Crawls content with comprehensive error handling."""
    try:
        print(f"Crawling content from: {url}")

        content = await crawl_content(url)

        if not content:
            return "Error: No content retrieved"

        print(f"Crawled {len(content)} characters from {url}")

        return content

    except Exception as e:
        error_msg = f"Failed to crawl {url}: {str(e)}"
        print(error_msg)
        return error_msg
```

### Content Processing

```python
@server.tool()
async def crawl(url: str) -> str:
    """Crawls content with processing."""
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    content = content.strip()

    if len(content) > 50000:
        content = content[:50000] + "\n\n[Content truncated...]"

    print(f"Crawled {len(content)} characters from {url}")

    return content
```

## Customization Options

### Content Length Limiting

```python
@server.tool()
async def crawl(url: str, max_length: int = 10000) -> str:
    """Crawls content with configurable length limit."""
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    if len(content) > max_length:
        content = content[:max_length] + "\n\n[Content truncated]"

    print(f"Crawled {len(content)} characters from {url}")

    return content
```

### Content Filtering

```python
@server.tool()
async def crawl(url: str) -> str:
    """Crawls content with filtering."""
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    lines = content.split('\n')
    filtered_lines = [line for line in lines if len(line.strip()) > 0]
    content = '\n'.join(filtered_lines)

    print(f"Crawled {len(content)} characters from {url}")

    return content
```

### Metadata Extraction

```python
@server.tool()
async def crawl_with_metadata(url: str) -> dict:
    """Crawls content and returns with metadata."""
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    result = {
        "url": url,
        "content": content,
        "length": len(content),
        "word_count": len(content.split()),
        "line_count": len(content.split('\n'))
    }

    print(f"Crawled {len(content)} characters from {url}")

    return result
```

## Advanced Features

### Multiple URL Crawling

```python
@server.tool()
async def crawl_multiple(urls: list[str]) -> dict:
    """Crawls multiple URLs and returns combined content."""
    print(f"Crawling {len(urls)} URLs...")

    results = {}

    for url in urls:
        try:
            content = await crawl_content(url)
            results[url] = content
            print(f"Crawled {len(content)} characters from {url}")
        except Exception as e:
            results[url] = f"Error: {str(e)}"
            print(f"Failed to crawl {url}: {e}")

    return results
```

### Parallel Crawling

```python
import asyncio

@server.tool()
async def crawl_parallel(urls: list[str]) -> dict:
    """Crawls multiple URLs in parallel."""
    print(f"Crawling {len(urls)} URLs in parallel...")

    async def crawl_one(url: str) -> tuple:
        try:
            content = await crawl_content(url)
            return (url, content)
        except Exception as e:
            return (url, f"Error: {str(e)}")

    tasks = [crawl_one(url) for url in urls]
    results = await asyncio.gather(*tasks)

    return dict(results)
```

### Content Summarization

```python
@server.tool()
async def crawl_and_summarize(url: str) -> dict:
    """Crawls content and provides summary statistics."""
    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    summary = {
        "url": url,
        "content": content,
        "characters": len(content),
        "words": len(content.split()),
        "lines": len(content.split('\n')),
        "paragraphs": len([p for p in content.split('\n\n') if p.strip()])
    }

    print(f"Crawled and summarized {url}")

    return summary
```

## Testing

### Start Server

```bash
python -m src.mcp_servers.mcp_web_crawler.server
```

Or:

```bash
start_web_crawler.bat
```

### Test Crawl

```python
import asyncio
from src.mcp_servers.mcp_web_crawler.server import crawl

async def test():
    result = await crawl("https://wowpedia.fandom.com")
    print(result[:500])

asyncio.run(test())
```

### Verify Agent Integration

Create a test agent and verify:
1. Connection to MCP server
2. URL crawling works
3. Markdown conversion is clean
4. Error handling is effective

## Common Use Cases

### Wiki Page Extraction

**System Prompt:**
```markdown
When given a wiki URL, use crawl to extract the page content.
```

### Documentation Fetching

**System Prompt:**
```markdown
For documentation URLs, use crawl to fetch and read the content.
```

### Article Reading

**System Prompt:**
```markdown
When asked to read an article from a URL, use crawl to extract the content.
```

### Reference Gathering

**System Prompt:**
```markdown
When given multiple URLs for reference, use crawl on each URL to gather content.
Format the output with clear source attribution.
```

The agent will automatically use the `crawl` tool based on these instructions.

## Performance Considerations

### Timeout Handling

```python
import asyncio

@server.tool()
async def crawl(url: str, timeout: int = 30) -> str:
    """Crawls content with timeout."""
    print(f"Crawling content from: {url}")

    try:
        content = await asyncio.wait_for(
            crawl_content(url),
            timeout=timeout
        )

        print(f"Crawled {len(content)} characters from {url}")

        return content

    except asyncio.TimeoutError:
        return f"Error: Timeout after {timeout} seconds"
```

### Caching

```python
from functools import lru_cache
import hashlib

cache = {}

@server.tool()
async def crawl(url: str, use_cache: bool = True) -> str:
    """Crawls content with optional caching."""
    if use_cache and url in cache:
        print(f"Returning cached content for: {url}")
        return cache[url]

    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    if use_cache:
        cache[url] = content

    print(f"Crawled {len(content)} characters from {url}")

    return content
```

## Troubleshooting

### Failed to Crawl

- Verify URL is accessible
- Check internet connection
- Ensure site allows crawling
- Try different user agent

### Empty Content

- Site may use JavaScript rendering
- Content might be protected
- Check for CAPTCHA or login requirements

### Encoding Issues

- Verify character encoding
- Check for special characters
- Ensure markdown conversion handles encoding

## Related Blueprints

- `mcp_web_search.md` - Web search with auto-crawling
- `mcp_base.md` - Base MCP server structure
