# Story Segment Restructure Plan

## Problem

The current story.json structure groups sections by quest, making it difficult to:
1. Sequence story segments according to the flow graph
2. Combine parallel execution phases into natural narrative
3. Ensure quest giver locations match the correct phase context

## Current Structure

```json
{
  "quests": [
    {
      "id": "A",
      "sections": {
        "introduction": { "text": "..." },
        "dialogue": { "lines": [...] },
        "execution": { "text": "..." },
        "completion": { "lines": [...] }
      }
    }
  ]
}
```

## Proposed Structure

Flatten segments to match the `execution_order` from research.json:

```json
{
  "title": "The Test3 Chronicles",
  "subject": "test3",
  "introduction": {
    "text": "...",
    "word_count": 133
  },
  "segments": [
    {
      "quest_ids": ["A"],
      "phase": "accept",
      "section": "intro",
      "text": "...",
      "word_count": 104
    },
    {
      "quest_ids": ["A"],
      "phase": "accept",
      "section": "dialogue",
      "lines": [
        { "actor": "Glynda Nal'Shea", "line": "..." },
        { "actor": "Fahari", "line": "..." }
      ]
    },
    {
      "quest_ids": ["B"],
      "phase": "accept",
      "section": "intro",
      "text": "...",
      "word_count": 104
    },
    {
      "quest_ids": ["B"],
      "phase": "accept",
      "section": "dialogue",
      "lines": [...]
    },
    {
      "quest_ids": ["A", "B"],
      "phase": "exec",
      "section": "narration",
      "text": "Combined execution narrative covering both quests...",
      "word_count": 200
    },
    {
      "quest_ids": ["A"],
      "phase": "complete",
      "section": "dialogue",
      "lines": [...]
    },
    {
      "quest_ids": ["B"],
      "phase": "complete",
      "section": "dialogue",
      "lines": [...]
    }
  ],
  "conclusion": {
    "text": "...",
    "word_count": 104
  }
}
```

## Key Design Decisions

### 1. quest_ids as Foreign Keys
- `quest_ids` is a list, not a unique identifier
- References quest IDs from research.json
- Allows multiple quests for parallel execution segments

### 2. Phase and Section Split
| Phase | Sections |
|-------|----------|
| accept | intro, dialogue |
| exec | narration |
| complete | dialogue |

### 3. Roleplay Embedded in Narrative
- Roleplay context from research.json is embedded during story creation
- No separate roleplay field in story.json
- Results in natural-sounding narrative
- Shot creator works with final text directly

### 4. Parallel Execution Combining
- When `execution_order` shows parallel exec phases (e.g., A.exec + B.exec)
- Story creator generates single narration segment
- `quest_ids` contains all parallel quest IDs

## Python Model

```python
from pydantic import BaseModel
from typing import Literal

class DialogueLine(BaseModel):
    actor: str
    line: str

class NarrativeText(BaseModel):
    text: str
    word_count: int

class StorySegment(BaseModel):
    quest_ids: list[str]
    phase: Literal["accept", "exec", "complete"]
    section: Literal["intro", "dialogue", "narration"]
    text: str | None = None
    lines: list[DialogueLine] | None = None
    word_count: int | None = None

class Story(BaseModel):
    title: str
    subject: str
    introduction: NarrativeText
    segments: list[StorySegment]
    conclusion: NarrativeText
```

## Implementation Steps

### Step 1: Update Story Model
- Location: `src/agents/story_creator_agent/models.py` (or create if needed)
- Define new Pydantic models as shown above
- Keep old models temporarily for migration

### Step 2: Update Story Creator Agent
- Location: `src/agents/story_creator_agent/`
- Modify to iterate through `execution_order` from research.json
- For each node in execution_order:
  - Extract quest_ids from node (e.g., "A.accept" -> ["A"])
  - Determine phase (accept/exec/complete)
  - Generate appropriate sections (intro+dialogue for accept, narration for exec, dialogue for complete)
- Detect parallel nodes (`is_parallel: true`) and combine into single segment
- Embed roleplay context into intro/narration text

### Step 3: Update Story Creator Prompts
- Location: `src/agents/story_creator_agent/prompts/`
- Update system prompt to reflect new segment-based generation
- Ensure prompt instructs embedding roleplay naturally

### Step 4: Update Shot Creator Agent
- Location: `src/agents/shot_creator_agent/`
- Modify to read flat segments array
- Handle `quest_ids` as list (for multi-quest segments)
- Iterate segments linearly instead of nested quest structure

### Step 5: Update Shot Creator Prompts
- Location: `src/agents/shot_creator_agent/prompts/`
- Reflect new input structure

### Step 6: Update Any Downstream Consumers
- Video director agent (if it reads story.json directly)
- Any CLI tools that process story.json

### Step 7: Test with Existing Quest Chains
- Run story creation with test3 quest chain
- Verify segments match execution_order
- Verify parallel exec phases are combined
- Verify roleplay context is embedded naturally
- Verify quest giver locations are correct per phase

## Migration Notes

- Old story.json files in output/ will not match new schema
- May need to regenerate stories for existing subjects
- Consider version field if backward compatibility needed

## Benefits

1. **Flow Graph Alignment** - Segments directly match execution_order
2. **Natural Parallel Narrative** - Combined exec phases read better
3. **Correct Location Context** - Each segment knows its phase, pulls correct NPC location
4. **Simpler Downstream Processing** - Linear iteration instead of nested traversal
5. **Embedded Roleplay** - No special handling needed in shot creator
