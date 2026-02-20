# Roleplay Context System

## Overview
Add a Roleplay section to `quest-chain.md` that provides the player's roleplay perspective for each segment of the story. This context flows through all agents, allowing them to weave the player's imagination into the generated narrative.

## Problem (Original)
- Quests are the mechanical skeleton, but the real story lives in the player's imagination
- Currently, agents generate narrative around quest data without knowing the player's roleplay intentions
- Missing: character motivation, emotional arc, internal moments between quest markers

## Solution (Phase 1 - Implemented)
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

## Testing (Phase 1)

1. Add Roleplay section to `output/test3/quest-chain.md`
2. Re-run research: `python -m src.ui.cli.research_story --subject test3`
3. Verify `research.json` contains roleplay data
4. Re-run story: `python -m src.ui.cli.create_story --subject test3 --regenerate`
5. Verify generated story reflects roleplay context

---

# Phase 2: Roleplay as Scene Direction (Evolution)

## Problem Discovery

Phase 1 implemented roleplay as **atmospheric coloring** - agents "weave" roleplay into their output. But this creates an immersive disconnect:

### What the User Writes (Scene Direction)
```markdown
A.accept:
Fahari looked back at the moonwell when she notices Ranger Glynda.
She is serious, restless. Fahari feels the tension, and becomes curious.

B.accept:
Fahari was informed by Ranger Glynda, that she should meet Cerellean
Whiteclaw before she goes to Bashal'Aran.

C.accept:
When Fahari was about to leave, she heard a faint voice asking for help.
It was Volkar.
```

This is a **beat sheet** - it describes what happens scene by scene.

### What the System Generates (Atmosphere)
| Segment | User's Vision | Generated Output |
|---------|---------------|------------------|
| A.accept | Notices Glynda while *looking back at moonwell* | Already walking away from moonwell |
| B.accept | *Glynda tells her* to meet Cerellean | Skips that scene, jumps to Cerellean |
| C.accept | *About to leave*, hears voice | Voice treated as memory, not someone calling |

### Root Cause
Current prompt language:
> "Weave the player's roleplay vision into the narration"
> "color the atmosphere, internal state, and emotional undertones"

This treats roleplay as **optional flavor** rather than **mandatory scene beats**.

---

## Solution: Roleplay as Primary Narrative Scaffolding

When roleplay is present for a segment, it becomes the **scene direction** that must be followed. Quest mechanics fill in the details, but roleplay drives the narrative structure.

### Hierarchy Change
**Before (Phase 1):**
```
Quest Mechanics (primary) → Roleplay (color layer)
```

**After (Phase 2):**
```
Roleplay (scene direction) → Quest Mechanics (detail layer)
```

### Key Principles

1. **Roleplay describes WHAT HAPPENS** - not just how things feel
2. **Segments must honor roleplay beats** - if roleplay says "Glynda tells her to meet Cerellean", that scene must happen
3. **Continuity flows through roleplay** - each segment picks up where the previous roleplay left off
4. **Quest mechanics are constraints** - they define what information must be conveyed, but roleplay defines the scene structure

---

## Implementation Changes

### 1. Story Planner Prompt Updates

**File:** `src/agents/story_planner_agent/prompts/system_prompt.md`

#### Change "Roleplay Direction" Section

**Current:**
```markdown
{IF roleplay:}
## Roleplay Direction (Player's Vision)
{roleplay}
{ENDIF}

...

{IF roleplay:}
Weave the player's roleplay vision into the narration. This is how they imagine their character
in this moment—use it to color the atmosphere, internal state, and emotional undertones.
{ENDIF}
```

**Updated:**
```markdown
{IF roleplay:}
## Scene Direction (Required)
The player has provided scene direction that MUST be followed:

{roleplay}

This is not optional flavor—these are the beats that define this scene. Your output must:
1. Include all events/actions described in the scene direction
2. Follow the narrative flow the player envisioned
3. Use quest mechanics to fill in dialogue content and world details
4. Treat the scene direction as your screenplay, quest data as your research
{ENDIF}
```

#### Update Quest Introduction Template

**Add after Context section:**
```markdown
{IF roleplay.accept:}
## Scene Direction (Required)
{roleplay.accept}

Follow this scene direction precisely. If it describes:
- A specific moment (e.g., "looked back at the moonwell") → Include that moment
- An action (e.g., "heard a faint voice") → Show that action happening
- A realization (e.g., "feels the tension") → Build the scene toward that realization

The scene direction is your screenplay. Quest data provides the details to fill in.
{ENDIF}
```

#### Update Quest Dialogue Template

**Add instruction:**
```markdown
{IF roleplay.accept:}
## Scene Direction (Required)
{roleplay.accept}

If the scene direction describes something that should happen IN THIS SCENE (e.g., "Glynda
tells her to meet Cerellean"), that exchange MUST appear in the dialogue. The scene direction
takes priority over condensing dialogue.
{ENDIF}
```

### 2. Add Continuity Bridges

**Problem:** Each segment starts fresh with new scene-setting instead of continuing from the previous moment.

**Solution:** Pass the previous segment's roleplay to the next segment as a continuity anchor.

**File:** `src/graphs/story_creator_graph/nodes.py`

In segment preparation, include:
```python
if previous_segment_roleplay:
    segment_data["previous_scene_ending"] = previous_segment_roleplay
```

**File:** `src/agents/story_planner_agent/prompts/system_prompt.md`

Add to templates:
```markdown
{IF previous_scene_ending:}
## Previous Scene Ended With
{previous_scene_ending}

Continue naturally from this moment. The player's scene direction tells you where they
left off—pick up the thread smoothly.
{ENDIF}
```

### 3. Segment Flow Awareness

Each segment should know:
- What roleplay beat it must hit
- What the previous roleplay beat was (continuity)
- What the next roleplay beat is (foreshadowing opportunity)

**Data structure enhancement:**
```python
segment_data = {
    # existing fields...
    "roleplay": {
        "current": "A.accept roleplay text",
        "previous": "Introduction roleplay text",  # for continuity
        "next": "A.exec roleplay text"  # optional, for subtle setup
    }
}
```

---

## Prompt Template Examples (Updated)

### Quest Introduction with Scene Direction

```markdown
## Context
- Quest: {title}
- NPC: {quest_giver.name}
- Location: {quest_giver.location}

{IF previous_scene_ending:}
## Previous Scene Ended With
{previous_scene_ending}

Continue from this moment—the player's narrative thread must flow unbroken.
{ENDIF}

{IF roleplay.accept:}
## Scene Direction (Required)
{roleplay.accept}

This defines what MUST happen in this scene. Follow it precisely:
- Include all described moments and actions
- Build toward the emotional beats indicated
- Use quest data to fill in specific dialogue and world details
{ENDIF}

## Task
Generate introduction narration for quest: {title}

{IF roleplay.accept:}
The scene direction above is your screenplay. Generate narration that:
1. Picks up from the previous scene (if provided)
2. Includes every beat from the scene direction
3. Flows naturally into the quest dialogue that follows
{ELSE:}
Create atmospheric narration as {player} approaches {quest_giver.name}.
{ENDIF}

## Requirements
- Use third-person perspective with player name "{player}"
- Scene direction beats are MANDATORY, not suggestions
- Target word count: 80-120 words
```

---

## Files to Modify (Phase 2)

1. `src/agents/story_planner_agent/prompts/system_prompt.md`
   - Change "Roleplay Direction" to "Scene Direction (Required)"
   - Add mandatory beat language
   - Add continuity bridge sections

2. `src/graphs/story_creator_graph/nodes.py`
   - Pass previous segment's roleplay for continuity
   - Structure roleplay as current/previous/next

---

## Testing (Phase 2)

Using `output/the_rescue/`:

1. **Beat Compliance Test**
   - Roleplay: "Fahari looked back at the moonwell when she notices Ranger Glynda"
   - Expected: Generated intro includes the moonwell lookback moment
   - Verify: Scene direction beats appear in output

2. **Scene Inclusion Test**
   - Roleplay: "Fahari was informed by Ranger Glynda, that she should meet Cerellean"
   - Expected: This information exchange appears in A.accept or B.accept dialogue
   - Verify: The "informing" scene is not skipped

3. **Continuity Test**
   - Each segment should flow from the previous
   - No jarring scene resets
   - Verify: Reading segments in order feels like continuous narrative

---

## Success Criteria

1. **Roleplay beats are honored** - If user writes "heard a faint voice", that moment appears
2. **Scenes are not skipped** - If roleplay describes an exchange, it happens in the story
3. **Continuity is preserved** - Segments connect smoothly, previous scene's ending leads to next
4. **Quest mechanics remain** - All required quest info is still conveyed, just within the roleplay structure
