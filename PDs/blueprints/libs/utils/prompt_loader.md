# Library: prompt_loader

Load agent system prompts from standard directory structure.

## Overview

**Location:** `src/libs/utils/prompt_loader.py`

**Use when:** Initializing agents, loading system prompts, following standard agent structure.

## Import

```python
from src.libs.utils.prompt_loader import load_system_prompt, load_prompt
```

## Functions

### load_system_prompt(caller_file) -> str
Load system_prompt.md from agent's prompts/ directory.

**Usage:**
```python
# In agent.py
system_prompt = load_system_prompt(__file__)
```

### load_prompt(caller_file, prompt_name: str) -> str
Load named prompt file from agent's prompts/ directory.

**Usage:**
```python
# Load prompts/preference_extraction.md
pref_prompt = load_prompt(__file__, 'preference_extraction')
```

## Expected Structure
```
agent_name/
├── agent.py
└── prompts/
    ├── system_prompt.md
    └── other_prompt.md
```

## Usage Pattern

```python
class MyAgent:
    def __init__(self):
        system_prompt = load_system_prompt(__file__)
        self.agent = Agent(
            model='openai:gpt-4o',
            system_prompt=system_prompt
        )
```

## Examples in Codebase
Every agent uses this in `__init__` method.
