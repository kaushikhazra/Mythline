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
Two different caching strategies based on data type:

1. **NPC Cache** - Store extracted NPC models (final form, ready to use)
   - NPCs are fixed entities with stable attributes
   - Skip search, crawl, AND agent extraction for cached NPCs

2. **Location Cache** - Store raw content + URL (for agent processing)
   - Location data is source material processed differently per context
   - Skip search and crawl, but agent still extracts relevant pieces

## Cache Structure

**Location:** `.mythline/wow_cache/`

```
.mythline/wow_cache/
├── npcs.json        # Extracted NPC models (final form)
└── locations.json   # Raw content + URL (for agent processing)
```

**NPC Cache Entry (extracted model):**
```json
{
  "ilthalaine": { 
    "name": "Ilthalaine",
    "title": "Druid Trainer",
    "personality": "Patient and wise, speaks with calm authority...",
    "lore": "Ilthalaine has trained generations of night elf druids...",
    "location": {
      "area": {"name": "Shadowglen", "x": 58.6, "y": 44.2},
      "position": "Near the moonwell at Aldrassil",
      "visual": "Standing beneath the great tree",
      "landmarks": "Moonwell, Aldrassil tree"
    },
    "cached_at": "2025-01-02T10:30:00Z"
  }
}
```

**Location Cache Entry (raw content):**
```json
{
  "shadowglen": {
    "url": "https://warcraft.wiki.gg/wiki/Shadowglen",
    "content": "# Shadowglen\n\nShadowglen is a subzone of Teldrassil...",
    "cached_at": "2025-01-02T10:30:00Z"
  }
}
```

## Implementation

### 1. Create WoW Cache Module
**File:** `src/libs/cache/wow_cache.py`

```python
from src.graphs.story_research_graph.models.research_models import NPC

def get_npc(name: str) -> NPC | None:
    """Get cached NPC model by name. Returns full NPC or None."""

def set_npc(npc: NPC) -> None:
    """Cache extracted NPC model."""

def get_location(name: str) -> dict | None:
    """Get cached location data by name. Returns {url, content} or None."""

def set_location(name: str, url: str, content: str) -> None:
    """Cache location raw content."""
```

Key normalization: lowercase, strip whitespace.

### 2. Update Research Graph Nodes
**File:** `src/graphs/story_research_graph/nodes.py`

**Modify `ExtractQuestData`:**
```python
# Before searching, check NPC cache
cached_quest_giver = get_npc(extraction.quest_giver_name)
if cached_quest_giver:
    ctx.state._cached_quest_giver = cached_quest_giver
else:
    # Add to list for crawling
    npc_urls.append(search_npc_url(extraction.quest_giver_name))
```

**Modify `CrawlNPCPages`:**
- Skip crawl if NPC already cached (check `ctx.state._cached_quest_giver`)
- Continue to crawl only uncached NPCs

**Modify `EnrichNPCData`:**
- Use cached NPC if available, skip agent extraction
- After agent extraction, save NPC to cache

**Modify `search_location_url()`:**
```python
def search_location_url(location_name: str) -> tuple[str | None, str | None]:
    # Check cache first
    cached = get_location(location_name)
    if cached:
        logger.info(f"Location cache hit: {location_name}")
        return cached['url'], cached['content']

    # Search and return (url, None) - content crawled later
    url = web_search(...)
    return url, None
```

**Modify `CrawlLocationPages`:**
- If content came from cache, skip crawl
- After crawling, save raw content to cache

**Modify `EnrichLocationData`:**
- Agent ALWAYS processes location content (cached or fresh)
- Location context varies per quest

### 3. Add Cache Export
**File:** `src/libs/cache/__init__.py`

```python
from .wow_cache import get_npc, set_npc, get_location, set_location
```

## Flow Change

**NPC Flow (Before):**
```
Quest 1 → Search Ilthalaine → Crawl → Agent Extract → Use
Quest 2 → Search Ilthalaine → Crawl → Agent Extract → Use (redundant!)
```

**NPC Flow (After):**
```
Quest 1 → Cache miss → Search → Crawl → Agent Extract → Cache → Use
Quest 2 → Cache hit → Use directly (skip search, crawl, agent)
```

**Location Flow (Before):**
```
Quest 1 → Search Shadowglen → Crawl → Agent Extract → Use
Quest 2 → Search Shadowglen → Crawl → Agent Extract → Use
```

**Location Flow (After):**
```
Quest 1 → Cache miss → Search → Crawl → Cache content → Agent Extract → Use
Quest 2 → Cache hit → Agent Extract (context-specific) → Use
```

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/libs/cache/__init__.py` | **NEW** - Export cache functions |
| `src/libs/cache/wow_cache.py` | **NEW** - Cache implementation |
| `src/graphs/story_research_graph/nodes.py` | Use cache in extract/crawl/enrich nodes |

## Cache Invalidation

For now: No automatic invalidation. Cache persists indefinitely.

Future options:
- TTL-based expiry (e.g., 30 days)
- Manual clear command
- Version bump invalidation

## Testing

1. Run research on "test" subject - should populate cache
2. Run research again - should see "Cache hit" logs, faster completion
3. Verify `.mythline/wow_cache/npcs.json` contains Ilthalaine, Melithar Staghelm
4. Verify `.mythline/wow_cache/locations.json` contains Shadowglen, Teldrassil
