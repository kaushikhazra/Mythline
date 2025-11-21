# Stateful Sub-Agent Blueprint

**Purpose:** Executable specification for building stateful agents that maintain conversation context for coherent multi-turn interactions.

**For:** AI assistants generating code, developers creating conversational agents

---

## Overview

Stateful sub-agents maintain conversation history via context memory, enabling coherent multi-turn conversations without MCP servers.

**Characteristics:**
- Maintain conversation history via context memory
- Generate coherent output across multiple interactions
- Have focused, single-purpose responsibilities
- Can use structured output with Pydantic models
- Are called by orchestrator agents or used in graphs
- No MCP servers (lightweight and fast)

**When to use this pattern:**
- Multi-turn conversations needed
- Context matters for output quality
- Building on previous responses
- Maintaining coherence across calls
- Agent needs to remember conversation

---

## Default Implementation Pattern

**Unless the user specifies otherwise, implement stateful sub-agents EXACTLY as follows:**

### Directory Structure

```
src/agents/{agent_name}/
├── __init__.py                   # Export agent class
├── agent.py                      # Agent implementation
├── prompts/
│   └── system_prompt.md          # System prompt
└── models/                       # OPTIONAL: Only if using structured output
    └── output_models.py
```

### Code Templates

#### File: `__init__.py`

```python
from .agent import {AgentClassName}

__all__ = ['{AgentClassName}']
```

**Rules:**
- Import agent class from `.agent`
- Use agent class name (PascalCase)
- Export in `__all__`

#### File: `agent.py` (Basic Pattern)

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import save_context, load_context

load_dotenv()

class {AgentClassName}:
    AGENT_ID = "{agent_id}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```

#### File: `agent.py` (With Structured Output)

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import save_context, load_context
from src.agents.{agent_name}.models.output_models import {OutputModel}

load_dotenv()

class {AgentClassName}:
    AGENT_ID = "{agent_id}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            output_type={OutputModel},
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[{OutputModel}]:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```

#### File: `prompts/system_prompt.md`

```markdown
# Persona

You are [role and expertise description].

# Task

Your task is to [clear task description].

# Instructions

1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [etc.]

# Constraints

- [Constraint 1]
- [Constraint 2]
- [etc.]

# Output

Return [output description with format].
```

#### File: `models/output_models.py` (Optional)

```python
from pydantic import BaseModel, Field

class {OutputModel}(BaseModel):
    """Description of what this output represents."""
    field1: str = Field(description="Description of field1")
    field2: int = Field(description="Description of field2")
    # Add more fields as needed
```

---

## Implementation Rules

### MUST Follow (Non-Negotiable)

✓ **Import order:**
1. Standard library (`import os`)
2. Third-party (`from dotenv import load_dotenv`)
3. Pydantic AI (`from pydantic_ai import Agent`)
4. Context memory (`from src.libs.agent_memory.context_memory import ...`)
5. Other local imports (`from src.agents...`)

✓ **Environment loading:**
- Load dotenv at **module level** (after imports, before class)
- Use `load_dotenv()` once
- NOT inside `__init__` or methods

✓ **LLM model configuration:**
- Use `os.getenv('LLM_MODEL')` directly
- Model is already in OpenRouter format (e.g., `openai/gpt-4o-mini`)
- NO string formatting like `f"openai:{...}"`

✓ **Agent ID:**
- AGENT_ID must match directory name
- Format: `lowercase_with_underscores`
- Must be a class constant

✓ **Class name:**
- PascalCase
- Descriptive of function
- Ends with "Agent" (e.g., `NarratorAgent`)

✓ **Session ID parameter:**
- `__init__(self, session_id: str)` MUST have session_id
- Store as `self.session_id`
- Required for context memory

✓ **Context memory:**
- Load context in `__init__`: `self.messages = load_context(self.AGENT_ID, session_id)`
- Pass to agent run: `agent_output = await self.agent.run(prompt, message_history=self.messages)`
- Update messages: `self.messages = agent_output.all_messages()`
- Save after run: `save_context(self.AGENT_ID, self.session_id, self.messages)`

✓ **Async run method:**
- MUST be `async def run(...)`
- Return type MUST be `AgentRunResult` or `AgentRunResult[OutputModel]`
- No sync version needed

✓ **Prompt loading:**
- Use `load_system_prompt(__file__)`
- Prompt file MUST be `prompts/system_prompt.md`
- Use `__file__` (not hardcoded path)

✓ **Memory persistence:**
- ALWAYS call `save_context()` after agent run
- ALWAYS update `self.messages` before saving
- Load context ONCE in `__init__`, not in `run()`

### SHOULD Follow (Best Practices)

- Keep agents focused on single responsibility
- Use structured output for complex responses
- Add type hints to all methods
- Include docstrings in class and methods
- Share session_id across related agents
- Handle errors gracefully

---

## Anti-Patterns (DO NOT)

### ❌ Wrong LLM Model Format

```python
# WRONG - Don't add "openai:" prefix
llm_model = f"openai:{os.getenv('LLM_MODEL')}"

# RIGHT - Use directly (already has provider prefix)
llm_model = os.getenv('LLM_MODEL')
```

### ❌ Loading Environment Inside __init__

```python
# WRONG - Don't load inside __init__
class MyAgent:
    def __init__(self, session_id: str):
        load_dotenv()  # Don't do this
        llm_model = os.getenv('LLM_MODEL')

# RIGHT - Load at module level
load_dotenv()  # Do this once at top

class MyAgent:
    def __init__(self, session_id: str):
        llm_model = os.getenv('LLM_MODEL')
```

### ❌ Sync run() Method

```python
# WRONG - Don't use sync
def run(self, prompt: str):
    return self.agent.run_sync(prompt, message_history=self.messages)

# RIGHT - Must be async
async def run(self, prompt: str):
    return await self.agent.run(prompt, message_history=self.messages)
```

### ❌ Missing session_id Parameter

```python
# WRONG - Stateful agents NEED session_id
class MyAgent:
    def __init__(self):  # Missing session_id!
        ...

# RIGHT - session_id required
class MyAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
```

### ❌ Not Loading Context Memory

```python
# WRONG - Missing context memory
class MyAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
        # Missing: self.messages = load_context(...)
        self.agent = Agent(...)

# RIGHT - Load context in __init__
class MyAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = load_context(self.AGENT_ID, session_id)
        self.agent = Agent(...)
```

### ❌ Not Passing Message History

```python
# WRONG - Not passing message history
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt)  # Missing message_history!
    return agent_output

# RIGHT - Pass message history
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

### ❌ Not Saving Context

```python
# WRONG - Not saving context after run
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    return agent_output  # Forgot to save!

# RIGHT - Always save context
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

### ❌ Loading Context on Every Run

```python
# WRONG - Don't load context in run() method
async def run(self, prompt: str):
    messages = load_context(self.AGENT_ID, self.session_id)  # Don't do this!
    agent_output = await self.agent.run(prompt, message_history=messages)
    ...

# RIGHT - Load once in __init__
def __init__(self, session_id: str):
    self.messages = load_context(self.AGENT_ID, session_id)  # Load once here

async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    ...
```

### ❌ Hardcoded Model Names

```python
# WRONG - Don't hardcode model names
llm_model = "openai/gpt-4o"

# RIGHT - Use environment variable
llm_model = os.getenv('LLM_MODEL')
```

---

## Code Generation Guide (For AI Assistants)

**When user requests a stateful agent, follow these steps:**

### Step 1: Parse Requirements

Extract from user request:
- **Agent name** (e.g., "narrator")
- **Purpose** (e.g., "create narrative text")
- **Input type** (e.g., "story context")
- **Output type** (e.g., "narrative text" or structured model)
- **Why stateful** (e.g., "needs to maintain writing style", "builds on previous narration")

### Step 2: Generate Names

```python
agent_name = "{user_provided_name}"  # lowercase_with_underscores
                                      # e.g., "narrator_agent"

agent_class = "{AgentClassName}"     # PascalCase
                                      # e.g., "NarratorAgent"

agent_id = "{agent_name}"            # same as directory name
                                      # e.g., "narrator"
```

### Step 3: Create Directory Structure

```bash
mkdir -p src/agents/{agent_name}/prompts
# If structured output needed:
mkdir -p src/agents/{agent_name}/models
```

### Step 4: Generate Files

Use templates above, substituting:
- `{agent_name}` → e.g., `narrator_agent`
- `{AgentClassName}` → e.g., `NarratorAgent`
- `{agent_id}` → e.g., `narrator`
- `{OutputModel}` → e.g., `Narration` (if structured output)

### Step 5: Write System Prompt

Based on user requirements, create `prompts/system_prompt.md`:
- Define persona matching agent purpose
- Clear task description
- Step-by-step instructions
- Constraints and guidelines
- Output format specification

### Step 6: Create Output Model (If Needed)

If user wants structured output:
- Create `models/output_models.py`
- Define Pydantic model with fields
- Add Field descriptions
- Update agent.py to use `output_type`

### Step 7: Validation

Before presenting code, verify:
- [ ] All imports in correct order (including context_memory)
- [ ] `load_dotenv()` at module level
- [ ] `os.getenv('LLM_MODEL')` used correctly (no extra formatting)
- [ ] AGENT_ID matches directory name
- [ ] Class name is PascalCase
- [ ] `__init__(self, session_id: str)` has session_id parameter
- [ ] Context loaded in `__init__`: `self.messages = load_context(...)`
- [ ] run() method is async
- [ ] run() passes `message_history=self.messages`
- [ ] run() updates `self.messages = agent_output.all_messages()`
- [ ] run() saves context: `save_context(...)`
- [ ] Prompt loaded with `__file__`

---

## Validation Checklist

**IMPORTANT:** Before validating, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

**Before considering code complete, verify ALL of these:**

### File Structure
- [ ] Directory: `src/agents/{agent_name}/`
- [ ] File: `__init__.py` exists and exports class
- [ ] File: `agent.py` exists with agent implementation
- [ ] File: `prompts/system_prompt.md` exists
- [ ] File: `models/output_models.py` exists (if structured output)

### Code Quality
- [ ] All imports in correct order (stdlib, third-party, pydantic_ai, context_memory, local)
- [ ] `load_dotenv()` called once at module level
- [ ] `os.getenv('LLM_MODEL')` used directly (no f-string wrapping)
- [ ] AGENT_ID is lowercase_with_underscores
- [ ] AGENT_ID matches directory name
- [ ] Class name is PascalCase ending in "Agent"
- [ ] `__init__(self, session_id: str)` HAS session_id parameter
- [ ] `self.session_id = session_id` stored as instance variable
- [ ] `run()` method is `async def`
- [ ] Return type is `AgentRunResult` or `AgentRunResult[Model]`
- [ ] `load_system_prompt(__file__)` used (not hardcoded path)

### Context Memory (Critical)
- [ ] Context memory imported: `from src.libs.agent_memory.context_memory import save_context, load_context`
- [ ] Context loaded in `__init__`: `self.messages = load_context(self.AGENT_ID, session_id)`
- [ ] Agent run receives message history: `agent_output = await self.agent.run(prompt, message_history=self.messages)`
- [ ] Messages updated after run: `self.messages = agent_output.all_messages()`
- [ ] Context saved after run: `save_context(self.AGENT_ID, self.session_id, self.messages)`
- [ ] Context memory loaded ONCE in __init__, NOT in run()

### Prompt Quality
- [ ] System prompt has all required sections (Persona, Task, Instructions, Constraints, Output)
- [ ] Instructions are clear and actionable
- [ ] Output format is specified
- [ ] Persona matches agent purpose

### Structured Output (if applicable)
- [ ] Pydantic model in `models/output_models.py`
- [ ] All fields have Field descriptions
- [ ] Model imported in agent.py
- [ ] `output_type={Model}` in Agent constructor
- [ ] Return type is `AgentRunResult[Model]`

### Testing
- [ ] Agent can be imported: `from src.agents.{agent_name} import {ClassName}`
- [ ] Agent can be instantiated: `agent = {ClassName}(session_id="test")`
- [ ] Agent can run: `result = await agent.run("test input")`
- [ ] Context persists across runs with same session_id

---

## Real-World Example: Narrator Agent

**Purpose:** Creates narrative text for story sections with consistent tone

**File:** `src/agents/narrator_agent/agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import save_context, load_context
from src.agents.story_creator_agent.models.story_models import Narration

load_dotenv()

class NarratorAgent:
    AGENT_ID = "narrator"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            output_type=Narration,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[Narration]:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```

**System Prompt:** `prompts/system_prompt.md`

```markdown
# Persona

You are a professional narrative writer specializing in World of Warcraft lore.

# Task

Create immersive, atmospheric narrative text that brings WoW locations and events to life.

# Instructions

1. Use vivid, sensory descriptions
2. Maintain consistency with WoW lore
3. Match the tone and style of the story
4. Keep narration concise but impactful
5. Focus on atmosphere and emotion

# Constraints

- Stay within specified word count
- Use present tense for immediacy
- Avoid breaking the fourth wall
- Maintain narrative flow

# Output

Return structured narration with text, word count, and tone.
```

---

## Usage Patterns

### Direct Usage

```python
from src.agents.narrator_agent import NarratorAgent

# Create agent for a session
narrator = NarratorAgent(session_id="story_session_123")

# First call
result1 = await narrator.run("Create narration for entering Shadowglen at dawn")
print(result1.output)

# Second call - agent remembers context from first call
result2 = await narrator.run("Now describe the ancient trees")
# Agent maintains consistent tone and references previous narration
print(result2.output)
```

### As Tool in Orchestrator

```python
class OrchestratorAgent:
    def __init__(self, session_id: str):
        # ... orchestrator setup ...

        self._narrator = NarratorAgent(session_id)

        @self.agent.tool
        async def create_narration(ctx: RunContext, reference_text: str) -> str:
            """Creates narrative text based on reference material."""
            result = await self._narrator.run(reference_text)
            return result.output.text if hasattr(result.output, 'text') else result.output
```

### Session Sharing for Coherence

```python
# Share session ID across related agents for coherent output
session_id = "story_creation_456"

narrator = NarratorAgent(session_id)
dialog_agent = DialogCreatorAgent(session_id)

# Both agents maintain consistent tone within this session
narration = await narrator.run("Describe the village square")
dialogue = await dialog_agent.run("Create dialogue between villagers")
```

---

## Structured Output Pattern

### Output Model Definition

**File:** `models/output_models.py`

```python
from pydantic import BaseModel, Field

class Narration(BaseModel):
    """Narrative text for a story section."""
    text: str = Field(description="The narrative text")
    word_count: int = Field(description="Number of words in narration")
    tone: str = Field(description="The tone of the narration (e.g., mysterious, uplifting)")
```

### Agent with Structured Output

```python
from src.agents.narrator_agent.models.output_models import Narration

class NarratorAgent:
    AGENT_ID = "narrator"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            output_type=Narration,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[Narration]:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```

### Using Structured Output

```python
narrator = NarratorAgent(session_id="test")
result = await narrator.run("Describe Shadowglen at twilight")

# Access structured fields
print(f"Text: {result.output.text}")
print(f"Words: {result.output.word_count}")
print(f"Tone: {result.output.tone}")
```

---

## Common Patterns

### Multi-Parameter Run Method

```python
async def run(self, reference_text: str, word_count: int = 100) -> AgentRunResult[Narration]:
    """Creates narration based on reference text with specific word count."""
    prompt = f"Create narration of {word_count} words based on:\n\n{reference_text}"

    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

### Template-Based Prompts

```python
from src.libs.utils.prompt_loader import load_prompt

async def run(self, actors: list[str], scene: str) -> AgentRunResult:
    """Creates dialogue between actors in a scene."""
    prompt_template = load_prompt(__file__, "create_dialogue")
    prompt = prompt_template.format(actors=", ".join(actors), scene=scene)

    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

---

## Performance Considerations

### Memory Management

```python
# GOOD: Load context once during initialization
def __init__(self, session_id: str):
    self.messages = load_context(self.AGENT_ID, session_id)

# BAD: Loading context on every run (slow!)
async def run(self, prompt: str):
    messages = load_context(self.AGENT_ID, self.session_id)  # Don't do this
```

### Session Sharing

```python
# GOOD: Same session ID for related agents (coherent output)
session_id = "research_session_123"
narrator = NarratorAgent(session_id)
dialog_agent = DialogCreatorAgent(session_id)

# They maintain consistent context within the session
```

### Async Consistency

```python
# GOOD: Always use async
async def run(self, prompt: str) -> AgentRunResult:
    agent_output = await self.agent.run(...)

# BAD: Mixing sync and async (performance issues)
def run(self, prompt: str) -> AgentRunResult:
    agent_output = self.agent.run_sync(...)  # Don't do this
```

---

## Testing

### Unit Testing

```python
import pytest
from src.agents.narrator_agent import NarratorAgent

@pytest.mark.asyncio
async def test_narrator_creates_narration():
    agent = NarratorAgent(session_id="test_session")

    prompt = "Describe a forest at dawn"
    result = await agent.run(prompt)

    assert result.output.text
    assert result.output.word_count > 0
    assert result.output.tone
```

### Context Persistence Testing

```python
@pytest.mark.asyncio
async def test_narrator_maintains_context():
    agent = NarratorAgent(session_id="test_context")

    # First interaction
    result1 = await agent.run("Describe Shadowglen")
    assert "Shadowglen" in result1.output.text

    # Second interaction references first
    result2 = await agent.run("Now describe leaving that place")

    # Agent should remember "that place" means Shadowglen
    # Check if context was maintained
    assert len(agent.messages) > 2  # Should have history
```

---

## Troubleshooting

### Context Not Persisting

**Issue:** Agent doesn't remember previous interactions

**Solution:**
- Verify `save_context()` is called after each run
- Check `.mythline/{agent_id}/context_memory/` directory exists
- Ensure session_id is consistent across calls
- Verify `self.messages` is being updated: `self.messages = agent_output.all_messages()`

### Output Model Validation Errors

**Issue:** Pydantic validation fails

**Solution:**
- Review model field requirements
- Check system prompt instructs correct output format
- Use Field descriptions to guide model
- Test with simpler output first

### Performance Issues

**Issue:** Agent runs slowly

**Solution:**
- Verify context loaded ONCE in `__init__`, not in `run()`
- Sub-agents should be lightweight (no MCP servers)
- Consider reducing context length with summarization
- Use async consistently
- Profile LLM response time

### Session Confusion

**Issue:** Different sessions interfering with each other

**Solution:**
- Use unique session_id for each conversation
- Don't reuse session_ids across unrelated tasks
- Clean up old session files if needed

---

## Comparison with Stateless Agents

| Feature | Stateful | Stateless |
|---------|----------|-----------|
| **Session ID** | Yes (required) | No |
| **Context Memory** | Yes | No |
| **Message History** | Yes | No |
| **Performance** | Slower (disk I/O) | Faster |
| **Use Case** | Conversations | One-time tasks |
| **Complexity** | More complex | Simpler |
| **Coherence** | Multi-turn | Per-call only |
| **Storage** | Disk I/O | None |

---

## Migration Path

### Converting Stateful to Stateless

```python
# Original stateful
class MyAgent:
    AGENT_ID = "my_agent"

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = load_context(self.AGENT_ID, session_id)
        self.agent = Agent(...)

    async def run(self, prompt: str):
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output

# Convert to stateless (remove memory)
class MyAgent:
    AGENT_ID = "my_agent"

    def __init__(self):  # Remove session_id
        # Remove: self.session_id
        # Remove: self.messages = load_context(...)
        self.agent = Agent(...)

    async def run(self, prompt: str):
        agent_output = await self.agent.run(prompt)  # Remove message_history
        # Remove: self.messages = agent_output.all_messages()
        # Remove: save_context(...)
        return agent_output
```

---

## Related Blueprints

- **[agent_stateless_subagent.md](agent_stateless_subagent.md)** - Stateless agent pattern
- **[agent_orchestrator.md](agent_orchestrator.md)** - Orchestrator with MCP pattern
- **[../graphs/graph_with_agents.md](../graphs/graph_with_agents.md)** - Using agents in graphs
- **[../../ENVIRONMENT.md](../../ENVIRONMENT.md)** - Environment configuration
- **[../../PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md)** - Project organization
