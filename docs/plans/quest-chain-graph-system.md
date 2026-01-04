# Quest Chain Graph System

## Overview
Implement a graph-based quest chain system that supports parallel quest pickups, executions, and sequential turn-ins. The system uses Mermaid syntax in `quest-chain.md` to define quest flow.

## Current State
- Quests are processed sequentially in a flat list
- No support for parallel quest execution
- No quest ID linking between research, story, and shots

## Target State
- Quest chain defined as a directed graph in Mermaid
- Quests have unique IDs (A, B, C, D) tracked through the pipeline
- Shot generation respects graph flow, especially for parallel executions

---

## Phase 1: Setup

### 1.1 Copy test subject
- Copy `output/the_rescue` to `output/test3`

### 1.2 Create git flow branch
- Branch name: `feature/quest-chain-graph`

---

## Phase 2: Research Output Modification

### 2.1 Add quest ID to research output
- File: `src/agents/story_research_agent/`
- Modify research output schema to include `id` field per quest
- ID comes from `quest-chain.md` mapping (A, B, C, D)

### 2.2 Parse quest-chain.md for IDs
- Create parser in `src/libs/parsers/quest_chain_parser.py`
- Extract:
  - Quest ID to URL mapping
  - Mermaid graph edges

### 2.3 Setting section in quest-chain.md ✅ NEW
The `quest-chain.md` file now supports a Setting section:

```markdown
## Setting
- Start: Darnassus
- Zone: Darkshore
- Journey: Flight path from Darnassus to Lor'danel

## Quests
- A: https://...
```

| Field | Required | Purpose |
|-------|----------|---------|
| Start | Yes | Where player begins (intro atmosphere) |
| Zone | Yes | Where quests happen (lore context, reduces hallucination) |
| Journey | No | How player travels to first quest (optional hint) |

**Data flow:**
1. Parser extracts Start, Zone, Journey from quest-chain.md
2. Setting extractor uses Zone for lore_context
3. Story intro prompt receives Start + first quest giver location + Journey hint
4. Introduction describes: atmosphere at Start → journey → arrival at first quest

---

## Phase 3: Story Output Modification

### 3.1 Add quest ID to story.json
- File: `src/agents/story_creator_agent/`
- Each quest in `story.json` should have an `id` field matching research

### 3.2 Schema update
```json
{
  "quests": [
    {
      "id": "A",
      "title": "The Final Flame of Bashal'Aran",
      "sections": { ... }
    }
  ]
}
```

---

## Phase 4: Quest Chain Graph Parser

### 4.1 Create Mermaid graph parser
- File: `src/libs/parsers/quest_chain_parser.py`
- Parse the mermaid graph into a traversable structure
- Functions:
  - `parse_quest_chain(file_path)` → returns graph + quest mappings
  - `get_execution_order(graph)` → returns ordered list of segments
  - `find_parallel_nodes(graph, phase)` → returns nodes that can run in parallel

### 4.2 Graph structure
```python
{
  'quests': {
    'A': 'https://...',
    'B': 'https://...'
  },
  'edges': [
    ('Start', 'A.accept'),
    ('A.accept', 'B.accept'),
    ...
  ],
  'nodes': ['Start', 'A.accept', 'A.exec', 'A.complete', ...]
}
```

---

## Phase 5: Shot Generation with Graph Flow

### 5.1 Modify shot creator to use graph
- File: `src/agents/shot_creator_agent/`
- Instead of iterating quests sequentially, follow graph traversal

### 5.2 Handle parallel executions
When multiple `.exec` nodes can run in parallel, determine order by:

**Priority 0: Alphabetical (default)** ✅ IMPLEMENTED
- Sort quest IDs alphabetically (A, B, C, D)
- Predictable, consistent ordering
- Fallback when no other criteria available

**Priority 1: Coordinates (if available)** ⏳ TODO
- If execution has location coordinates from research
- Order by distance from player's current position
- Nearer locations first

**Priority 2: Lore Continuity** ⏳ TODO
- Query knowledge base for connected events
- Group related quests together
- Follow narrative threads

**Priority 3: Same Area Detection** ⏳ TODO
- If executions are in the same area/zone
- Bake them together into a combined narrative segment
- Single execution section covering multiple quest objectives

### 5.3 Execution baking logic
```python
def should_bake_executions(exec_a, exec_b):
    # Same zone/area?
    if get_zone(exec_a) == get_zone(exec_b):
        return True
    # Adjacent coordinates?
    if distance(exec_a.coords, exec_b.coords) < THRESHOLD:
        return True
    return False

def bake_executions(executions):
    # Combine into single narrative segment
    # Mention all quest objectives
    # Return merged execution text
```

---

## Phase 6: Graph Traversal Algorithm

### 6.1 Topological sort with parallel detection
```python
def traverse_quest_graph(graph):
    segments = []
    visited = set()

    # BFS/DFS with level tracking
    # Nodes at same level = parallel
    # Sequential nodes = dependencies

    for node in topological_order(graph):
        parallel_nodes = get_parallel_nodes(graph, node)
        if parallel_nodes:
            segments.append(handle_parallel(parallel_nodes))
        else:
            segments.append(handle_sequential(node))

    return segments
```

### 6.2 Segment types
- `accept`: Introduction + Dialogue (sequential, NPC interaction)
- `exec`: Execution (can be parallel, may be baked)
- `complete`: Completion dialogue (sequential, NPC interaction)

---

## Phase 7: Integration

### 7.1 Update story creator graph
- Modify `src/graphs/story_creator_graph/` to use quest chain parser
- Pass graph structure through the pipeline

### 7.2 Update shot creator
- Accept graph structure as input
- Generate shots following graph traversal order

---

## Testing

### Manual Testing
1. Run story creation for `test3` subject
2. Verify quest IDs propagate through pipeline
3. Check shot order follows graph
4. Verify parallel executions are handled correctly

### Review Points
- Quest IDs in research output
- Quest IDs in story.json
- Shot sequence matches graph flow
- Parallel executions baked or ordered correctly

---

## Files to Modify

1. `src/libs/parsers/quest_chain_parser.py` (NEW)
2. `src/agents/story_research_agent/agent.py`
3. `src/agents/story_creator_agent/agent.py`
4. `src/agents/shot_creator_agent/agent.py`
5. `src/graphs/story_creator_graph/nodes.py`

## Dependencies
- No new external dependencies
- Uses regex for Mermaid parsing
