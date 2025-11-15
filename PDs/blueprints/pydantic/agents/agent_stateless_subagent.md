# Stateless Sub-Agent Blueprint

This blueprint covers stateless sub-agents that perform single-purpose transformations without maintaining conversation history. These agents are pure input-output processors used for analysis, extraction, and transformation tasks.

## Overview

Stateless sub-agents:
- No conversation history or context memory
- Pure input-output transformation
- Fast and lightweight
- Used for one-time operations
- Often for analysis or extraction tasks
- No session ID required
- Can use structured output with Pydantic models

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

## Implementation Pattern

### Basic Stateless Agent

**File:** `agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()

class {AgentName}:
    AGENT_ID = "{agent_id}"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult:
        agent_output = await self.agent.run(prompt)
        return agent_output
```

### Key Differences from Stateful Agents

**No session_id:**
```python
# Stateless - no session_id parameter
def __init__(self):
    ...

# Stateful - requires session_id
def __init__(self, session_id: str):
    ...
```

**No context memory:**
```python
# Stateless - no message history
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt)
    return agent_output

# Stateful - loads and saves context
async def run(self, prompt: str):
    self.messages = load_context(...)
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    save_context(...)
    return agent_output
```

## Real-World Example: User Preference Agent

**Purpose:** Extracts user preferences from messages for long-term memory

**File:** `src/agents/user_preference_agent/agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()

class UserPreferenceAgent:
    AGENT_ID = "user_preference"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult:
        agent_output = await self.agent.run(prompt)
        return agent_output
```

**System Prompt:** `prompts/system_prompt.md`

```markdown
# Persona

You are an expert at identifying and extracting user preferences from conversations.

# Task

Analyze the provided user message and extract any meaningful preferences, likes, dislikes, or stylistic choices the user has expressed.

# Instructions

1. Look for explicit statements of preference
2. Identify implicit preferences from context
3. Extract tone and style preferences
4. Note content preferences
5. Return "none" if no clear preferences found

# Constraints

- Only extract actual preferences, not casual mentions
- Be specific and actionable
- Keep extractions concise
- Don't infer preferences that aren't there

# Output

Return a clear statement of the user's preference, or "none" if no preference detected.
```

## Usage Patterns

### One-Time Analysis

```python
from src.agents.user_preference_agent.agent import UserPreferenceAgent

# Create instance
preference_agent = UserPreferenceAgent()

# Use once
user_message = "I prefer dark, atmospheric stories with complex characters"
result = await preference_agent.run(user_message)

if result.output.lower().strip() != "none":
    save_long_term_memory(AGENT_ID, result.output)
```

### Multiple Independent Calls

```python
# Each call is independent - no shared state
agent = UserPreferenceAgent()

result1 = await agent.run("I love epic battles")
result2 = await agent.run("I prefer short stories")
result3 = await agent.run("More dragons please")

# Each result is independent, no context between calls
```

### Within Orchestrator as Tool

```python
class OrchestratorAgent:
    def __init__(self, session_id: str):
        self._preference_agent = UserPreferenceAgent()

        @self.agent.tool
        async def extract_preference(ctx: RunContext, user_message: str) -> str:
            """Extracts user preferences from a message."""
            result = await self._preference_agent.run(user_message)

            if result.output.lower().strip() != "none":
                save_long_term_memory(self.AGENT_ID, result.output)
                return f"Preference saved: {result.output}"

            return "No preference detected"
```

## With Structured Output

### Output Model

**File:** `models/output_models.py`

```python
from pydantic import BaseModel, Field

class PreferenceAnalysis(BaseModel):
    """Structured preference analysis."""
    has_preference: bool = Field(description="Whether a preference was found")
    preference_type: str = Field(description="Type of preference (tone, content, style, etc.)")
    preference_text: str = Field(description="The extracted preference")
    confidence: float = Field(description="Confidence score 0-1")
```

### Agent with Structured Output

```python
from src.agents.preference_agent.models.output_models import PreferenceAnalysis

class PreferenceAgent:
    AGENT_ID = "preference_analyzer"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=PreferenceAnalysis,
            system_prompt=system_prompt
        )

    async def run(self, user_message: str) -> AgentRunResult[PreferenceAnalysis]:
        agent_output = await self.agent.run(user_message)
        return agent_output
```

### Using Structured Output

```python
agent = PreferenceAgent()
result = await agent.run("I really enjoy mystery elements in my stories")

if result.output.has_preference and result.output.confidence > 0.7:
    print(f"Type: {result.output.preference_type}")
    print(f"Preference: {result.output.preference_text}")
```

## Common Use Cases

### Text Analysis

```python
class SentimentAnalyzer:
    """Analyzes sentiment of text without needing conversation history."""
    AGENT_ID = "sentiment_analyzer"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = "Analyze the sentiment of the given text."

        self.agent = Agent(llm_model, system_prompt=system_prompt)

    async def run(self, text: str) -> AgentRunResult:
        return await self.agent.run(text)
```

### Content Extraction

```python
class KeywordExtractor:
    """Extracts keywords from content."""
    AGENT_ID = "keyword_extractor"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = "Extract key topics and keywords from the content."

        self.agent = Agent(llm_model, system_prompt=system_prompt)

    async def run(self, content: str) -> AgentRunResult:
        return await self.agent.run(content)
```

### Format Conversion

```python
class MarkdownConverter:
    """Converts text to markdown format."""
    AGENT_ID = "markdown_converter"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = "Convert the given text to well-formatted markdown."

        self.agent = Agent(llm_model, system_prompt=system_prompt)

    async def run(self, text: str) -> AgentRunResult:
        return await self.agent.run(text)
```

### Validation

```python
class ContentValidator:
    """Validates content meets criteria."""
    AGENT_ID = "content_validator"

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = "Validate if content meets the specified criteria."

        self.agent = Agent(llm_model, system_prompt=system_prompt)

    async def run(self, content: str, criteria: str) -> AgentRunResult:
        prompt = f"Content:\n{content}\n\nCriteria:\n{criteria}\n\nValidate:"
        return await self.agent.run(prompt)
```

## Best Practices

### When to Use Stateless vs Stateful

**Use Stateless when:**
- Each call is independent
- No conversation context needed
- Pure transformation/analysis
- Performance is critical (no memory I/O)
- Used as utility/helper function

**Use Stateful when:**
- Multi-turn conversation
- Context matters for quality
- Building on previous responses
- Maintaining coherence

### Instance Reuse

```python
# GOOD: Reuse instance for multiple calls
agent = PreferenceAgent()
for message in messages:
    result = await agent.run(message)

# OK but less efficient: New instance each time
for message in messages:
    agent = PreferenceAgent()
    result = await agent.run(message)
```

### Prompt Templates

```python
async def run(self, content: str, instruction: str) -> AgentRunResult:
    """Flexible prompt construction."""
    prompt = f"{instruction}\n\nContent:\n{content}"
    return await self.agent.run(prompt)
```

### Error Handling

```python
async def run(self, text: str) -> AgentRunResult:
    try:
        return await self.agent.run(text)
    except Exception as e:
        print(f"Error in {self.AGENT_ID}: {e}")
        raise
```

## Performance Considerations

### Speed Advantage

Stateless agents are faster because:
- No context loading from disk
- No context saving to disk
- Smaller prompts (no message history)
- Less token usage

### Caching

```python
from functools import lru_cache

class StatelessAgent:
    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)
        self.agent = Agent(llm_model, system_prompt=system_prompt)

    @lru_cache(maxsize=100)
    async def run_cached(self, text: str) -> str:
        """Cache results for identical inputs."""
        result = await self.agent.run(text)
        return result.output
```

## Testing

### Unit Testing

```python
import pytest
from src.agents.user_preference_agent.agent import UserPreferenceAgent

@pytest.mark.asyncio
async def test_extracts_preference():
    agent = UserPreferenceAgent()

    result = await agent.run("I love dark fantasy stories")

    assert result.output
    assert result.output.lower() != "none"

@pytest.mark.asyncio
async def test_returns_none_when_no_preference():
    agent = UserPreferenceAgent()

    result = await agent.run("What's the weather today?")

    assert result.output.lower().strip() == "none"
```

### Independence Testing

```python
@pytest.mark.asyncio
async def test_calls_are_independent():
    agent = UserPreferenceAgent()

    result1 = await agent.run("I prefer action")
    result2 = await agent.run("What about romance?")

    # Second call shouldn't know about first call
    assert "action" not in result2.output.lower()
```

## Comparison with Stateful Agents

| Feature | Stateless | Stateful |
|---------|-----------|----------|
| **Session ID** | No | Yes |
| **Context Memory** | No | Yes |
| **Message History** | No | Yes |
| **Performance** | Faster | Slower |
| **Use Case** | One-time tasks | Conversations |
| **Complexity** | Simpler | More complex |
| **Coherence** | Per-call only | Multi-turn |
| **Storage** | None | Disk I/O |

## Migration Path

### Converting Stateless to Stateful

```python
# Original stateless
class MyAgent:
    def __init__(self):
        self.agent = Agent(...)

    async def run(self, prompt: str):
        return await self.agent.run(prompt)

# Convert to stateful
class MyAgent:
    AGENT_ID = "my_agent"

    def __init__(self, session_id: str):  # Add session_id
        self.session_id = session_id
        self.messages = load_context(self.AGENT_ID, session_id)  # Add context
        self.agent = Agent(...)

    async def run(self, prompt: str):
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()  # Track messages
        save_context(self.AGENT_ID, self.session_id, self.messages)  # Save context
        return agent_output
```

## File Checklist

When creating a new stateless sub-agent:

- [ ] `__init__.py` - Export agent class
- [ ] `agent.py` - Agent implementation
- [ ] `prompts/system_prompt.md` - System prompt
- [ ] `models/output_models.py` - Output models (if structured)
- [ ] Test file in `tests/agents/`
- [ ] Documentation in agent docstring

## Troubleshooting

### When Context Seems Missing

**Issue:** Agent doesn't seem to understand context from previous calls

**Solution:** This is expected! Stateless agents don't maintain context. Consider:
- Use stateful agent if context needed
- Pass more context in the prompt
- Use structured output to chain calls

### Performance Not Improved

**Issue:** Stateless agent not faster than stateful

**Solution:**
- Profile to identify bottleneck
- Check LLM response time (main factor)
- Verify no unnecessary I/O operations
- Consider prompt length

## Related Blueprints

- `agent_stateful_subagent.md` - Stateful agent pattern
- `agent_orchestrator.md` - Orchestrator with MCP pattern
- `../graphs/graph_with_agents.md` - Using agents in graphs
