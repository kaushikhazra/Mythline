# Story Quality Fixes Plan

## Issues Identified

From analyzing `output/test/story.json`:

| Issue | Example | Root Cause |
|-------|---------|------------|
| `<class>` token not replaced | "train young <class>s like you" | Token substitution missing in pipeline |
| Actor name inconsistency | "Ilthalaine" vs "Ilthalaine, Conservator" vs "Conservator Ilthalaine" | No format standard enforced |
| Wrong addressee in dialogue | "I'm sorry, Huntress..." | Source text includes out-of-context references |
| Reviewer not catching issues | All above passed review | Reviewer prompt missing specific checks |

## Root Cause Analysis

### 1. `<class>` Token Issue
- WoW quest text contains `<class>` placeholders
- The pipeline replaces `{player}` but not `<class>`
- Player class information exists in research but isn't substituted

### 2. Actor Name Inconsistency
- Dialog creator uses NPC names from prompts
- No consistent format specified (name only vs "Name, Title" vs "Title Name")
- Different quests produce different formats

### 3. Wrong Addressee (Source Text Issue)
- Dialog creator is instructed to "stay close to source text"
- Original WoW quest completion text references NPCs not in the scene
- The agent copies these references verbatim

### 4. Reviewer Gaps
The `story_reviewer_agent` system prompt lacks explicit checks for:
- Unreplaced template tokens
- Actor name format consistency
- Out-of-context character references
- Raw game data (coordinates) in narrative

## Fixes

### Fix 1: Update Reviewer to Catch Template Tokens
**File:** `src/agents/story_reviewer_agent/prompts/system_prompt.md`

Add new issue category and checks:
```markdown
## Critical Checks (Auto-Fail)

Before scoring, scan for these critical issues that ALWAYS fail the segment:

1. **Unreplaced Template Tokens**
   - Look for: `<class>`, `<race>`, `<name>`, `{player}`, or similar template syntax
   - These indicate broken token substitution and MUST be flagged as critical
   - Example: "young <class>s like you" should be "young druids like you"

2. **Raw Game Data in Narrative**
   - Coordinates like "46.0, 73.4" or "at position (x, y)"
   - Item IDs, quest IDs, or numerical references
   - These break immersion and should be flagged as critical

3. **Out-of-Context References**
   - Dialogue addressing characters not present in the scene
   - References to "Huntress", "Commander", etc. when only the player is present
   - Flag as high severity - indicates source text was copied without adaptation
```

### Fix 2: Update Dialog Creator for Actor Name Consistency
**File:** `src/agents/dialog_creator_agent/prompts/system_prompt.md`

Add to Rules section:
```markdown
### Actor Name Format
- Use the NPC's primary name only (e.g., "Ilthalaine", not "Ilthalaine, Conservator")
- Title can be woven into dialogue naturally if needed
- Keep actor names consistent across all dialogue in the story
- The player character uses their name only (e.g., "Fahari")
```

### Fix 3: Update Dialog Creator for Source Text Adaptation
**File:** `src/agents/dialog_creator_agent/prompts/system_prompt.md`

Modify the Source Text instruction:
```markdown
### `## Source Text (stay authentic)` Section
Contains the original quest text from the game. This is the source of truth for dialogue.

**IMPORTANT: Adapt source text to the current scene:**
- Preserve the MEANING and key information from source text
- REMOVE references to characters not present in this scene
- If source text addresses "Huntress", "Commander", etc. and only the player is present, adapt the dialogue to address the player instead
- Stay authentic to the content, but adapt the context to fit the scene
```

### Fix 4: Token Replacement in Pipeline (Future Enhancement)
**Note:** Full `<class>` token replacement requires:
1. Player class being stored in session state
2. Token substitution in `_build_prompt` method

This is a larger change - for now, the reviewer catching it will force regeneration with explicit feedback.

## Files to Modify

1. `src/agents/story_reviewer_agent/prompts/system_prompt.md` - Add critical checks
2. `src/agents/dialog_creator_agent/prompts/system_prompt.md` - Actor name format + source text adaptation

## Implementation Order

1. Update reviewer first (catches issues going forward)
2. Update dialog creator (prevents issues at source)
3. Test with new story generation

## Verification

After fixes, these should be caught/prevented:
- [ ] `<class>` tokens flagged as critical by reviewer
- [ ] Coordinates in narrative flagged by reviewer
- [ ] Actor names use consistent format
- [ ] Source text adapted to scene (no "Huntress" references)
