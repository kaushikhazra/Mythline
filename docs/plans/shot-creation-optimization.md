# Shot Creation Optimization Plan

## Problem Statement

The shot creator is **blind to research context**. It receives only:
- `text`, `actor`, `chunk_type`, `reference`

But `research.json` contains rich visual data that should inform shot creation:
- Setting descriptions with visual details
- Quest execution location visuals and landmarks
- NPC personalities (useful for TTS parameters)
- Location-specific atmosphere descriptions

The shot creator currently **invents** backdrops and cinematography from just text content, when all this context already exists.

## Approach: Option A - Load Both Files

Keep `research.json` and `story.json` separate:
- **research.json** = World facts (locations, visuals, NPC personalities)
- **story.json** = Narrative content (what happens)
- **shot creator** = Loads both, combines for cinematography

This maintains separation of concerns and allows visual/NPC data to be reused independently.

## Data Flow Mapping

| Chunk Reference | Research Source |
|-----------------|-----------------|
| Introduction | `setting.description` |
| Quest N - Introduction | `quests[N-1].execution_location.visual` |
| Quest N - Dialogue | `quests[N-1].quest_giver.location.visual` + `personality` |
| Quest N - Execution | `quests[N-1].execution_location.visual` + `landmarks` |
| Quest N - Completion | `quests[N-1].turn_in_npc.location.visual` + `personality` |
| Conclusion | `setting.description` |

## Implementation Steps

### Step 1: Update Chunk Model
Add structured fields for safe lookup (no regex parsing).

**File:** `src/agents/chunker_agent/models/output_models.py`

```python
class Chunk(BaseModel):
    text: str
    actor: str
    chunk_type: str
    reference: str
    quest_index: int | None = None    # Direct index for lookup (0-based)
    section_type: str | None = None   # "introduction", "dialogue", "execution", "completion"
    hint: str = ""                    # Research context for shot creation
```

### Step 2: Update State Model
Add research to session state.

**File:** `src/graphs/shot_creator_graph/models/state_models.py`

```python
from src.graphs.story_research_graph.models.research_models import ResearchBrief

@dataclass
class ShotCreatorSession:
    subject: str
    story: Optional[Story] = None
    research: Optional[ResearchBrief] = None  # NEW
    # ... rest of fields
```

### Step 3: Load Research in Graph
Load `research.json` alongside `story.json`.

**File:** `src/graphs/shot_creator_graph/nodes.py`

In `LoadStory` node:
```python
research_file = f"output/{subject}/research.json"
if file_exists(research_file):
    research_content = read_file(research_file)
    ctx.state.research = ResearchBrief.model_validate_json(research_content)
```

### Step 4: Create Hint Extraction Helper
Add function to extract hints with quest title guardrail (no regex parsing).

**File:** `src/graphs/shot_creator_graph/nodes.py`

```python
def get_hint_for_chunk(research: ResearchBrief, story: Story, chunk: Chunk) -> str:
    if not research:
        return ""

    # Non-quest sections (Introduction/Conclusion)
    if chunk.quest_index is None:
        return research.setting.description

    # Bounds check on both story and research
    if chunk.quest_index >= len(research.quests):
        print(colored(f"[!] Quest index {chunk.quest_index} out of bounds for research", "yellow"))
        return ""

    if chunk.quest_index >= len(story.quests):
        print(colored(f"[!] Quest index {chunk.quest_index} out of bounds for story", "yellow"))
        return ""

    # GUARDRAIL: Verify quest titles match
    story_quest_title = story.quests[chunk.quest_index].title
    research_quest_title = research.quests[chunk.quest_index].title

    if story_quest_title != research_quest_title:
        print(colored(f"[!] Quest mismatch: story='{story_quest_title}' vs research='{research_quest_title}'", "red"))
        return ""

    quest = research.quests[chunk.quest_index]

    if chunk.section_type == "introduction":
        return quest.execution_location.visual
    elif chunk.section_type == "dialogue":
        return f"{quest.quest_giver.location.visual}\nNPC Personality: {quest.quest_giver.personality}"
    elif chunk.section_type == "execution":
        return f"{quest.execution_location.visual}\nLandmarks: {quest.execution_location.landmarks}"
    elif chunk.section_type == "completion":
        return f"{quest.turn_in_npc.location.visual}\nNPC Personality: {quest.turn_in_npc.personality}"

    return ""
```

**Guardrail Benefits:**
- No regex parsing - uses direct index from chunk
- Bounds checking on both story and research arrays
- Quest title verification prevents using wrong quest's hints
- Clear error messages when mismatch detected
- Falls back to empty hint (shot creator invents backdrop) on any failure

### Step 5: Attach Metadata During Chunking
Modify chunking nodes to set quest_index and section_type on chunks.

**File:** `src/graphs/shot_creator_graph/nodes.py`

Each node sets appropriate metadata:

**ProcessIntroduction** (quest_index=None):
```python
result = await self.chunker_agent.run(...)
for chunk in result.output:
    chunk.quest_index = None
    chunk.section_type = None
ctx.state.chunks.extend(result.output)
```

**ProcessQuestIntroduction** (quest_index from state):
```python
result = await self.chunker_agent.run(...)
for chunk in result.output:
    chunk.quest_index = ctx.state.quest_index  # 0-based
    chunk.section_type = "introduction"
ctx.state.chunks.extend(result.output)
```

**ProcessQuestDialogue**:
```python
for chunk in result.output:
    chunk.quest_index = ctx.state.quest_index
    chunk.section_type = "dialogue"
```

**ProcessQuestExecution**:
```python
for chunk in result.output:
    chunk.quest_index = ctx.state.quest_index
    chunk.section_type = "execution"
```

**ProcessQuestCompletion**:
```python
for chunk in result.output:
    chunk.quest_index = ctx.state.quest_index
    chunk.section_type = "completion"
```

**ProcessConclusion** (quest_index=None):
```python
for chunk in result.output:
    chunk.quest_index = None
    chunk.section_type = None
```

### Step 6: Populate Hints in InitializeShotIndex
After all chunks are created, populate hints using the helper function.

**File:** `src/graphs/shot_creator_graph/nodes.py`

In `InitializeShotIndex` node (after saving chunks.json):
```python
# Populate hints for all chunks
if ctx.state.research:
    for chunk in ctx.state.chunks:
        chunk.hint = get_hint_for_chunk(ctx.state.research, ctx.state.story, chunk)
    print(colored(f"[+] Populated hints for {len(ctx.state.chunks)} chunks", "green"))
else:
    print(colored("[!] No research.json found, shots will use generated backdrops", "yellow"))
```

This ensures:
- All metadata (quest_index, section_type) is set before hint lookup
- Single location for hint population (easier to debug)
- Clear feedback when research is missing

### Step 7: Update ShotCreatorAgent
Accept and use the hint parameter.

**File:** `src/agents/shot_creator_agent/agent.py`

```python
async def run(self, text: str, actor: str, chunk_type: str, reference: str, hint: str = "") -> AgentRunResult[Shot]:
    prompt = f"""
text: {text}
actor: {actor}
chunk_type: {chunk_type}
reference: {reference}
hint: {hint}
"""
    agent_output = await self.agent.run(prompt)
    return agent_output
```

### Step 8: Update System Prompt
Guide the agent to use hints.

**File:** `src/agents/shot_creator_agent/prompts/system_prompt.md`

Add to Rules section:
```markdown
### Using Hints
- The `hint` field contains research context about the location and characters
- Use hint descriptions to inform your `backdrop` field - prefer hint visuals over invented descriptions
- Use landmark information from hints for `player_actions` positioning
- Use NPC personality from hints to inform TTS parameters (temperature, exaggeration)
- If hint is empty, use your best judgment based on text content
```

### Step 9: Pass Hint in CreateShot Node
Pass hint from chunk to agent.

**File:** `src/graphs/shot_creator_graph/nodes.py`

```python
result = await self.shot_creator_agent.run(
    text=chunk.text,
    actor=chunk.actor,
    chunk_type=chunk.chunk_type,
    reference=chunk.reference,
    hint=chunk.hint  # NEW
)
```

## Files to Modify

1. `src/agents/chunker_agent/models/output_models.py` - Add quest_index, section_type, hint fields
2. `src/graphs/shot_creator_graph/models/state_models.py` - Add research to state
3. `src/graphs/shot_creator_graph/nodes.py`:
   - Add `get_hint_for_chunk()` helper with quest title guardrail
   - Load research.json in LoadStory node
   - Set quest_index/section_type in each chunking node
   - Populate hints in InitializeShotIndex node
   - Pass hint to agent in CreateShot node
4. `src/agents/shot_creator_agent/agent.py` - Accept hint parameter
5. `src/agents/shot_creator_agent/prompts/system_prompt.md` - Guide hint usage

## Existing Model to Reuse

`ResearchBrief` model already exists at `src/graphs/story_research_graph/models/research_models.py`:
- `ResearchBrief.setting.description` - Setting visual
- `ResearchBrief.quests[].execution_location.visual` - Quest location visuals
- `ResearchBrief.quests[].execution_location.landmarks` - Landmarks
- `ResearchBrief.quests[].quest_giver.personality` - NPC personality
- `ResearchBrief.quests[].quest_giver.location.visual` - NPC location visual

## Expected Benefits

1. **Better backdrops**: Use actual location descriptions instead of inventing them
2. **Consistent visuals**: Same location = same backdrop style across shots
3. **Accurate landmarks**: Player actions can reference actual in-game landmarks
4. **Better TTS parameters**: NPC personality informs emotional delivery
5. **Reduced review failures**: More accurate shots = fewer retries needed
