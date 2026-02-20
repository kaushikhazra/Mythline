# Stateless Sub-Agent Blueprint

**Purpose:** Executable specification for building stateless agents that perform single-purpose transformations without conversation history.

**For:** AI assistants generating code, developers creating new agents

---

## Overview

Stateless sub-agents are pure input-output processors used for analysis, extraction, and transformation tasks.

**Characteristics:**
- No conversation history or context memory
- Pure input-output transformation
- Fast and lightweight
- Used for one-time operations
- Often for analysis or extraction tasks
- No session ID required
- Can use structured output with Pydantic models

**When to use this pattern:**
- Each call is independent
- No conversation context needed
- Pure transformation/analysis
- Performance is critical (no memory I/O)
- Used as utility/helper function

---

## Default Implementation Pattern

**Unless the user specifies otherwise, implement stateless agents EXACTLY as follows:**

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

load_dotenv()

class {AgentClassName}:
    AGENT_ID = "{agent_id}"

    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult:
        agent_output = await self.agent.run(prompt)
        return agent_output
```

#### File: `agent.py` (With Structured Output)

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.{agent_name}.models.output_models import {OutputModel}

load_dotenv()

class {AgentClassName}:
    AGENT_ID = "{agent_id}"

    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type={OutputModel},
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[{OutputModel}]:
        agent_output = await self.agent.run(prompt)
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
4. Local imports (`from src.agents...`)

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
- Ends with "Agent" (e.g., `SentimentAgent`)

✓ **No session_id:**
- `__init__(self)` takes NO parameters
- No session tracking
- No conversation history

✓ **Async run method:**
- MUST be `async def run(...)`
- Return type MUST be `AgentRunResult` or `AgentRunResult[OutputModel]`
- No sync version needed

✓ **Prompt loading:**
- Use `load_system_prompt(__file__)`
- Prompt file MUST be `prompts/system_prompt.md`
- Use `__file__` (not hardcoded path)

### SHOULD Follow (Best Practices)

- Keep agents focused on single responsibility
- Use structured output for complex responses
- Add type hints to all methods
- Include docstrings in class and methods
- Reuse agent instances when calling multiple times

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
    def __init__(self):
        load_dotenv()  # Don't do this
        llm_model = os.getenv('LLM_MODEL')

# RIGHT - Load at module level
load_dotenv()  # Do this once at top

class MyAgent:
    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
```

### ❌ Sync run() Method

```python
# WRONG - Don't use sync
def run(self, prompt: str):
    return self.agent.run_sync(prompt)

# RIGHT - Must be async
async def run(self, prompt: str):
    return await self.agent.run(prompt)
```

### ❌ Adding session_id to Stateless Agent

```python
# WRONG - Stateless agents don't have session_id
class MyAgent:
    def __init__(self, session_id: str):  # Don't add this
        self.session_id = session_id

# RIGHT - No parameters for stateless
class MyAgent:
    def __init__(self):
        ...
```

### ❌ Adding Memory to Stateless Agent

```python
# WRONG - Stateless agents don't save context
async def run(self, prompt: str):
    self.messages = load_context(...)  # Don't do this
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    save_context(...)
    return agent_output

# RIGHT - Direct run, no memory
async def run(self, prompt: str):
    agent_output = await self.agent.run(prompt)
    return agent_output
```

### ❌ Hardcoded Model Names

```python
# WRONG - Don't hardcode model names
llm_model = "openai/gpt-4o"

# RIGHT - Use environment variable
llm_model = os.getenv('LLM_MODEL')
```

### ❌ Hardcoded Prompt Paths

```python
# WRONG - Don't hardcode paths
system_prompt = load_system_prompt('src/agents/my_agent/prompts/system_prompt.md')

# RIGHT - Use __file__
system_prompt = load_system_prompt(__file__)
```

---

## Code Generation Guide (For AI Assistants)

**When user requests a stateless agent, follow these steps:**

### Step 1: Parse Requirements

Extract from user request:
- **Agent name** (e.g., "sentiment analyzer")
- **Purpose** (e.g., "analyze sentiment of text")
- **Input type** (e.g., "text string")
- **Output type** (e.g., "sentiment classification" or structured model)

### Step 2: Generate Names

```python
agent_name = "{user_provided_name}"  # lowercase_with_underscores
                                      # e.g., "sentiment_agent"

agent_class = "{AgentClassName}"     # PascalCase
                                      # e.g., "SentimentAgent"

agent_id = "{agent_name}"            # same as directory name
                                      # e.g., "sentiment_agent"
```

### Step 3: Create Directory Structure

```bash
mkdir -p src/agents/{agent_name}/prompts
# If structured output needed:
mkdir -p src/agents/{agent_name}/models
```

### Step 4: Generate Files

Use templates above, substituting:
- `{agent_name}` → e.g., `sentiment_agent`
- `{AgentClassName}` → e.g., `SentimentAgent`
- `{agent_id}` → e.g., `sentiment_agent`
- `{OutputModel}` → e.g., `SentimentAnalysis` (if structured output)

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
- [ ] All imports in correct order
- [ ] `load_dotenv()` at module level
- [ ] `os.getenv('LLM_MODEL')` used correctly (no extra formatting)
- [ ] AGENT_ID matches directory name
- [ ] Class name is PascalCase
- [ ] No session_id parameter
- [ ] run() method is async
- [ ] Prompt loaded with `__file__`
- [ ] No context memory code
- [ ] All files use correct paths

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
- [ ] All imports in correct order (stdlib, third-party, local)
- [ ] `load_dotenv()` called once at module level
- [ ] `os.getenv('LLM_MODEL')` used directly (no f-string wrapping)
- [ ] AGENT_ID is lowercase_with_underscores
- [ ] AGENT_ID matches directory name
- [ ] Class name is PascalCase ending in "Agent"
- [ ] `__init__(self)` has NO session_id parameter
- [ ] `run()` method is `async def`
- [ ] Return type is `AgentRunResult` or `AgentRunResult[Model]`
- [ ] `load_system_prompt(__file__)` used (not hardcoded path)
- [ ] No context memory (load_context/save_context) calls
- [ ] No message history tracking

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
- [ ] Agent can be instantiated: `agent = {ClassName}()`
- [ ] Agent can run: `result = await agent.run("test input")`

---

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
        llm_model = os.getenv('LLM_MODEL')
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

---

## Usage Patterns

### One-Time Analysis

```python
from src.agents.user_preference_agent import UserPreferenceAgent

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

### In CLI/Graph/Test Files

**CRITICAL:** When using agents in CLI, graphs, or tests, ALWAYS load dotenv at module level:

```python
# File: src/ui/cli/analyze_preferences.py
import os
from dotenv import load_dotenv
from src.agents.user_preference_agent import UserPreferenceAgent

load_dotenv()  # MUST be here!

def main():
    agent = UserPreferenceAgent()
    result = agent.run("I love dark stories")
    print(result.output)

if __name__ == "__main__":
    main()
```

```python
# File: tests/agents/test_preference_agent.py
import os
import pytest
from dotenv import load_dotenv
from src.agents.user_preference_agent import UserPreferenceAgent

load_dotenv()  # MUST be here!

@pytest.mark.asyncio
async def test_preference_extraction():
    agent = UserPreferenceAgent()
    result = await agent.run("I prefer epic battles")
    assert result.output
```

**Why this is critical:**
- Without `load_dotenv()`, `os.getenv('LLM_MODEL')` returns `None`
- Agent initialization fails with unclear errors
- Tests pass locally but fail in CI/CD
- CLI scripts work in dev but fail in production

**Rule:** Better to call `load_dotenv()` multiple times than forget it once!

---

## Structured Output Pattern

### Output Model Definition

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
        llm_model = os.getenv('LLM_MODEL')
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

---

## Common Use Cases

### Text Analysis

```python
class SentimentAnalyzer:
    """Analyzes sentiment of text without needing conversation history."""
    AGENT_ID = "sentiment_analyzer"

    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
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
        llm_model = os.getenv('LLM_MODEL')
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
        llm_model = os.getenv('LLM_MODEL')
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
        llm_model = os.getenv('LLM_MODEL')
        system_prompt = "Validate if content meets the specified criteria."

        self.agent = Agent(llm_model, system_prompt=system_prompt)

    async def run(self, content: str, criteria: str) -> AgentRunResult:
        prompt = f"Content:\n{content}\n\nCriteria:\n{criteria}\n\nValidate:"
        return await self.agent.run(prompt)
```

---

## Performance Considerations

### Speed Advantage

Stateless agents are faster because:
- No context loading from disk
- No context saving to disk
- Smaller prompts (no message history)
- Less token usage

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

### Caching (Advanced)

```python
from functools import lru_cache

class StatelessAgent:
    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)
        self.agent = Agent(llm_model, system_prompt=system_prompt)

    @lru_cache(maxsize=100)
    async def run_cached(self, text: str) -> str:
        """Cache results for identical inputs."""
        result = await self.agent.run(text)
        return result.output
```

---

## Testing

### Unit Testing

```python
import pytest
from src.agents.user_preference_agent import UserPreferenceAgent

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

---

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

---

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

---

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

---

## Related Blueprints

- **[agent_stateful_subagent.md](agent_stateful_subagent.md)** - Stateful agent pattern
- **[agent_orchestrator.md](agent_orchestrator.md)** - Orchestrator with MCP pattern
- **[../graphs/graph_with_agents.md](../graphs/graph_with_agents.md)** - Using agents in graphs
- **[../../ENVIRONMENT.md](../../ENVIRONMENT.md)** - Environment configuration
- **[../../PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md)** - Project organization
