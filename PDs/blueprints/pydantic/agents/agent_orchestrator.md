# Orchestrator Agent Blueprint

**Purpose:** Executable specification for creating orchestrator agents that coordinate MCP servers, sub-agents, and both memory systems.

**For:** AI assistants and developers building complex agent orchestrators.

---

## Overview

Orchestrator agents:
- Load and use MCP servers for external tools (web search, filesystem, knowledge base)
- Maintain full conversation context (short-term) and long-term memory (preferences)
- Delegate specialized tasks to stateful/stateless sub-agents via custom tools
- Provide custom tools for complex operations and workflows
- Handle multi-turn conversations with users
- Support multiple run modes: sync, async, streaming

**When to use this pattern:**
- Agent needs external tools (web, files, databases)
- Agent coordinates multiple sub-agents
- Agent is the primary user-facing interface
- Agent needs both conversation history and user preferences

**When NOT to use:**
- Simple single-purpose tasks → Use stateless sub-agent
- Only needs conversation memory → Use stateful sub-agent
- No external tools needed → Use sub-agent pattern

## Agent Structure

```
src/agents/{agent_name}/
├── __init__.py
├── agent.py
├── prompts/
│   ├── system_prompt.md
│   └── {tool_name}.md    # Optional: prompt templates for tools
└── config/
    └── mcp_config.json   # MCP server configuration
```

---

## Default Implementation Pattern

### MUST Follow This Exact Structure

This is the canonical pattern. Copy this template and fill in placeholders `{like_this}`.

**File:** `src/agents/{agent_name}/agent.py`

```python
import os

from dotenv import load_dotenv
from termcolor import colored

from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import Agent, RunContext

from src.libs.utils.prompt_loader import load_system_prompt, load_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory
from src.agents.{sub_agent}.agent import {SubAgent}

load_dotenv()

class {OrchestratorName}:
    AGENT_ID = "{orchestrator_id}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)
        system_prompt += self._load_preferences()

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )

        self._sub_agent = {SubAgent}(session_id)

        @self.agent.tool
        async def custom_tool(ctx: RunContext, param: str) -> str:
            """Tool description."""
            print(colored(f"⚙ Calling custom tool with: {param}", "grey"))

            result = await self._sub_agent.run(param)

            print(colored(f"\n⚙ Got response: {result.output}", "grey"))

            return result.output

    def _load_preferences(self) -> str:
        """Loads long-term memory preferences."""
        preferences = load_long_term_memory(self.AGENT_ID)
        if not preferences:
            return ""

        preferences_text = "\n\n##Memory:\n"
        for pref in preferences:
            preferences_text += f"- {pref['preference']}\n"

        return preferences_text

    def run(self, prompt: str) -> AgentRunResult:
        """Synchronous run for CLI interfaces."""
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output

    async def run_async(self, prompt: str) -> AgentRunResult:
        """Async run for web interfaces and graphs."""
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output

    async def run_stream(self, prompt: str):
        """Streaming run for real-time responses."""
        async with self.agent.run_stream(prompt, message_history=self.messages) as result:
            async for chunk in result.stream_text(delta=True):
                yield chunk

            self.messages = result.all_messages()
            save_context(self.AGENT_ID, self.session_id, self.messages)
```

**File:** `src/agents/{agent_name}/config/mcp_config.json`

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    },
    "web-crawler": {
      "url": "http://localhost:8001/mcp"
    },
    "knowledge-base": {
      "url": "http://localhost:8003/mcp"
    }
  }
}
```

**File:** `src/agents/{agent_name}/__init__.py`

```python
from .agent import {AgentClassName}

__all__ = ['{AgentClassName}']
```

**File:** `src/agents/{agent_name}/prompts/system_prompt.md`

See [System Prompt Structure](#system-prompt-structure) section below.

---

## Implementation Rules (MUST Follow)

### 1. Import Order

✓ **REQUIRED order:**
```python
# 1. Standard library
import os

# 2. Third-party (dotenv, termcolor)
from dotenv import load_dotenv
from termcolor import colored

# 3. Pydantic AI
from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import Agent, RunContext

# 4. Local utilities
from src.libs.utils.prompt_loader import load_system_prompt, load_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory

# 5. Sub-agents
from src.agents.{sub_agent}.agent import {SubAgent}

# 6. Load environment AT MODULE LEVEL
load_dotenv()
```

### 2. Class Structure

✓ **REQUIRED:**
- Class name: `PascalCase` ending in descriptive noun (e.g., `StoryResearcher`, `ShotCreator`)
- `AGENT_ID`: lowercase_with_underscores, matches directory name
- `__init__(session_id: str)`: Takes session_id parameter
- `run(prompt: str) -> AgentRunResult`: Synchronous method for CLI
- `run_async(prompt: str) -> AgentRunResult`: Async method for web/graphs
- `run_stream(prompt: str)`: Generator for streaming responses
- `_load_preferences() -> str`: Private method for long-term memory

### 3. Environment Loading

✓ **RIGHT - Load at module level:**
```python
load_dotenv()  # At top of file, AFTER imports

class MyAgent:
    def __init__(self, session_id: str):
        llm_model = os.getenv('LLM_MODEL')  # Use directly
```

❌ **WRONG - Don't load in __init__:**
```python
class MyAgent:
    def __init__(self, session_id: str):
        load_dotenv()  # Don't do this!
```

### 4. Model Format

✓ **RIGHT - Use directly (OpenRouter format):**
```python
llm_model = os.getenv('LLM_MODEL')
# Model already includes provider: "openai/gpt-4o-mini"
```

❌ **WRONG - Don't add prefix:**
```python
llm_model = f"openai:{os.getenv('LLM_MODEL')}"  # Don't do this!
```

### 5. MCP Server Loading

✓ **REQUIRED pattern:**
```python
def __init__(self, session_id: str):
    # ... other setup ...

    servers = load_mcp_servers(load_mcp_config(__file__))

    self.agent = Agent(
        llm_model,
        system_prompt=system_prompt,
        toolsets=servers  # ← MCP servers here
    )
```

❌ **WRONG - Manual server loading:**
```python
# Don't manually configure MCP servers
# Always use load_mcp_servers(load_mcp_config(__file__))
```

### 6. Context Memory Pattern

✓ **REQUIRED - Load ONCE in __init__, save AFTER every run:**
```python
def __init__(self, session_id: str):
    self.session_id = session_id
    self.messages = load_context(self.AGENT_ID, session_id)  # Load once
    # ... create agent ...

def run(self, prompt: str) -> AgentRunResult:
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()  # Update
    save_context(self.AGENT_ID, self.session_id, self.messages)  # Save
    return agent_output
```

❌ **WRONG - Loading on every run:**
```python
def run(self, prompt: str):
    messages = load_context(self.AGENT_ID, self.session_id)  # Slow! Don't do this!
```

### 7. Long-term Memory Pattern

✓ **REQUIRED - Load in __init__, append to system prompt:**
```python
def __init__(self, session_id: str):
    # ... setup ...
    system_prompt = load_system_prompt(__file__)
    system_prompt += self._load_preferences()  # Add preferences

    self.agent = Agent(llm_model, system_prompt=system_prompt, ...)

def _load_preferences(self) -> str:
    preferences = load_long_term_memory(self.AGENT_ID)
    if not preferences:
        return ""

    preferences_text = "\n\n##Memory:\n"
    for pref in preferences:
        preferences_text += f"- {pref['preference']}\n"

    return preferences_text
```

### 8. Custom Tool Pattern

✓ **REQUIRED - Decorator inside __init__, async, use RunContext:**
```python
def __init__(self, session_id: str):
    # ... create agent first ...

    self._sub_agent = SubAgent(session_id)  # Initialize sub-agent

    @self.agent.tool
    async def tool_name(ctx: RunContext, param: str) -> str:
        """Clear description for LLM."""
        print(colored(f"⚙ Tool action", "grey"))

        result = await self._sub_agent.run(param)

        print(colored(f"✓ Tool complete", "green"))
        return result.output
```

❌ **WRONG - Tool outside __init__:**
```python
class MyAgent:
    @self.agent.tool  # Can't access self here!
    async def tool_name(...):
        pass
```

### 9. Run Method Consistency

✓ **REQUIRED - All three run methods must save context:**
```python
def run(self, prompt: str) -> AgentRunResult:
    """Sync for CLI."""
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output

async def run_async(self, prompt: str) -> AgentRunResult:
    """Async for web/graphs."""
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output

async def run_stream(self, prompt: str):
    """Streaming for real-time UI."""
    async with self.agent.run_stream(prompt, message_history=self.messages) as result:
        async for chunk in result.stream_text(delta=True):
            yield chunk

        self.messages = result.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
```

### 10. Sub-Agent Initialization

✓ **REQUIRED - Initialize in __init__, pass session_id:**
```python
def __init__(self, session_id: str):
    # ... setup ...

    # Stateful sub-agents need session_id
    self._narrator = NarratorAgent(session_id)
    self._dialog_creator = DialogCreatorAgent(session_id)

    # Stateless sub-agents don't need session_id
    self._preference_agent = UserPreferenceAgent()
```

---

## Anti-Patterns (Common Mistakes)

### Anti-Pattern 1: Loading Context Memory on Every Run

❌ **WRONG:**
```python
def run(self, prompt: str):
    messages = load_context(self.AGENT_ID, self.session_id)  # Slow!
    agent_output = self.agent.run_sync(prompt, message_history=messages)
    save_context(self.AGENT_ID, self.session_id, agent_output.all_messages())
    return agent_output
```

✓ **RIGHT:**
```python
def __init__(self, session_id: str):
    self.messages = load_context(self.AGENT_ID, session_id)  # Load once

def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Why:** Loading context on every run is 10-100x slower. Load once in `__init__`.

### Anti-Pattern 2: Forgetting to Save Context

❌ **WRONG:**
```python
def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    return agent_output  # Forgot to save!
```

✓ **RIGHT:**
```python
def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)  # Save!
    return agent_output
```

**Why:** Context must be saved after every run or conversation history is lost.

### Anti-Pattern 3: Wrong Model Format

❌ **WRONG:**
```python
llm_model = f"openai:{os.getenv('LLM_MODEL')}"
# Results in: "openai:openai/gpt-4o-mini" (double prefix!)
```

✓ **RIGHT:**
```python
llm_model = os.getenv('LLM_MODEL')
# Results in: "openai/gpt-4o-mini" (correct OpenRouter format)
```

**Why:** OpenRouter models already include provider prefix.

### Anti-Pattern 4: MCP Config Not Matching .env

❌ **WRONG:**
```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

```env
# In .env file
MCP_WEB_SEARCH_PORT=9000  # Different port!
```

✓ **RIGHT:**
```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

```env
MCP_WEB_SEARCH_PORT=9000  # Ports match!
```

**Why:** MCP config URLs must match the ports MCP servers are running on.

### Anti-Pattern 5: Sync Tool with Async Sub-Agent

❌ **WRONG:**
```python
@self.agent.tool
def create_content(ctx: RunContext, topic: str) -> str:  # Not async!
    result = await self._sub_agent.run(topic)  # Can't await in sync function!
    return result.output
```

✓ **RIGHT:**
```python
@self.agent.tool
async def create_content(ctx: RunContext, topic: str) -> str:  # Async!
    result = await self._sub_agent.run(topic)
    return result.output
```

**Why:** Sub-agent `run()` methods are async, so tools must be async too.

### Anti-Pattern 6: Not Passing message_history

❌ **WRONG:**
```python
def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt)  # No message_history!
    return agent_output
```

✓ **RIGHT:**
```python
def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Why:** Without message_history, agent has no conversation context.

### Anti-Pattern 7: Poor Tool Descriptions

❌ **WRONG:**
```python
@self.agent.tool
async def create_stuff(ctx: RunContext, thing: str) -> str:
    """Creates stuff."""  # Vague!
    pass
```

✓ **RIGHT:**
```python
@self.agent.tool
async def create_narration(ctx: RunContext, reference_text: str, word_count: int) -> str:
    """Creates narrative text of specified word count based on reference material.

    Args:
        reference_text: Source material for narration
        word_count: Target length in words (50-5000)

    Returns:
        Narrative text in established story tone
    """
    pass
```

**Why:** LLM needs clear descriptions to know when and how to use tools.

### Anti-Pattern 8: Stateless Sub-Agent with session_id

❌ **WRONG:**
```python
self._preference_agent = UserPreferenceAgent(session_id)  # Stateless agents don't take session_id!
```

✓ **RIGHT:**
```python
# Stateful sub-agents
self._narrator = NarratorAgent(session_id)

# Stateless sub-agents
self._preference_agent = UserPreferenceAgent()
```

**Why:** Stateless agents have no `__init__(session_id)` parameter.

### Anti-Pattern 9: Not Handling Tool Errors

❌ **WRONG:**
```python
@self.agent.tool
async def risky_tool(ctx: RunContext, param: str) -> str:
    """Does risky operation."""
    result = await external_api_call(param)  # May fail!
    return result
```

✓ **RIGHT:**
```python
@self.agent.tool
async def risky_tool(ctx: RunContext, param: str) -> str:
    """Does risky operation with error handling."""
    try:
        result = await external_api_call(param)
        return result
    except Exception as e:
        error_msg = f"Error in risky_tool: {str(e)}"
        print(colored(error_msg, "red"))
        return error_msg  # Return error as string so LLM can handle it
```

**Why:** Tool failures should return error messages, not crash the agent.

### Anti-Pattern 10: Inconsistent Run Methods

❌ **WRONG:**
```python
def run(self, prompt: str):
    # ... saves context ...
    return agent_output

async def run_async(self, prompt: str):
    # ... forgot to save context!
    return agent_output
```

✓ **RIGHT:**
```python
def run(self, prompt: str):
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output

async def run_async(self, prompt: str):
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Why:** All run methods must have identical memory handling logic.

---

## Code Generation Guide (For AI Assistants)

When generating an orchestrator agent, follow these steps exactly:

### Step 1: Understand Requirements
- Identify what MCP servers are needed (web, filesystem, knowledge base?)
- Identify what sub-agents are needed (narrator, dialog creator, etc.?)
- Identify what custom tools are needed (what specialized tasks?)
- Determine if long-term memory is needed (user preferences?)

### Step 2: Create Directory Structure
```bash
mkdir -p src/agents/{agent_name}/prompts
mkdir -p src/agents/{agent_name}/config
```

### Step 3: Generate agent.py
1. Copy the [Default Implementation Pattern](#default-implementation-pattern) exactly
2. Replace all placeholders:
   - `{OrchestratorName}` → `YourAgentClassName`
   - `{orchestrator_id}` → `your_agent_id`
   - `{SubAgent}` → Actual sub-agent class names
   - `{sub_agent}` → Actual sub-agent module names
3. Add custom tools inside `__init__` after agent creation
4. Implement all three run methods: `run()`, `run_async()`, `run_stream()`

### Step 4: Generate config/mcp_config.json
1. Only include MCP servers the agent actually needs
2. Use correct port numbers from .env
3. Standard servers:
   - `web-search`: port 8000
   - `web-crawler`: port 8001
   - `filesystem`: port 8002
   - `knowledge-base`: port 8003

### Step 5: Generate prompts/system_prompt.md
Follow structure in [System Prompt Structure](#system-prompt-structure):
1. Persona section
2. Tools Available section (list all MCP and custom tools)
3. Task section
4. Instructions section
5. Workflow section
6. Constraints section
7. Output Format section

### Step 6: Generate __init__.py
```python
from .agent import {YourAgentClassName}

__all__ = ['{YourAgentClassName}']
```

### Step 7: Validate Against Checklist
Use the [Validation Checklist](#validation-checklist) below to verify correctness.

---

## Validation Checklist

**IMPORTANT:** Before validating, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

Before completing orchestrator agent implementation, verify:

### File Structure
- [ ] Directory created: `src/agents/{agent_name}/`
- [ ] `__init__.py` exists and exports agent class
- [ ] `agent.py` exists with complete implementation
- [ ] `prompts/system_prompt.md` exists
- [ ] `config/mcp_config.json` exists (if using MCP servers)

### Imports
- [ ] Import order correct: stdlib → third-party → pydantic_ai → local → sub-agents
- [ ] `load_dotenv()` at module level (not in class)
- [ ] All required imports present
- [ ] No unused imports

### Class Structure
- [ ] Class name is PascalCase
- [ ] `AGENT_ID` constant defined
- [ ] `AGENT_ID` matches directory name
- [ ] `__init__(session_id: str)` signature correct

### Model Configuration
- [ ] `llm_model = os.getenv('LLM_MODEL')` used directly
- [ ] NO f-string wrapping (no `f"openai:{model}"`)
- [ ] Model format is OpenRouter-compatible

### MCP Servers
- [ ] `load_mcp_servers(load_mcp_config(__file__))` used
- [ ] `config/mcp_config.json` exists
- [ ] Port numbers in config match .env
- [ ] `toolsets=servers` passed to Agent constructor
- [ ] Only necessary servers included

### Context Memory
- [ ] `save_context` and `load_context` imported
- [ ] Context loaded ONCE in `__init__`
- [ ] Context saved AFTER every run method
- [ ] `message_history=self.messages` passed to agent.run()
- [ ] `self.messages` updated with `agent_output.all_messages()`
- [ ] Context NOT loaded in run methods (anti-pattern)

### Long-term Memory
- [ ] `save_long_term_memory` and `load_long_term_memory` imported
- [ ] `_load_preferences()` method implemented
- [ ] Preferences appended to system prompt in `__init__`
- [ ] Preferences formatted as markdown list
- [ ] Empty check returns "" if no preferences

### Custom Tools
- [ ] Tools defined inside `__init__` with decorator
- [ ] All tools are `async def`
- [ ] All tools have `ctx: RunContext` first parameter
- [ ] Tool docstrings are clear and descriptive
- [ ] Tool logging uses `colored()` from termcolor
- [ ] Sub-agents initialized before tool definitions
- [ ] Error handling in tools (try/except)

### Sub-Agents
- [ ] Stateful sub-agents initialized with `session_id`
- [ ] Stateless sub-agents initialized without `session_id`
- [ ] Sub-agents initialized in `__init__`
- [ ] Sub-agent calls use `await`

### Run Methods
- [ ] `run(prompt: str) -> AgentRunResult` implemented (sync)
- [ ] `run_async(prompt: str) -> AgentRunResult` implemented
- [ ] `run_stream(prompt: str)` implemented (generator)
- [ ] All three methods save context identically
- [ ] All three methods pass `message_history`
- [ ] All three methods update `self.messages`

### System Prompt
- [ ] Loaded using `load_system_prompt(__file__)`
- [ ] Preferences appended: `system_prompt += self._load_preferences()`
- [ ] Includes Persona section
- [ ] Lists all available tools (MCP and custom)
- [ ] Includes clear task description
- [ ] Includes workflow steps
- [ ] Includes constraints

### __init__.py
- [ ] Imports agent class
- [ ] Uses `__all__` list
- [ ] Class name matches import

### Code Quality
- [ ] No inline imports
- [ ] No unnecessary comments
- [ ] Consistent indentation
- [ ] No debug print statements (except tool logging)
- [ ] Follows KISS principle

---

## Key Components Explained

### MCP Server Loading

```python
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

servers = load_mcp_servers(load_mcp_config(__file__))

self.agent = Agent(
    llm_model,
    system_prompt=system_prompt,
    toolsets=servers  # MCP tools automatically available
)
```

**What this does:**
- Loads MCP server configuration from `config/mcp_config.json`
- Connects to specified MCP servers
- Makes all MCP tools available to the agent
- Agent can call tools by name automatically

**Available MCP Tools (if configured):**
- `web_search(query)` - Search web and crawl results
- `crawl(url)` - Extract content from URL
- `search_guide_knowledge(query, top_k)` - Search knowledge base
- `read(path)`, `write(path, content)` - File operations
- (All tools from configured MCP servers)

### Both Memory Systems

**Context Memory (Short-term):**
```python
self.messages = load_context(self.AGENT_ID, session_id)
# ... after run ...
self.messages = agent_output.all_messages()
save_context(self.AGENT_ID, self.session_id, self.messages)
```

**Location:** `.mythline/{agent_id}/context_memory/{session_id}.json`
**Purpose:** Conversation history for this session

**Long-term Memory:**
```python
def _load_preferences(self) -> str:
    preferences = load_long_term_memory(self.AGENT_ID)
    if not preferences:
        return ""

    preferences_text = "\n\n##Memory:\n"
    for pref in preferences:
        preferences_text += f"- {pref['preference']}\n"

    return preferences_text
```

**Location:** `.mythline/{agent_id}/long_term_memory/memory.json`
**Purpose:** User preferences and facts that persist across all sessions

### Custom Tools with Sub-Agents

```python
self._sub_agent = NarratorAgent(session_id)

@self.agent.tool
async def create_narration(ctx: RunContext, reference_text: str, word_count: int) -> str:
    """Creates narrative text based on reference material."""
    print(colored(f"⚙ Calling Narrator", "grey"))

    prompt_template = load_prompt(__file__, "create_narration")
    prompt = prompt_template.format(word_count=word_count, reference_text=reference_text)

    response = await self._sub_agent.run(prompt)

    print(colored(f"⚙ Got narration: {len(response.output.text)} chars", "grey"))

    return response.output.text
```

**Tool Prompt Template:** `prompts/create_narration.md`

```markdown
Create narration of exactly {word_count} words based on this reference:

{reference_text}

Follow the established tone and style.
```

### Multiple Run Methods

**Synchronous (for CLI):**
```python
def run(self, prompt: str) -> AgentRunResult:
    agent_output = self.agent.run_sync(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Asynchronous (for web/graphs):**
```python
async def run_async(self, prompt: str) -> AgentRunResult:
    agent_output = await self.agent.run(prompt, message_history=self.messages)
    self.messages = agent_output.all_messages()
    save_context(self.AGENT_ID, self.session_id, self.messages)
    return agent_output
```

**Streaming (for real-time UI):**
```python
async def run_stream(self, prompt: str):
    async with self.agent.run_stream(prompt, message_history=self.messages) as result:
        async for chunk in result.stream_text(delta=True):
            yield chunk

        self.messages = result.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
```

## Real-World Example: Story Research Agent

**File:** `src/agents/story_research_agent/agent.py`

```python
import os

from dotenv import load_dotenv
from termcolor import colored

from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult
from pydantic_ai import Agent, RunContext

from src.libs.utils.prompt_loader import load_system_prompt, load_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory
from src.agents.narrator_agent.agent import NarratorAgent
from src.agents.dialog_creator_agent.agent import DialogCreatorAgent
from src.agents.user_preference_agent.agent import UserPreferenceAgent

load_dotenv()

class StoryResearcher:
    AGENT_ID = "story_researcher"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)
        system_prompt += self._load_preferences()

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )

        self._narrator_agent = NarratorAgent(session_id)
        self._dialog_agent = DialogCreatorAgent(session_id)
        self._user_preference_agent = UserPreferenceAgent()

        @self.agent.tool
        async def create_dialog(ctx: RunContext, reference_text: str, actors: list[str]) -> str:
            """Creates dialogue between characters based on reference text."""
            print(colored(f"⚙ Calling Dialog Creator", "grey"))

            prompt_template = load_prompt(__file__, "create_dialog")
            prompt = prompt_template.format(actors=actors, reference_text=reference_text)
            response = await self._dialog_agent.run(prompt)

            print(colored(f"\n⚙ Got dialog", "grey"))

            return response.output

        @self.agent.tool
        async def create_narration(ctx: RunContext, reference_text: str, word_count: int) -> str:
            """Creates narrative text based on reference material."""
            print(colored(f"⚙ Calling Narrator", "grey"))

            prompt_template = load_prompt(__file__, "create_narration")
            prompt = prompt_template.format(word_count=word_count, reference_text=reference_text)
            response = await self._narrator_agent.run(prompt)

            print(colored(f"\n⚙ Got narration", "grey"))

            return response.output

        @self.agent.tool
        async def save_user_preference(ctx: RunContext, user_message: str):
            """Identifies and saves user preferences for future sessions."""
            print(f"⚙ Identifying user's preference")

            prompt_template = load_prompt(__file__, "save_user_preference")
            prompt = prompt_template.format(user_message=user_message)
            response = await self._user_preference_agent.run(prompt)

            print(f"\n⚙ Got response: {response.output}")

            if response.output.lower().strip() != "none":
                save_long_term_memory(self.AGENT_ID, response.output)
                print(f"✓ Preference saved to long-term memory")

            return response.output

    def _load_preferences(self) -> str:
        preferences = load_long_term_memory(self.AGENT_ID)
        if not preferences:
            return ""

        preferences_text = "\n\n##Memory:\n"
        for pref in preferences:
            preferences_text += f"- {pref['preference']}\n"

        return preferences_text

    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output

    async def run_async(self, prompt: str) -> AgentRunResult:
        agent_output = await self.agent.run(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output

    async def run_stream(self, prompt: str):
        async with self.agent.run_stream(prompt, message_history=self.messages) as result:
            async for chunk in result.stream_text(delta=True):
                yield chunk

            self.messages = result.all_messages()
            save_context(self.AGENT_ID, self.session_id, self.messages)
```

**File:** `config/mcp_config.json`

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    },
    "web-crawler": {
      "url": "http://localhost:8001/mcp"
    },
    "knowledge-base": {
      "url": "http://localhost:8003/mcp"
    }
  }
}
```

## System Prompt Structure

**File:** `prompts/system_prompt.md`

```markdown
# Persona

You are [role and expertise description].

# Tools Available

You have access to these MCP tools:
- web_search(query): Search the web and return content from top results
- crawl(url): Extract content from a specific URL
- search_guide_knowledge(query, top_k): Search the knowledge base

You have access to these custom tools:
- create_narration(reference_text, word_count): Generate narrative text
- create_dialog(reference_text, actors): Generate character dialogue
- save_user_preference(user_message): Extract and save user preferences

# Task

Your primary task is [main responsibility].

# Instructions

1. [Step-by-step instructions]
2. Use web_search when you need current information
3. Use search_guide_knowledge for documented best practices
4. Use create_narration for storytelling sections
5. Use create_dialog for character conversations
6. Use save_user_preference when user expresses preferences

# Workflow

1. Understand user request
2. Research using MCP tools if needed
3. Delegate specialized tasks to sub-agents via custom tools
4. Synthesize final response
5. Track user preferences

# Constraints

- [Behavioral constraints]
- Always research before creating content
- Maintain consistency with established lore
- Save user preferences for future sessions

# Output Format

[Expected output structure and style]
```

## Tool Design Patterns

### Simple Sub-Agent Delegation

```python
self._sub_agent = SubAgent(session_id)

@self.agent.tool
async def use_sub_agent(ctx: RunContext, input: str) -> str:
    """Uses sub-agent for specialized task."""
    response = await self._sub_agent.run(input)
    return response.output
```

### Templated Sub-Agent Delegation

```python
@self.agent.tool
async def create_content(ctx: RunContext, topic: str, length: int) -> str:
    """Creates content with specific parameters."""
    prompt_template = load_prompt(__file__, "create_content")
    prompt = prompt_template.format(topic=topic, length=length)

    response = await self._content_agent.run(prompt)
    return response.output
```

### Conditional Long-term Memory

```python
@self.agent.tool
async def save_preference(ctx: RunContext, user_message: str) -> str:
    """Extracts and saves preferences."""
    response = await self._preference_agent.run(user_message)

    if response.output.lower().strip() != "none":
        save_long_term_memory(self.AGENT_ID, response.output)
        return f"Saved: {response.output}"

    return "No preference detected"
```

### Multi-Step Tool Logic

```python
@self.agent.tool
async def research_and_summarize(ctx: RunContext, topic: str) -> str:
    """Researches a topic and provides summary."""
    # Step 1: Search knowledge base
    kb_results = await ctx.deps.search_guide_knowledge(topic, top_k=5)

    # Step 2: If not enough info, search web
    if len(kb_results) < 100:
        web_results = await ctx.deps.web_search(topic)
        kb_results += "\n\n" + web_results

    # Step 3: Have sub-agent summarize
    summary = await self._summarizer.run(kb_results)

    return summary.output
```

## Best Practices

### Tool Logging

```python
from termcolor import colored

@self.agent.tool
async def create_narration(ctx: RunContext, reference_text: str, word_count: int) -> str:
    print(colored(f"⚙ Calling Narrator with {word_count} words", "grey"))

    response = await self._narrator_agent.run(...)

    print(colored(f"✓ Narration created: {len(response.output)} chars", "green"))

    return response.output
```

### Tool Parameter Validation

```python
@self.agent.tool
async def create_content(ctx: RunContext, word_count: int, topic: str) -> str:
    """Creates content with validation."""
    if word_count < 10 or word_count > 10000:
        return "Error: word_count must be between 10 and 10000"

    if not topic.strip():
        return "Error: topic cannot be empty"

    response = await self._content_agent.run(...)
    return response.output
```

### Error Handling in Tools

```python
@self.agent.tool
async def risky_operation(ctx: RunContext, param: str) -> str:
    """Handles errors gracefully."""
    try:
        result = await self._sub_agent.run(param)
        return result.output
    except Exception as e:
        error_msg = f"Error in risky_operation: {str(e)}"
        print(colored(error_msg, "red"))
        return error_msg
```

### Memory Management

```python
def _load_preferences(self) -> str:
    """Loads long-term memory and formats for system prompt."""
    preferences = load_long_term_memory(self.AGENT_ID)

    if not preferences:
        return ""

    # Format as markdown list
    preferences_text = "\n\n## User Preferences\n\n"
    for pref in preferences:
        preferences_text += f"- {pref['preference']}\n"

    return preferences_text
```

## Advanced Patterns

### Context History Summarization

```python
from src.libs.agent_memory.context_memory import summarize_context

self.agent = Agent(
    llm_model,
    system_prompt=system_prompt,
    toolsets=servers,
    history_processors=[summarize_context]  # Auto-summarize long conversations
)
```

### Conditional MCP Loading

```python
def __init__(self, session_id: str, use_web: bool = True):
    # ... setup ...

    if use_web:
        servers = load_mcp_servers(load_mcp_config(__file__))
    else:
        servers = []

    self.agent = Agent(llm_model, toolsets=servers, ...)
```

### Dynamic Tool Registration

```python
def __init__(self, session_id: str):
    # ... setup ...

    self.agent = Agent(...)

    # Conditionally register tools
    if self.has_feature("narration"):
        self._register_narration_tool()

    if self.has_feature("dialogue"):
        self._register_dialogue_tool()

def _register_narration_tool(self):
    self._narrator = NarratorAgent(self.session_id)

    @self.agent.tool
    async def create_narration(...):
        # Tool implementation
        pass
```

## Testing

### Unit Testing Tools

```python
import pytest
from src.agents.orchestrator_agent.agent import OrchestratorAgent

@pytest.mark.asyncio
async def test_tool_delegates_to_subagent():
    agent = OrchestratorAgent(session_id="test")

    # Access tool directly for testing
    result = await agent.create_narration(
        reference_text="Test reference",
        word_count=100
    )

    assert result
    assert len(result) > 0
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_workflow():
    agent = OrchestratorAgent(session_id="test_workflow")

    # Test multi-turn conversation
    result1 = await agent.run_async("Research Shadowglen")
    assert "Shadowglen" in result1.output

    result2 = await agent.run_async("Create a short story about it")
    assert len(result2.output) > 100
```

### MCP Server Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('pydantic_ai.mcp.load_mcp_servers')
async def test_without_mcp_servers(mock_load_servers):
    mock_load_servers.return_value = []

    agent = OrchestratorAgent(session_id="test_no_mcp")

    # Test agent works without MCP servers
    result = await agent.run_async("Hello")
    assert result.output
```

## Troubleshooting

### MCP Servers Not Available

**Issue:** Tools from MCP servers not working

**Solution:**
- Verify MCP servers are running (`start_web_search.bat`, etc.)
- Check `config/mcp_config.json` has correct URLs
- Ensure ports in config match `.env` settings
- Test MCP server directly: `curl http://localhost:8000/mcp`

### Tools Not Being Called

**Issue:** Agent doesn't use custom tools

**Solution:**
- Document tools clearly in system prompt
- Provide usage examples in system prompt
- Check tool docstrings are descriptive
- Test with explicit instruction to use tool

### Memory Not Persisting

**Issue:** Long-term memory not working across sessions

**Solution:**
- Verify `_load_preferences()` called in `__init__`
- Check `.mythline/{agent_id}/long_term_memory/` exists
- Ensure `save_long_term_memory()` called in tool
- Test memory loading: `load_long_term_memory(AGENT_ID)`

### Performance Issues

**Issue:** Agent runs slowly

**Solution:**
- Profile MCP server response times
- Check context memory size (summarize if needed)
- Consider reducing number of tools
- Use async consistently
- Monitor token usage

## File Checklist

When creating a new orchestrator agent:

- [ ] `__init__.py` - Export agent class
- [ ] `agent.py` - Full orchestrator implementation
- [ ] `prompts/system_prompt.md` - Comprehensive system prompt
- [ ] `prompts/{tool_name}.md` - Prompt templates for tools (optional)
- [ ] `config/mcp_config.json` - MCP server configuration
- [ ] Test file in `tests/agents/`
- [ ] Documentation in agent docstring
- [ ] CLI interface in `src/ui/cli/`
- [ ] Web interface in `src/ui/web/` (optional)

## Related Blueprints

- `agent_stateful_subagent.md` - Sub-agents with memory
- `agent_stateless_subagent.md` - Stateless sub-agents
- `../graphs/graph_with_agents.md` - Using orchestrators in graphs
- `../../mcps/mcp_base.md` - MCP server integration
- `../../interfaces/cli/interface_cli_interactive.md` - CLI interfaces
