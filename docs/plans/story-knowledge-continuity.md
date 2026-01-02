# Story Knowledge Base for Narrative Continuity

## Goal
Enable the story creator to reference past stories, building narrative continuity across sessions by:
1. Indexing completed stories in the knowledge base (chunked by quest)
2. Giving story_planner_agent the ability to search past story events
3. Weaving references and continuity into new stories

## Current State

**Knowledge Base:**
- Chunks markdown by headers (`libs/parsers/markdown_parser.py`)
- Stores in Qdrant vector DB (`libs/knowledge_base/knowledge_vectordb.py`)
- MCP server exposes `search_guide_knowledge` tool

**Story Creator:**
- Graph-based orchestrator (not Pydantic AI agent)
- StoryPlannerAgent already has MCP with knowledge-base server
- Currently only uses KB for player class lookup
- Stores stories as JSON in `output/{subject}/story.json`

## Design Decisions
- **Auto-index**: Stories indexed via dedicated `IndexStoryToKB` node (SOC pattern)
- **Search scope**: Search KB once at story introduction, not every segment
- **Metadata**: Use `story_subject` instead of `source_file` (all stories are story.json)
- **No file detection**: Clear chain from story creator → story indexer (no extension sniffing)

## Implementation Plan

### 1. Create Story Parser
**File:** `src/libs/parsers/story_parser.py`

Chunk stories by quest with rich metadata:
```python
def chunk_story_by_quests(file_path: str) -> list[dict]:
    # Returns chunks with:
    # - text: Full quest narrative (intro + dialogue + execution + completion)
    # - story_subject: "test" (from JSON or derived from path)
    # - story_title: "The Test Chronicles"
    # - quest_title: "The Balance of Nature"
    # - quest_index: 0, 1, 2...
    # - npcs: ["Ilthalaine", "Fahari"]
    # - section_header: "Quest: The Balance of Nature"
```

Export from `__init__.py`.

### 2. Add Story Indexing to Knowledge Base
**File:** `src/libs/knowledge_base/knowledge_vectordb.py`

Add dedicated function for story indexing (no file detection logic):
```python
def index_story(story_path: str, collection_name: str = "stories_knowledge") -> int:
    """Index a single story file into the stories collection."""
    # Uses chunk_story_by_quests parser
    # Stores in dedicated stories_knowledge collection
```

Keep `index_knowledge()` unchanged - it handles markdown guides only.

### 3. Add Story Search Tool to MCP
**File:** `src/mcp_servers/mcp_knowledge_base/server.py`

Add new tool:
```python
@server.tool()
def search_past_story_knowledge(query: str, top_k: int = 3) -> str:
    """Search past stories for events, characters, and continuity."""
    # Search only stories_knowledge collection
    # Return formatted results with story/quest context
```

### 4. Update Story Planner System Prompt
**File:** `src/agents/story_planner_agent/prompts/system_prompt.md`

Add section for **introduction segments only**:
```markdown
## Story Continuity (Introduction Segments Only)

When processing an INTRODUCTION segment, search for past story references:
1. Use `search_past_story_knowledge(zone_name)` to find past events in this area
2. Use `search_past_story_knowledge(player_name)` to find player's history
3. Include relevant past events in the `## Context` section

When past context is found:
- Add a "Previous Events" bullet point in Context
- Reference player's history naturally in the introduction prompt
- Build on established relationships and past accomplishments
```

### 5. Create IndexStoryToKB Node
**File:** `src/graphs/story_creator_graph/nodes.py`

Create new node (maintains SOC):
```python
class IndexStoryToKB(BaseNode):
    """Indexes completed story to knowledge base for future continuity."""

    async def run(self, ctx: GraphRunContext) -> End:
        from src.libs.knowledge_base import index_story
        story_path = f"output/{ctx.state.subject}/story.json"
        index_story(story_path)
        return End()
```

**File:** `src/graphs/story_creator_graph/graph.py`

Add node to graph flow after WriteToFile:
```
WriteToFile → IndexStoryToKB → End
```

### 6. Add CLI Command for Manual Story Indexing
**File:** `src/ui/cli/manage_knowledge_base.py`

Add command:
```bash
python -m src.ui.cli.manage_knowledge_base load-stories
# Indexes all stories from output/*/story.json
```

## Files to Modify

| File | Change |
|------|--------|
| `src/libs/parsers/__init__.py` | Export `chunk_story_by_quests` |
| `src/libs/parsers/story_parser.py` | **NEW** - Story chunking logic |
| `src/libs/knowledge_base/__init__.py` | Export `index_story` |
| `src/libs/knowledge_base/knowledge_vectordb.py` | Add `index_story()` (separate from `index_knowledge`) |
| `src/mcp_servers/mcp_knowledge_base/server.py` | Add `search_past_story_knowledge` tool |
| `src/agents/story_planner_agent/prompts/system_prompt.md` | Add continuity instructions |
| `src/graphs/story_creator_graph/nodes.py` | **NEW** `IndexStoryToKB` node |
| `src/graphs/story_creator_graph/graph.py` | Add `IndexStoryToKB` to flow |
| `src/ui/cli/manage_knowledge_base.py` | Add `load-stories` command |

## Chunk Structure Example

For quest "The Balance of Nature":
```json
{
  "text": "The moonlight braided through Teldrassil's boughs as Fahari stepped into the hush of Shadowglen...[full quest narrative]",
  "story_subject": "test",
  "story_title": "The Test Chronicles",
  "quest_title": "The Balance of Nature",
  "quest_index": 0,
  "npcs": ["Ilthalaine", "Fahari"],
  "section_header": "Quest: The Balance of Nature"
}
```

## Testing

1. Index existing stories: `manage_knowledge_base load-stories`
2. Search: `manage_knowledge_base search "Ilthalaine"`
3. Create new story that references same NPCs/locations
4. Verify continuity references appear in generated content
