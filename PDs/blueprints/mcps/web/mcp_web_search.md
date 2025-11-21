# MCP Web Search Server Blueprint

This blueprint provides a comprehensive MCP server for web searching using DuckDuckGo and automatic content crawling.

## Overview

The Web Search MCP server provides tools for searching the web and automatically crawling the top results to retrieve their content. It combines DuckDuckGo search with web crawling to return comprehensive information.

## Structure

```
src/mcp_servers/mcp_web_search/
├── __init__.py
└── server.py

start_web_search.bat (at project root)
```

## Implementation

### `server.py`

```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.duck_duck_go import search
from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
server = FastMCP(name="Web Search MCP", port=port)

@server.tool()
async def web_search(query: str) -> str:
    """Searches the web using DuckDuckGo and crawls the top results to fetch their content.

    Args:
        query (str): The search query to look for

    Returns:
        str: Combined content from the top search results
    """
    print(f"Searching for: {query}")

    content = ""
    search_results = search(query)

    for result in search_results:
        page_content = await crawl_content(result['href'])
        content += f"{result['href']}\n\n{page_content[:3000]}\n\n"

    print(content[:300], "...")

    return content

if __name__=='__main__':
    server.run(transport='streamable-http')
```

### `__init__.py`

```python
from .server import server

__all__ = ['server']
```

### `start_web_search.bat` (at project root)

```batch
@echo off
echo Starting Web Search MCP Server...
python -m src.mcp_servers.mcp_web_search.server
```

This file should be placed at the root of the project for easy access.

## Configuration

### Environment Variables

Add to `.env`:

```
MCP_WEB_SEARCH_PORT=8000
```

### Agent Configuration

Add to agent's `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Features

### Automatic Content Crawling

The server automatically:
1. Searches DuckDuckGo for the query
2. Retrieves top search results
3. Crawls each result URL
4. Extracts and combines content
5. Returns comprehensive information

### Content Limiting

- Each page is limited to 3000 characters
- Prevents overwhelming agents with too much data
- Focuses on the most relevant content

### Progress Tracking

- Prints search query for debugging
- Shows preview of retrieved content
- Helps monitor server activity

## Usage in Agents

### Agent Integration

Load the MCP server in the agent's `__init__` method:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

class ResearchAgent:
    AGENT_ID = "research_agent"

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

The `web_search` tool is automatically available to the agent. The agent can call it directly without any wrapper code. Simply instruct the agent in the system prompt that it has access to web search capabilities.

**System Prompt Example:**
```markdown
You have access to the following tools:
- web_search: Searches the web using DuckDuckGo and returns content from top results

Use web_search when you need to find information about topics.
```

The agent will automatically use the tool when needed based on the conversation context.

## Dependencies

### Required Libraries

```python
from src.libs.web.duck_duck_go import search
from src.libs.web.crawl import crawl_content
```

### DuckDuckGo Search

The `search()` function returns a list of results:

```python
[
    {
        'title': 'Page Title',
        'href': 'https://example.com',
        'body': 'Brief description...'
    },
    ...
]
```

### Content Crawling

The `crawl_content()` function:
- Accepts a URL
- Returns markdown-formatted content
- Handles errors gracefully
- Extracts clean text

## Best Practices

### Query Formulation

- Use specific, focused queries
- Avoid overly broad searches
- Include relevant keywords

### Content Processing

```python
for result in search_results:
    page_content = await crawl_content(result['href'])

    content += f"Source: {result['href']}\n"
    content += f"Title: {result['title']}\n"
    content += f"Content: {page_content[:3000]}\n"
    content += "-" * 50 + "\n"
```

### Error Handling

```python
@server.tool()
async def web_search(query: str) -> str:
    """Searches the web with error handling."""
    try:
        print(f"Searching for: {query}")

        content = ""
        search_results = search(query)

        for result in search_results:
            try:
                page_content = await crawl_content(result['href'])
                content += f"{result['href']}\n\n{page_content[:3000]}\n\n"
            except Exception as e:
                print(f"Failed to crawl {result['href']}: {e}")
                continue

        return content if content else "No results found"

    except Exception as e:
        print(f"Search failed: {e}")
        return f"Search error: {str(e)}"
```

### Rate Limiting

Consider adding delays between requests:

```python
import asyncio

for result in search_results:
    page_content = await crawl_content(result['href'])
    content += f"{result['href']}\n\n{page_content[:3000]}\n\n"

    await asyncio.sleep(0.5)
```

## Customization Options

### Adjust Content Length

```python
max_content_length = 5000

page_content = await crawl_content(result['href'])
content += f"{result['href']}\n\n{page_content[:max_content_length]}\n\n"
```

### Filter Results

```python
search_results = search(query)
filtered_results = [r for r in search_results if 'wiki' in r['href']]

for result in filtered_results:
    page_content = await crawl_content(result['href'])
    content += f"{result['href']}\n\n{page_content[:3000]}\n\n"
```

### Add Metadata

```python
content = f"Query: {query}\n"
content += f"Results: {len(search_results)}\n"
content += "=" * 50 + "\n\n"

for i, result in enumerate(search_results, 1):
    page_content = await crawl_content(result['href'])
    content += f"Result {i}:\n"
    content += f"Title: {result['title']}\n"
    content += f"URL: {result['href']}\n"
    content += f"Content: {page_content[:3000]}\n"
    content += "-" * 50 + "\n\n"
```

## Performance Considerations

### Parallel Crawling

```python
import asyncio

async def crawl_result(result):
    page_content = await crawl_content(result['href'])
    return f"{result['href']}\n\n{page_content[:3000]}\n\n"

@server.tool()
async def web_search(query: str) -> str:
    """Searches web with parallel crawling."""
    print(f"Searching for: {query}")

    search_results = search(query)

    tasks = [crawl_result(result) for result in search_results]
    contents = await asyncio.gather(*tasks, return_exceptions=True)

    content = ""
    for item in contents:
        if isinstance(item, str):
            content += item

    return content
```

### Limit Number of Results

```python
max_results = 5

search_results = search(query)[:max_results]

for result in search_results:
    page_content = await crawl_content(result['href'])
    content += f"{result['href']}\n\n{page_content[:3000]}\n\n"
```

## Testing

### Start Server

```bash
python -m src.mcp_servers.mcp_web_search.server
```

Or:

```bash
start_web_search.bat
```

### Test Query

```python
import asyncio
from src.mcp_servers.mcp_web_search.server import web_search

async def test():
    result = await web_search("World of Warcraft lore")
    print(result)

asyncio.run(test())
```

### Verify Agent Integration

Create a test agent that uses the search tool and verify it can:
1. Connect to the MCP server
2. Execute searches
3. Receive combined content
4. Process results effectively

## Common Use Cases

### Lore Research

The agent automatically uses `web_search` when researching topics:

**System Prompt:**
```markdown
When asked to research World of Warcraft lore, use web_search with queries like:
- "World of Warcraft [topic] lore wiki"
```

### Current Events

**System Prompt:**
```markdown
For current events, use web_search with queries like:
- "[topic] news 2025"
```

### Reference Material

**System Prompt:**
```markdown
For reference material, use web_search with queries like:
- "[subject] documentation reference"
```

The agent will automatically formulate appropriate queries and use the web_search tool based on your system prompt instructions.

## Troubleshooting

### No Results Returned

- Check internet connection
- Verify DuckDuckGo is accessible
- Try different query terms

### Crawling Failures

- Some sites block crawlers
- Check URL format
- Verify crawl library is working

### Performance Issues

- Reduce number of results
- Decrease content length limit
- Add parallel crawling
- Implement caching

## Related Blueprints

- `mcp_web_crawler.md` - Single URL crawling
- `mcp_base.md` - Base MCP server structure
