# WoW Data Cache for Research Optimization

## Goal
Cache NPC and location data persistently to avoid redundant web searches and crawls across research sessions.

## Problem
Currently, each quest in a research session triggers:
1. DuckDuckGo search for NPC name → URL
2. DuckDuckGo search for location name → URL
3. Playwright crawl for each URL (already cached in-session)

For a 3-quest chain with the same NPC (e.g., Ilthalaine), we search 3 times instead of 1.
Across sessions, we re-crawl the same NPCs and locations repeatedly.

## Solution
Persistent JSON cache that stores:
- `npc_name → {url, content, timestamp}`
- `location_name → {url, content, timestamp}`

Skip both search AND crawl for cached entities.

## Cache Structure

**Location:** `.mythline/wow_cache/`

```
.mythline/wow_cache/
├── npcs.json
└── locations.json
```

**NPC Cache Entry:**
```json
{
  "ilthalaine": {
    "url": "https://warcraft.wiki.gg/wiki/Ilthalaine",
    "content": "# Ilthalaine\n\nIlthalaine is a night elf...",
    "cached_at": "2025-01-02T10:30:00Z"
  }
}
```

**Location Cache Entry:**
```json
{
  "shadowglen": {
    "url": "https://warcraft.wiki.gg/wiki/Shadowglen",
    "content": "# Shadowglen\n\nShadowglen is a subzone...",
    "cached_at": "2025-01-02T10:30:00Z"
  }
}
```

## Implementation

### 1. Create WoW Cache Module
**File:** `src/libs/cache/wow_cache.py`

```python
def get_npc(name: str) -> dict | None:
    """Get cached NPC data by name. Returns {url, content} or None."""

def set_npc(name: str, url: str, content: str) -> None:
    """Cache NPC data."""

def get_location(name: str) -> dict | None:
    """Get cached location data by name. Returns {url, content} or None."""

def set_location(name: str, url: str, content: str) -> None:
    """Cache location data."""
```

Key normalization: lowercase, strip whitespace.

### 2. Update Research Graph Nodes
**File:** `src/graphs/story_research_graph/nodes.py`

**Modify `search_npc_url()`:**
```python
def search_npc_url(npc_name: str) -> tuple[str | None, str | None]:
    # Check cache first
    cached = get_npc(npc_name)
    if cached:
        logger.info(f"Cache hit: {npc_name}")
        return cached['url'], cached['content']

    # Search and return (url, None) - content crawled later
    url = web_search(...)
    return url, None
```

**Modify `search_location_url()`:**
```python
def search_location_url(location_name: str) -> tuple[str | None, str | None]:
    # Check cache first
    cached = get_location(location_name)
    if cached:
        logger.info(f"Cache hit: {location_name}")
        return cached['url'], cached['content']

    # Search and return (url, None)
    url = web_search(...)
    return url, None
```

**Modify `CrawlNPCPages`:**
- If content came from cache, skip crawl
- After crawling, save to cache

**Modify `CrawlLocationPages`:**
- If content came from cache, skip crawl
- After crawling, save to cache

### 3. Add Cache Export
**File:** `src/libs/cache/__init__.py`

```python
from .wow_cache import get_npc, set_npc, get_location, set_location
```

## State Changes

Add to `ResearchSession`:
```python
# Track which entities came from cache (no need to re-cache)
cached_npcs: set[str] = field(default_factory=set)
cached_locations: set[str] = field(default_factory=set)
```

## Flow Change

**Before:**
```
Quest → Search NPC → Search Location → Crawl NPC → Crawl Location
Quest → Search NPC → Search Location → Crawl NPC → Crawl Location  (same NPC!)
```

**After:**
```
Quest → Check Cache → Miss → Search → Crawl → Save to Cache
Quest → Check Cache → Hit → Skip search & crawl
```

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/libs/cache/__init__.py` | **NEW** - Export cache functions |
| `src/libs/cache/wow_cache.py` | **NEW** - Cache implementation |
| `src/graphs/story_research_graph/nodes.py` | Use cache in search/crawl functions |
| `src/graphs/story_research_graph/models/state_models.py` | Add cached entity tracking |

## Cache Invalidation

For now: No automatic invalidation. Cache persists indefinitely.

Future options:
- TTL-based expiry (e.g., 30 days)
- Manual clear command
- Version bump invalidation

## Testing

1. Run research on "test" subject - should populate cache
2. Run research again - should see "Cache hit" logs
3. Verify `.mythline/wow_cache/npcs.json` contains Ilthalaine, Melithar Staghelm
4. Verify `.mythline/wow_cache/locations.json` contains Shadowglen, Teldrassil
