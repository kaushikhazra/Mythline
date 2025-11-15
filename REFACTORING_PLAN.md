# Story Generation Refactoring Plan

## Context
We're refactoring the story generation system to use a todo-based approach to solve context window overflow issues and provide better incremental progress.

## Problem with Current Approach
- Story creator agent was calling tools iteratively (reading research multiple times, saving multiple times)
- Context window growing uncontrollably → hitting 128K token limits
- No clear progress indication
- All-or-nothing generation (no resume capability)

## New Architecture: Todo-Based Generation

### Flow
```
1. Read research document
2. Plan Agent → Generate list of narration-level todos
3. For each todo (with 3 retry max):
   a. Generate piece (single narration)
   b. Validate piece
   c. If valid: add to story, save JSON
   d. If invalid: retry with feedback
   e. Clear context between todos
4. Return complete validated story
```

### Benefits
- ✅ Controlled context per todo
- ✅ Incremental progress with persistence
- ✅ Resume capability (JSON saved after each)
- ✅ Clear validation per piece
- ✅ Better error handling

## What's Been Completed

### 1. Created Story Planner Agent
**Location:** `src/agents/story_planner_agent/`

**Files:**
- `models/plan_models.py` - StoryTodo and StoryPlan Pydantic models
- `models/__init__.py` - Model exports
- `agent.py` - Stateless planner agent
- `prompts/system_prompt.md` - Planning instructions
- `__init__.py` - Agent export

**StoryTodo Structure:**
```python
class StoryTodo(BaseModel):
    type: Literal["introduction", "quest_introduction", "quest_dialogue",
                  "quest_execution", "quest_completion", "conclusion"]
    quest_title: Optional[str]  # Only for quest-related todos
    description: str  # What to generate
```

**Granularity:** Narration-level (each todo = one narration piece)

### 2. Updated Story Creator Agent Imports
**File:** `src/agents/story_creator_agent/agent.py`

**Added:**
```python
from src.agents.story_planner_agent import StoryPlannerAgent
from src.agents.story_creator_agent.models import Story, Narration, DialogueLine, DialogueLines, Quest, QuestSection
```

**Added to __init__:**
```python
self._planner_agent = StoryPlannerAgent()
```

### 3. Removed Reviewable Base Class
- Deleted `src/agents/reviewer_agent/models/review_models.py`
- Updated all model imports
- Story models now pure Pydantic (no validation decorators)

## What Needs to Be Done

### 1. Refactor `StoryCreatorAgent.run()` Method

**Remove:**
- Current `_generate_story()` - generates entire story at once
- Current `_validate_story()` - validates entire story
- Current retry loop at story level

**Add:**
```python
async def run(self, prompt: str, subject: str) -> Story:
    # 1. Read research
    research_content = read_file(f"output/{subject}/research.md")

    # 2. Generate plan
    plan = await self._planner_agent.run(research_content)

    # 3. Initialize empty story
    story = Story(title="", subject=subject, introduction=None, quests=[], conclusion=None)

    # 4. Execute each todo
    for todo in plan.todos:
        piece = await self._execute_todo(todo, story)
        story = self._add_piece_to_story(story, piece, todo)
        self._save_story_json(story, subject)

    return story
```

### 2. Add Todo Execution Method

```python
async def _execute_todo(self, todo: StoryTodo, current_story: Story):
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        # Clear context to prevent overflow
        self.messages = []

        # Generate piece
        piece = await self._generate_piece(todo, current_story)

        # Validate piece
        validation = await self._validate_piece(piece, todo)

        if validation.valid:
            return piece

        # Retry with feedback
        if attempt < max_retries:
            print(f"Validation failed, retrying ({attempt}/{max_retries})")
            continue

    raise ValueError(f"Failed to generate {todo.type} after {max_retries} attempts")
```

### 3. Add Piece Generation Method

```python
async def _generate_piece(self, todo: StoryTodo, current_story: Story):
    # Build focused prompt based on todo type
    prompt = self._build_todo_prompt(todo, current_story)

    # Generate with agent (agent.output_type needs to be dynamic based on todo type)
    # This might need separate agents or output type switching
    result = await self.agent.run(prompt, message_history=self.messages)

    return result.output
```

### 4. Add Piece Validation Method

```python
async def _validate_piece(self, piece, todo: StoryTodo):
    self._reviewer_agent.messages = []  # Clear reviewer context

    # Build validation prompt based on todo type
    validation_prompt = self._build_validation_prompt(piece, todo)

    result = await self._reviewer_agent.run(validation_prompt)
    return result
```

### 5. Update Story Models for Incremental Building

May need to make fields Optional and add methods to add pieces:
```python
class Story(BaseModel):
    title: str
    subject: str
    introduction: Optional[Narration] = None
    quests: list[Quest] = []
    conclusion: Optional[Narration] = None
```

### 6. Update CLI

**File:** `src/ui/cli/create_story.py`

Update to pass subject separately:
```python
story = await story_creator.run(prompt, subject=args.subject)
```

## Design Decisions

1. **Planner is separate agent** → Reusable for future features
2. **Narration-level granularity** → Fine-grained control, clear validation
3. **Retry at todo level (3x)** → Fail fast, clear error reporting
4. **Context clearing between todos** → Prevent overflow
5. **JSON persistence after each todo** → Resume capability

## Testing Plan

1. Test planner agent generates valid todos from research
2. Test piece-by-piece generation
3. Test validation per piece
4. Test retry logic
5. Test full end-to-end story generation
6. Verify JSON saved incrementally
7. Test context doesn't overflow

## Notes

- Current token usage: ~138K/200K
- GPT-5 model configured in .env
- MCP servers running (ports 8000, 8001, 8002)
- Test research file exists at `output/test/research.md`
