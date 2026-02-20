# Story Creator Progress Display Refactoring Plan

## Problem Statement
After refactoring the story creator, the progress display stopped working properly. The user wants to:
1. Invoke story creation when pressing the "Create Story" button
2. See what step the agent is currently performing

## Root Cause Analysis

After reviewing the codebase, I found:

1. **CRITICAL BUG: Wrong file extension check** - `src/ui/web/backend/routers/story.py:36`
   - Backend checks for `research.md` but research is saved as `research.json`
   - This causes ALL story creation requests to fail with "Research file not found"
   - **This is why story creation cannot be invoked at all!**

2. **Graph nodes save progress correctly** - `src/graphs/story_creator_graph/nodes.py`
   - `save_progress()` is called at key points (CreateTODO, GetNextTODO)
   - Progress includes: status, message, current, total, details (segment_type, quest_name)

3. **CORS Configuration** - `src/ui/web/backend/main.py:9`
   - Only allows origin `http://localhost:5173`
   - Frontend sometimes runs on port `5174` - should allow both

4. **Frontend progress display is minimal** - `src/ui/web/frontend/src/pages/SimpleStoryCreator.jsx`
   - Only shows "Progress: X / Y" and quest name
   - Doesn't show segment type, sub_type, or visual progress bar
   - Status message shown separately without formatting

## Implementation Plan

### Step 1: Fix Research File Extension (CRITICAL)
**File:** `src/ui/web/backend/routers/story.py`

Change line 36 from:
```python
research_path = f"output/{request.subject}/research.md"
```
To:
```python
research_path = f"output/{request.subject}/research.json"
```

### Step 2: Fix CORS Configuration
**File:** `src/ui/web/backend/main.py`

Update CORS to allow both development ports:
```python
allow_origins=["http://localhost:5173", "http://localhost:5174"]
```

### Step 3: Enhance Progress Display in Frontend
**File:** `src/ui/web/frontend/src/pages/SimpleStoryCreator.jsx`

Add enhanced progress display showing:
- Visual progress bar
- Current step type (e.g., "Introduction", "Quest Dialogue", "Quest Execution")
- Quest name when applicable
- Sub-type information (quest_introduction, quest_dialogue, etc.)
- Better formatted status messages

**Changes:**
1. Add a progress bar component using existing `.progress-bar` CSS classes
2. Show segment type with better labeling:
   - `introduction` → "Introduction"
   - `quest` with `quest_introduction` → "Quest Introduction"
   - `quest` with `quest_dialogue` → "Quest Dialogue"
   - `quest` with `quest_execution` → "Quest Execution"
   - `quest` with `quest_conclusion` → "Quest Completion"
   - `conclusion` → "Conclusion"
3. Display quest name prominently when available
4. Use styled progress container from existing CSS

### Step 4: Add Sub-Type to Progress Details
**File:** `src/graphs/story_creator_graph/nodes.py`

Update `save_progress()` call in `GetNextTODO.run()` to include `sub_type`:
```python
save_progress(
    ctx.state.subject,
    "in_progress",
    f"Processing {current_todo.item.type}{sub_type_info}{quest_info}",
    ctx.state.current_todo_index + 1,
    len(ctx.state.todo_list),
    {
        "segment_type": current_todo.item.type,
        "sub_type": current_todo.item.sub_type,  # Add this
        "quest_name": current_todo.item.quest_name
    }
)
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/ui/web/backend/routers/story.py` | **CRITICAL**: Fix research.md → research.json |
| `src/ui/web/backend/main.py` | Add port 5174 to CORS origins |
| `src/graphs/story_creator_graph/nodes.py` | Add sub_type to progress details |
| `src/ui/web/frontend/src/pages/SimpleStoryCreator.jsx` | Enhance progress display with visual bar and step details |

## Verification

1. Start the backend: `start_web_ui.bat` or `uvicorn src.ui.web.backend.main:app --reload --port 8080`
2. Start the frontend: `cd src/ui/web/frontend && npm run dev`
3. Navigate to "Create Story" tab
4. Select a subject from dropdown
5. Enter player name and click "Create Story"
6. Verify:
   - API call succeeds (no "Research file not found" error)
   - No CORS errors in browser console
   - Progress bar appears and updates
   - Current step type is displayed (e.g., "Processing Introduction")
   - Quest name shown when processing quest segments
   - Sub-type shown (e.g., "Quest Dialogue")
   - Progress completes and shows "Story creation complete!"
