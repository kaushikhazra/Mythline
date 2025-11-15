# Stateful Sub-Agent Blueprint

This blueprint covers stateful sub-agents that maintain context memory for coherent multi-turn conversations but don't use MCP servers. These agents are typically called by orchestrator agents for specialized tasks.

## Overview

Stateful sub-agents:
- Maintain conversation history via context memory
- Generate coherent output across multiple interactions
- Have focused, single-purpose responsibilities
- Can use structured output with Pydantic models
- Are called by orchestrator agents or used in graphs
- No MCP servers (lightweight and fast)

## Agent Structure

```
src/agents/{agent_name}/
├── __init__.py
├── agent.py
├── prompts/
│   └── system_prompt.md
└── models/           # Optional - if using structured output
    └── output_models.py
```

## Implementation Patterns

### Basic Stateful Agent (Text Output)

**File:** `agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import save_context, load_context

load_dotenv()

class {AgentName}:
    AGENT_ID = "{agent_id}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
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

### Stateful Agent with Structured Output

**File:** `agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import save_context, load_context
from src.agents.{agent_name}.models.output_models import {OutputModel}

load_dotenv()

class {AgentName}:
    AGENT_ID = "{agent_id}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
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

**File:** `models/output_models.py`

```python
from pydantic import BaseModel

class {OutputModel}(BaseModel):
    """Description of what this output represents."""
    field1: str
    field2: int
    field3: list[str]
```

## Key Components

### Agent ID

```python
AGENT_ID = "{agent_id}"
```

- Unique identifier for the agent
- Used for context memory storage
- Lowercase with underscores
- Should match the agent directory name

### Session ID

```python
def __init__(self, session_id: str):
    self.session_id = session_id
```

- Passed to constructor for session management
- Enables multi-session support
- Each session has independent conversation history
- Required for context memory

### Context Memory

```python
from src.libs.agent_memory.context_memory import save_context, load_context

self.messages = load_context(self.AGENT_ID, session_id)

# After agent run
self.messages = agent_output.all_messages()
save_context(self.AGENT_ID, self.session_id, self.messages)
```

**Storage Location:** `.mythline/{agent_id}/context_memory/{session_id}.json`

**Purpose:**
- Maintains conversation history
- Enables coherent multi-turn interactions
- Agent remembers previous context
- Separate file per session

### System Prompt

```python
from src.libs.utils.prompt_loader import load_system_prompt

system_prompt = load_system_prompt(__file__)
```

**File:** `prompts/system_prompt.md`

```markdown
# Persona

You are a [role description].

# Task

Your task is to [task description].

# Instructions

1. [Instruction 1]
2. [Instruction 2]
3. [Instruction 3]

# Constraints

- [Constraint 1]
- [Constraint 2]

# Output

Return [output description].
```

### Run Method

```python
async def run(self, prompt: str) -> AgentRunResult:
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Always async** for consistency and performance.

## Structured Output with Pydantic Models

### When to Use Structured Output

Use structured output when:
- Output has specific required fields
- Data needs validation
- Output consumed by other code (not just humans)
- Type safety is important
- Used in graph workflows

### Defining Output Models

**File:** `models/output_models.py`

```python
from pydantic import BaseModel, Field

class Narration(BaseModel):
    """Narrative text for a story section."""
    text: str = Field(description="The narrative text")
    word_count: int = Field(description="Number of words in narration")
    tone: str = Field(description="The tone of the narration")

class DialogueLines(BaseModel):
    """Dialogue between characters."""
    speaker: str = Field(description="Name of the character speaking")
    line: str = Field(description="What the character says")
    emotion: str = Field(description="Emotional state of the speaker")
```

### Using Structured Output

```python
from src.agents.narrator_agent.models.output_models import Narration

self.agent = Agent(
    llm_model,
    output_type=Narration,
    system_prompt=system_prompt
)

async def run(self, prompt: str) -> AgentRunResult[Narration]:
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    # Access structured output
    narration_text = agent_output.output.text
    word_count = agent_output.output.word_count
    return agent_output
```

## Usage by Orchestrator Agents

### As a Tool in Orchestrator

```python
class OrchestratorAgent:
    def __init__(self, session_id: str):
        # ... orchestrator setup ...

        self._sub_agent = SubAgent(session_id)

        @self.agent.tool
        async def use_sub_agent(ctx: RunContext, input_text: str) -> str:
            """Calls the sub-agent for specialized processing."""
            result = await self._sub_agent.run(input_text)
            return result.output
```

### Direct Call Pattern

```python
from src.agents.narrator_agent.agent import NarratorAgent

narrator = NarratorAgent(session_id="session_123")

prompt = "Create narration for entering Shadowglen at dawn"
result = await narrator.run(prompt)

narration = result.output
print(narration)
```

## Real-World Example: Narrator Agent

**Purpose:** Creates narrative text for story sections

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

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
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

## Best Practices

### Memory Management

```python
# GOOD: Load context once during initialization
def __init__(self, session_id: str):
    self.messages = load_context(self.AGENT_ID, session_id)

# BAD: Loading context on every run
async def run(self, prompt: str):
    messages = load_context(self.AGENT_ID, self.session_id)  # Don't do this
```

### Session Sharing

```python
# GOOD: Same session ID for related agents
session_id = "research_session_123"
narrator = NarratorAgent(session_id)
dialog_agent = DialogCreatorAgent(session_id)

# They can reference each other's context implicitly through shared memory
```

### Async Consistency

```python
# GOOD: Always use async
async def run(self, prompt: str) -> AgentRunResult:
    agent_output = await self.agent.run(...)

# BAD: Mixing sync and async
def run(self, prompt: str) -> AgentRunResult:
    agent_output = self.agent.run_sync(...)  # Don't do this for sub-agents
```

### Error Handling

```python
async def run(self, prompt: str) -> AgentRunResult:
    try:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
    except Exception as e:
        print(f"Error in {self.AGENT_ID}: {e}")
        raise
```

## Common Patterns

### Multi-Parameter Run Method

```python
async def run(self, reference_text: str, word_count: int) -> AgentRunResult[Narration]:
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

async def run(self, actors: list[str], reference_text: str) -> AgentRunResult:
    """Creates dialogue between actors."""
    prompt_template = load_prompt(__file__, "create_dialogue")
    prompt = prompt_template.format(actors=actors, reference_text=reference_text)

    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

## Testing

### Unit Testing

```python
import pytest
from src.agents.narrator_agent.agent import NarratorAgent

@pytest.mark.asyncio
async def test_narrator_creates_narration():
    agent = NarratorAgent(session_id="test_session")

    prompt = "Describe a forest at dawn"
    result = await agent.run(prompt)

    assert result.output.text
    assert result.output.word_count > 0
    assert result.output.tone
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_narrator_maintains_context():
    agent = NarratorAgent(session_id="test_context")

    # First interaction
    result1 = await agent.run("Describe Shadowglen")

    # Second interaction references first
    result2 = await agent.run("Now describe leaving that place")

    # Agent should remember "that place" means Shadowglen
    assert "Shadowglen" in result2.output.text or agent.messages
```

## Troubleshooting

### Context Not Persisting

**Issue:** Agent doesn't remember previous interactions

**Solution:**
- Verify `save_context()` is called after each run
- Check `.mythline/{agent_id}/context_memory/` directory exists
- Ensure session_id is consistent across calls

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
- Sub-agents should be lightweight (no MCP servers)
- Consider reducing context length with summarization
- Use async consistently
- Profile LLM response time

## File Checklist

When creating a new stateful sub-agent:

- [ ] `__init__.py` - Export agent class
- [ ] `agent.py` - Agent implementation
- [ ] `prompts/system_prompt.md` - System prompt
- [ ] `models/output_models.py` - Output models (if structured)
- [ ] Test file in `tests/agents/`
- [ ] Documentation in agent docstring

## Related Blueprints

- `agent_stateless_subagent.md` - Stateless agent pattern
- `agent_orchestrator.md` - Orchestrator with MCP pattern
- `../graphs/graph_with_agents.md` - Using agents in graphs
