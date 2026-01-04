# Roleplay Context System

## Overview
Add a Roleplay section to `quest-chain.md` that provides the player's roleplay perspective for each segment of the story. This context flows through all agents, allowing them to weave the player's imagination into the generated narrative.

## Problem
- Quests are the mechanical skeleton, but the real story lives in the player's imagination
- Currently, agents generate narrative around quest data without knowing the player's roleplay intentions
- Missing: character motivation, emotional arc, internal moments between quest markers

## Solution
A `## Roleplay` section in quest-chain.md with segment-keyed freeform notes:

```markdown
## Roleplay

Introduction:
Sitting beside the Moonwell, Fahari's eyes lost in the depth of the ocean.

A.accept:
Fahari looked back at the moonwell when she notices Ranger Glynda.
She is serious, restless. Fahari feels curious.

There's something about Glynda's urgency that reminds her of the last days
before Teldrassil fell. That same desperate energy.

A.exec:
Walking toward Bashal'Aran, memories of Teldrassil flood back.
She sees herself in these trapped spirits.

B.accept:
Meeting Cerellean, she recognizes grief. His loss mirrors her own.
```

### Segment Keys
- `Introduction` - Story introduction
- `Conclusion` - Story conclusion
- `{id}.accept` - Quest acceptance (e.g., `A.accept`, `B.accept`)
- `{id}.exec` - Quest execution (e.g., `A.exec`, `B.exec`)
- `{id}.complete` - Quest completion (e.g., `A.complete`, `B.complete`)

### Format Rules
- Key at start of line followed by colon
- Text continues until next key is found
- Blank lines preserved (supports paragraphs)
- Freeform content - no structure requirements

---

## Implementation

### Phase 1: Parser Update

**File:** `src/libs/parsers/quest_chain_parser.py`

Add `_parse_roleplay_section()` function:
- Find `## Roleplay` section in content
- Parse key-value pairs where keys are segment identifiers
- Support multi-line/paragraph values
- Return dict: `{'Introduction': '...', 'A.accept': '...', ...}`

Update `parse_quest_chain()` to include roleplay in return dict.

### Phase 2: Research Pipeline

**File:** `src/graphs/story_research_graph/models/research_models.py`

Add to `Setting` model:
```python
roleplay: dict[str, str] = {}  # segment_key -> roleplay_text
```

**File:** `src/graphs/story_research_graph/nodes.py`

In `ExtractSetting` node:
- Extract roleplay from parsed quest chain
- Store in setting

### Phase 3: Story Creator Flow

**File:** `src/graphs/story_creator_graph/nodes.py`

In `GetStoryResearch._get_settings_segment()`:
- Include full roleplay dict in segment data

In `GetStoryResearch._get_quest_segment()`:
- Include relevant roleplay entries for quest segments

### Phase 4: Agent Prompts

**File:** `src/agents/story_planner_agent/prompts/system_prompt.md`

Update prompt templates to include roleplay context:

```markdown
## Context
...existing context...

## Roleplay Direction (Player's Vision)
{roleplay_text for this segment}

## Task
...existing task...
```

The roleplay section provides creative direction the agent should weave into:
- Narrator: Internal moments, emotional undertones
- Dialog Creator: How player responds to NPCs
- Execution: Atmosphere colored by character's lens

---

## Files to Modify

1. `src/libs/parsers/quest_chain_parser.py` - Add roleplay parser
2. `src/graphs/story_research_graph/models/research_models.py` - Add roleplay to Setting
3. `src/graphs/story_research_graph/nodes.py` - Extract and store roleplay
4. `src/graphs/story_creator_graph/nodes.py` - Pass roleplay to segments
5. `src/agents/story_planner_agent/prompts/system_prompt.md` - Use roleplay in prompts

---

## Testing

1. Add Roleplay section to `output/test3/quest-chain.md`
2. Re-run research: `python -m src.ui.cli.research_story --subject test3`
3. Verify `research.json` contains roleplay data
4. Re-run story: `python -m src.ui.cli.create_story --subject test3 --regenerate`
5. Verify generated story reflects roleplay context
