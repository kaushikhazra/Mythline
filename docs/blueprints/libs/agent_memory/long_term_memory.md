# Library: long_term_memory

Cross-session user preference storage system.

---

## Overview

**Purpose:** Stores user preferences that persist across multiple sessions, enabling personalized agent behavior.

**Location:** `src/libs/agent_memory/long_term_memory.py`

**Storage:** `.mythline/{agent_id}/long_term_memory/memory.json`

**Use when:**
- Tracking user preferences
- Cross-session personalization
- Building user profiles
- Preference-based agent behavior

---

## Import

```python
from src.libs.agent_memory.long_term_memory import (
    save_long_term_memory,
    load_long_term_memory
)
```

---

## Functions

### save_long_term_memory()

Append new preference with timestamp.

```python
def save_long_term_memory(
    agent_id: str,
    preference: str
) -> None
```

**Parameters:**
- `agent_id` - Agent identifier
- `preference` - Preference text to store

**Behavior:** Appends to existing preferences (never overwrites)

**Example:**
```python
save_long_term_memory('story_creator', 'User prefers dark fantasy themes')
save_long_term_memory('story_creator', 'User likes night elf characters')
```

---

### load_long_term_memory()

Load all stored preferences.

```python
def load_long_term_memory(agent_id: str) -> list[dict]
```

**Parameters:**
- `agent_id` - Agent identifier

**Returns:** List of preference dictionaries with timestamps

**Example:**
```python
preferences = load_long_term_memory('story_creator')
# [
#   {'preference': 'User prefers dark fantasy', 'timestamp': '2024-11-13T10:30:00'},
#   {'preference': 'User likes night elves', 'timestamp': '2024-11-13T11:45:00'}
# ]
```

---

## Data Format

**File structure (.json):**
```json
[
  {
    "preference": "User prefers dark fantasy themes with moral ambiguity",
    "timestamp": "2024-11-13T10:30:00.123456"
  },
  {
    "preference": "User enjoys detailed environmental descriptions",
    "timestamp": "2024-11-13T11:45:22.987654"
  }
]
```

**Timestamp format:** ISO 8601 (`datetime.now().isoformat()`)

---

## Usage Pattern

### Saving Preferences (UserPreferenceAgent)

```python
from src.libs.agent_memory.long_term_memory import save_long_term_memory

class UserPreferenceAgent:
    AGENT_ID = "user_preference"

    def run(self, user_feedback: str) -> str:
        # Extract preference from feedback
        preferences = self.extract_preferences(user_feedback)

        # Save each preference
        for pref in preferences:
            save_long_term_memory(self.AGENT_ID, pref)

        return f"Saved {len(preferences)} preferences"
```

### Loading Preferences (StoryCreatorAgent)

```python
from src.libs.agent_memory.long_term_memory import load_long_term_memory

class StoryCreatorAgent:
    AGENT_ID = "story_creator"

    def __init__(self, session_id: str, player_name: str):
        # Load preferences
        preferences = load_long_term_memory(self.AGENT_ID)

        # Format for system prompt
        if preferences:
            pref_text = "\n".join([p["preference"] for p in preferences])
            system_prompt = f"{base_prompt}\n\nUser Preferences:\n{pref_text}"
        else:
            system_prompt = base_prompt

        self.agent = Agent(
            model=os.getenv('LLM_MODEL'),
            system_prompt=system_prompt
        )
```

---

## Configuration

**Storage directory:**
```python
MEMORY_DIR = ".mythline"
```

**Auto-created paths:**
```
.mythline/{agent_id}/long_term_memory/memory.json
```

**Append-only:** New preferences are always added, never removed automatically

---

## Dependencies

**External:**
- `json`
- `pathlib.Path`
- `datetime.datetime`

**Internal:** None

---

## Error Handling

Returns empty list if no preferences stored:

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

**Load preferences on agent initialization:**
```python
def __init__(self, session_id: str):
    preferences = load_long_term_memory(self.AGENT_ID)
    self.preference_text = "\n".join([p["preference"] for p in preferences])
```

**Save extracted preferences:**
```python
extracted_prefs = agent.run("Extract preferences from: " + user_input)
for pref in extracted_prefs:
    save_long_term_memory(self.AGENT_ID, pref)
```

**Format for system prompt:**
```python
preferences = load_long_term_memory(agent_id)
if preferences:
    pref_section = "User Preferences:\n" + "\n".join([
        f"- {p['preference']}" for p in preferences
    ])
```

---

## Examples in Codebase

**Agents using long_term_memory:**
- `src/agents/user_preference_agent/agent.py` - Saves preferences
- `src/agents/story_creator_agent/agent.py` - Loads preferences

**Pattern:**
1. UserPreferenceAgent extracts preferences from user feedback
2. Saves to long_term_memory
3. StoryCreatorAgent loads preferences on initialization
4. Includes preferences in system prompt for personalization

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Related Libraries

- `context_memory` - Session-based conversation history
- `prompt_loader` - System prompt loading

---

## Comparison: Context Memory vs Long-term Memory

| Feature | Context Memory | Long-term Memory |
|---------|----------------|------------------|
| **Scope** | Single session | Cross-session |
| **Data** | Full conversation | User preferences |
| **Format** | ModelMessage objects | Plain text with timestamps |
| **Lifetime** | Session duration | Indefinite |
| **Usage** | Every agent run | Agent initialization |
| **Updates** | After each run | When preferences change |

---

## Troubleshooting

**Issue:** Preferences not loading
- Check agent_id matches between save and load
- Verify `.mythline/` directory exists
- Check file permissions

**Issue:** Duplicate preferences
- Long-term memory is append-only by design
- Implement deduplication in loading code if needed:
```python
preferences = load_long_term_memory(agent_id)
unique_prefs = {p['preference']: p for p in preferences}.values()
```

**Issue:** Old preferences affecting behavior
- Manually edit or delete `.mythline/{agent_id}/long_term_memory/memory.json`
- Consider implementing preference expiration by timestamp
- Add preference priority/weight system

**Issue:** Preferences not being extracted
- Check UserPreferenceAgent system prompt
- Verify extraction logic
- Test with explicit preference statements

---

## Best Practices

1. **Clear preference extraction:** Ensure UserPreferenceAgent extracts specific, actionable preferences
2. **Deduplication:** Consider checking for similar preferences before saving
3. **Preference quality:** Extract only meaningful, persistent preferences
4. **Privacy:** Store only preference statements, not personal information
5. **Manual management:** Provide CLI or UI for viewing/editing preferences
