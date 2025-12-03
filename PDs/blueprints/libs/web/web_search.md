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

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Examples in Codebase
- MCP web_search server
