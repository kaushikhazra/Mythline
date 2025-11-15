# Orchestrator Agent Blueprint

This blueprint covers orchestrator agents that coordinate multiple tools, MCP servers, and sub-agents to accomplish complex tasks. These are the primary agents users interact with directly.

## Overview

Orchestrator agents:
- Load and use MCP servers for external tools
- Maintain full conversation context and long-term memory
- Delegate specialized tasks to sub-agents
- Provide custom tools for complex operations
- Handle multi-turn conversations with users
- Coordinate workflows and decision-making

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

## Implementation Pattern

### Complete Orchestrator Agent

**File:** `agent.py`

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

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
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

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
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
