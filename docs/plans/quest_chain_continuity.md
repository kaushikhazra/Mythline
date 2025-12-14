# Plan: Add Quest Chain Continuity to Story Creator

## Problem
Quests in a chain feel disconnected. Each quest introduction treats the player as arriving fresh, rather than continuing from the previous quest.

**Example from output:**
- Quest 1 completion: *"None of our new initiates are ready..."*
- Quest 2 introduction: *"The moonlight sifted through..."* (no connection)

## Root Cause
The `CreateTODO` node loops through quests with index `i`, but:
- Only passes isolated segment data to the planner
- Planner has zero knowledge of quest position or previous quest
- System prompt has no continuity guidance

## Solution

### File 1: `src/graphs/story_creator_graph/nodes.py`
**Modify `CreateTODO.run()` (around line 175-182)**

Enrich the quest segment with continuity context before passing to planner:

```python
quests = research_data.get('quests', [])
for i, quest in enumerate(quests):
    quest_title = quest.get('title', f'Quest {i+1}')
    quest_segment = self.research_node._get_quest_segment(research_data, i)

    # Add continuity context
    quest_segment['quest_position'] = i + 1
    quest_segment['total_quests'] = len(quests)
    quest_segment['is_first_quest'] = (i == 0)
    quest_segment['is_final_quest'] = (i == len(quests) - 1)

    if i > 0:
        prev_quest = quests[i - 1]
        prev_quest_giver = prev_quest.get('quest_giver', {}).get('name', '')
        current_quest_giver = quest.get('quest_giver', {}).get('name', '')

        quest_segment['previous_quest'] = {
            'title': prev_quest.get('title'),
            'completion_text': prev_quest.get('completion_text', '')[:500]
        }
        quest_segment['same_npc_as_previous'] = (prev_quest_giver == current_quest_giver)

    # Add next quest info for completion hints
    if i < len(quests) - 1:
        next_quest = quests[i + 1]
        quest_segment['next_quest'] = {
            'title': next_quest.get('title'),
            'story_beat': next_quest.get('story_beat', '')[:200]
        }

    quest_todos = await self.planner_agent.run(quest_segment, ctx.state.player)
    todos.extend(quest_todos)
```

### File 2: `src/agents/story_planner_agent/prompts/system_prompt.md`
**Add Quest Continuity section and update templates**

Add new section after "## Segment Types":

```markdown
## Quest Chain Continuity

When processing quest segments, check for continuity context:

### For First Quest (`is_first_quest: true`)
- Player is fresh to this quest chain
- Introduction establishes arrival and first meeting with NPC

### For Continuation Quests (`previous_quest` present)

**If `same_npc_as_previous: true` (returning to same quest giver):**
- Strong continuity - player returns to an NPC they just worked with
- NPC can acknowledge the player's return directly
- Reference the previous task naturally: "Now that the sabers are thinned..."
- Feels like an ongoing working relationship

**If `same_npc_as_previous: false` (new quest giver):**
- Softer transition - player moves to a new encounter
- The journey continues but focus shifts
- Transition through the world: "Having dealt with [previous task], Fahari noticed..."
- New NPC is a fresh meeting, but player carries momentum from their work
- Don't ignore previous quest - it's part of the player's growing story in this area

### Continuity in Quest Introduction Prompts
When `previous_quest` data is available, add to the Context section:
```
- Previous Quest: {previous_quest.title} (just completed)
- Same NPC: {same_npc_as_previous}
- Continuity: Player returns to/continues in the area after completing previous task
```

And instruct narrator:
"Create a transition that flows from the previous quest's completion. The player is not arriving fresh - they've been active in this area."
```

**Update Quest Introduction Prompt Template** to include:

```markdown
### Quest Introduction Prompt Template:
```
## Context
- Quest: {title}
- Story Beat: {story_beat}
- NPC: {quest_giver.name}, {quest_giver.title}
- NPC Location: {quest_giver.location.area_name}, {quest_giver.location.position}
- Landmarks: {quest_giver.location.landmarks}
{IF previous_quest:}
- Previous Quest: {previous_quest.title} (just completed)
- Same NPC: {same_npc_as_previous}
- Continuity: Player continues their journey in the area
{ENDIF}

## Task
Generate introduction narration for quest: {title}

{IF is_first_quest:}
Create atmospheric narration as {player} approaches {quest_giver.name} for the first time.
{ELSE IF same_npc_as_previous:}
Create a continuation as {player} returns to {quest_giver.name} after completing their previous task.
The NPC can acknowledge the player's return. Strong narrative continuity.
{ELSE:}
Create a transition as {player} moves through the area to a new encounter with {quest_giver.name}.
Reference the ongoing journey - softer continuity, fresh meeting but player carries momentum.
{ENDIF}
```
```

**Update Quest Conclusion Prompt Template** to include next quest awareness:

```markdown
### Quest Conclusion Prompt Template:
```
## Context
- Quest: {title}
- Story Beat: {story_beat}
- NPC: {turn_in_npc.name}, {turn_in_npc.title}
- Personality: {turn_in_npc.personality}
- NPC Location: {turn_in_npc.location.position}
{IF next_quest AND NOT is_final_quest:}
- Next Quest: {next_quest.title}
- Chain Position: Quest {quest_position} of {total_quests}
{ENDIF}

## Source Text (stay authentic)
{completion_text}

## Task
Generate quest completion dialogue for: {title}

{IF is_final_quest:}
This is the final quest in the chain. Provide closure while hinting at the broader world.
{ELSE:}
This quest leads into the next task. The NPC's dialogue can naturally hint at what's coming
without explicitly stating it - create narrative momentum toward the next challenge.
{ENDIF}
```
```

## Files to Modify

1. `src/graphs/story_creator_graph/nodes.py`
   - Add `quest_position`, `total_quests`, `is_first_quest`, `is_final_quest` to segment
   - Add `previous_quest` (title + completion_text) when not first quest
   - Add `same_npc_as_previous` flag (true if same quest giver as previous quest)
   - Add `next_quest` (title + story_beat) when not final quest

2. `src/agents/story_planner_agent/prompts/system_prompt.md`
   - Add "Quest Chain Continuity" section explaining how to use the context
   - Update Quest Introduction template to reference previous quest
   - Update Quest Conclusion template to hint at next quest

## Expected Result

**Introduction (before - disconnected):**
> Quest 2 intro: "The moonlight sifted through Teldrassil's silver boughs as Fahari pushed into the clearing..."

**Introduction (after - same NPC, strong continuity):**
> Quest 2 intro: "The balance of the grove felt steadier now, but Ilthalaine's expression had not eased. Fahari approached, the memory of prowling nightsabers still fresh. Something in the Conservator's stance suggested the work was not yet done..."

**Introduction (after - different NPC, softer transition):**
> Quest 3 intro: "Having dealt with the fel moss, Fahari noticed a figure at the western path. Melithar Staghelm stood watchful at the glade's edge, his attention fixed on something beyond the trees..."

**Completion (before - isolated):**
> Quest 1 end: "You performed your duties well, Fahari."

**Completion (after - forward momentum):**
> Quest 1 end: "You performed your duties well, Fahari. The balance holds... for now. But I sense something darker lingers in the west. The grellkin have been restless of late."
