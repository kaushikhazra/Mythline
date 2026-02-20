# Library: context_memory

Session-based conversation history management for stateful agents.

---

## Overview

**Purpose:** Maintains conversation history across agent runs within a session, enabling coherent multi-turn interactions.

**Location:** `src/libs/agent_memory/context_memory.py`

**Storage:** `.mythline/{agent_id}/context_memory/{session_id}.json`

**Use when:**
- Building stateful agents
- Need conversation continuity
- Multi-turn dialogues
- Agent should remember previous interactions

---

## Import

```python
from src.libs.agent_memory.context_memory import (
    save_context,
    load_context,
    get_latest_session,
    summarize_context
)
```

---

## Functions

### save_context()

Save message history to disk.

```python
def save_context(
    agent_id: str,
    session_id: str,
    messages: list[ModelMessage]
) -> None
```

**Parameters:**
- `agent_id` - Agent identifier (use `AGENT_ID` constant)
- `session_id` - Session identifier
- `messages` - List of Pydantic AI ModelMessage objects

**Example:**
```python
self.messages = agent_output.all_messages()
save_context(self.AGENT_ID, self.session_id, self.messages)
```

---

### load_context()

Load message history from disk.

```python
def load_context(
    agent_id: str,
    session_id: str
) -> list[ModelMessage]
```

**Parameters:**
- `agent_id` - Agent identifier
- `session_id` - Session identifier

**Returns:** List of ModelMessage objects (empty list if file doesn't exist)

**Example:**
```python
self.messages = load_context(self.AGENT_ID, session_id)
```

---

### get_latest_session()

Find most recent session for an agent.

```python
def get_latest_session(agent_id: str) -> str | None
```

**Parameters:**
- `agent_id` - Agent identifier

**Returns:** Latest session ID or None if no sessions exist

**Example:**
```python
if args.resume:
    session_id = get_latest_session(agent_id) or generate_new_session_id()
```

---

### summarize_context()

Summarize conversation history when it gets too long.

```python
async def summarize_context(
    ctx: RunContext[None],
    messages: list[ModelMessage]
) -> list[ModelMessage]
```

**Parameters:**
- `ctx` - Pydantic AI RunContext
- `messages` - Current message list

**Returns:** Summarized message list (first message + summary + last 20 messages)

**Triggers:** Automatically when messages exceed 50

**Example:**
```python
# In agent tool
if len(self.messages) > 50:
    self.messages = await summarize_context(ctx, self.messages)
```

---

## Configuration

**Storage directory:**
```python
CONTEXT_DIR = ".mythline"
```

**Summarization:**
```python
MAX_MESSAGES_BEFORE_SUMMARY = 50
KEEP_RECENT_MESSAGES = 20
SUMMARIZER_AGENT = Agent(os.getenv('LLM_MODEL'))
```

**Auto-created paths:**
```
.mythline/{agent_id}/context_memory/{session_id}.json
```

---

## Usage Pattern

### In Stateful Agent

```python
from src.libs.agent_memory.context_memory import save_context, load_context

class StoryResearcher:
    AGENT_ID = "story_research"

    def __init__(self, session_id: str):
        self.session_id = session_id

        # Load existing context
        self.messages = load_context(self.AGENT_ID, session_id)

        # Initialize agent
        self.agent = Agent(...)

    def run(self, prompt: str):
        # Run with message history
        response = self.agent.run_sync(
            prompt,
            message_history=self.messages
        )

        # Update and save context
        self.messages = response.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)

        return response
```

### With Summarization

```python
@self.agent.tool
async def research_with_summary(ctx: RunContext, query: str) -> str:
    result = perform_research(query)

    # Summarize if conversation gets long
    if len(self.messages) > 50:
        self.messages = await summarize_context(ctx, self.messages)

    return result
```

---

## Data Format

**File structure (.json):**
```json
[
  {
    "kind": "request",
    "parts": [
      {
        "part_kind": "user-prompt",
        "content": "Tell me about Shadowglen"
      }
    ]
  },
  {
    "kind": "response",
    "parts": [
      {
        "part_kind": "text",
        "content": "Shadowglen is the night elf starting zone..."
      }
    ]
  }
]
```

---

## Dependencies

**External:**
- `pydantic_ai.messages.ModelMessage`
- `pydantic_ai.models.openai.OpenAIModel`
- `pydantic_ai.Agent`
- `pydantic_core.to_jsonable_python`
- `pathlib.Path`
- `json`

**Internal:** None

---

## Error Handling

Returns empty list if session file doesn't exist:

```python
if not file_path.exists():
    return []
```

Auto-creates directories when saving:

```python
file_path.parent.mkdir(parents=True, exist_ok=True)
```

---

## Common Patterns

**Load on agent initialization:**
```python
def __init__(self, session_id: str):
    self.messages = load_context(self.AGENT_ID, session_id)
```

**Save after each run:**
```python
self.messages = agent_output.all_messages()
save_context(self.AGENT_ID, self.session_id, self.messages)
```

**Resume latest session:**
```python
session_id = get_latest_session(AGENT_ID) or new_session_id()
```

---

## Examples in Codebase

**Agents using context_memory:**
- `src/agents/story_research_agent/agent.py`
- `src/agents/video_director_agent/agent.py`
- `src/agents/story_creator_agent/agent.py`
- `src/agents/shot_creator_agent/agent.py`
- `src/agents/narrator_agent/agent.py`
- `src/agents/dialog_creator_agent/agent.py`

**CLIs using context_memory:**
- `src/ui/cli/research_story.py` (via agent)
- `src/ui/cli/direct_shots.py` (via agent)

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Related Libraries

- `long_term_memory` - Cross-session preferences
- `argument_parser` - Session ID management in CLIs

---

## Troubleshooting

**Issue:** Context not persisting between runs
- Check session_id is same between runs
- Verify `.mythline/` directory is writable
- Ensure `save_context()` is called after agent run

**Issue:** Agent loses memory mid-conversation
- Verify `message_history` is passed to agent.run()
- Check messages are updated with `all_messages()`
- Ensure not creating new agent instance each run

**Issue:** Summarization not triggering
- Check message count exceeds 50
- Verify `summarize_context()` is called in async context
- Ensure `await` is used when calling

**Issue:** Session file corrupted
- Delete `.mythline/{agent_id}/context_memory/{session_id}.json`
- Start new session
- Check for concurrent writes to same session
