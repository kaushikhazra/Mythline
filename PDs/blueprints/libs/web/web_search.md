# Library: web_search

DuckDuckGo web search integration.

## Overview

**Location:** `src/libs/web/duck_duck_go.py`

**Use when:** Web search capability for research agents, MCP search tools.

## Import

```python
from src.libs.web.duck_duck_go import search
```

## Function

### search(query: str) -> list
Search DuckDuckGo and return top 5 results.

**Returns:**
```python
[
    {
        'href': 'https://...',
        'title': 'Page title',
        'body': 'Snippet text...'
    },
    ...
]
```

**Usage:**
```python
results = search('Shadowglen night elf starting zone')

for result in results:
    url = result['href']
    title = result['title']
    snippet = result['body']
```

## Configuration
- Max 5 results (hardcoded)

## Dependencies
- `ddgs` - DuckDuckGo Search library

## Examples in Codebase
- MCP web_search server
