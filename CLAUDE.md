# CLAUDE.md - AI Agent Development Guide

This document provides guidance for AI agents (like Claude) working on the Mythline codebase.

## Project Overview

Mythline is a multi-agent AI storytelling system built with Pydantic AI. The system creates World of Warcraft narratives using specialized agents that research lore, generate narration, create dialogue, and track user preferences.

## Architecture Principles

### Agent Design Pattern

All agents follow a consistent pattern defined in `PDs/pydantic_ai_coding_guide.md`:

**Standard Agent Structure:**
```
agent_name/
├── __init__.py
├── agent.py
├── prompts/
│   └── system_prompt.md
└── config/
    └── mcp_config.json (optional)
```

**Agent Class Pattern:**
- OOP design with class-based agents
- `AGENT_ID` constant for identification
- `__init__(session_id: str)` for stateful agents
- `run(prompt: str) -> AgentRunResult` method
- Context memory for coherent conversations

### Agent Types

**Orchestrator Agents (with MCP tools)**
- story_research_agent
- story_creator_agent
- shot_creator_agent
- Load MCP servers for external tools
- Have both context and long-term memory
- Delegate specialized tasks to sub-agents

**Sub-Agents (stateful)**
- narrator_agent
- dialog_creator_agent
- Have context memory for coherent output
- No MCP servers (lightweight)
- Focused single purpose

**Sub-Agents (stateless)**
- user_preference_agent
- No session_id or context memory
- Pure input/output transformation
- Used for analysis and extraction

## Memory System

### Context Memory

**Location:** `.mythline/{agent_id}/context_memory/{session_id}.json`

**Purpose:**
- Maintains conversation history per session
- Enables coherent multi-turn interactions
- Agent-specific namespaces

**Implementation:**
```python
from src.libs.agent_memory.context_memory import save_context, load_context

self.messages = load_context(self.AGENT_ID, session_id)
agent_output = self.agent.run_sync(prompt, message_history=self.messages)
self.messages = agent_output.all_messages()
save_context(self.AGENT_ID, self.session_id, self.messages)
```

### Long-term Memory

**Location:** `.mythline/{agent_id}/long_term_memory/memory.json`

**Purpose:**
- Cross-session preference storage
- User preference tracking
- Agent-specific memory

**Implementation:**
```python
from src.libs.agent_memory.long_term_memory import save_long_term_memory, load_long_term_memory

preferences = load_long_term_memory(self.AGENT_ID)
save_long_term_memory(self.AGENT_ID, preference_text)
```

## MCP Servers

### Available Servers

**mcp_web_search (port 8000)**
- Web search via DuckDuckGo
- Auto-crawls top 5 results
- Returns combined content

**mcp_web_crawler (port 8001)**
- URL content extraction
- Markdown conversion
- Single page crawling

**mcp_filesystem (port 8002)**
- File read/write operations
- Directory operations
- File existence checks

## External Service Libraries

### YouTube Uploader (`src/libs/youtube/`)

**Purpose:** Upload videos to YouTube with full metadata support

**Components:**
- `auth.py` - OAuth 2.0 authentication with token storage
- `uploader.py` - YouTubeUploader class following OBSController pattern

**Credential Storage:** `.mythline/youtube/credentials.json`

**Usage:**
```python
from src.libs.youtube import YouTubeUploader, VideoMetadata

uploader = YouTubeUploader()
success, error = uploader.connect()

metadata = VideoMetadata(
    title="My Video",
    description="Description",
    tags=["tag1", "tag2"],
    privacy_status="private"
)

success, video_id, error = uploader.upload(video_path, metadata)
```

### OBS Controller (`src/libs/obs/`)

**Purpose:** Control OBS Studio for screen recording

**Pattern:** Service controller with connect/disconnect and tuple returns

### Voice Recognition (`src/libs/voice/`)

**Purpose:** Voice command recognition for hands-free navigation

**Components:**
- `voice_recognizer.py` - Vosk-based speech recognition
- `voice_commands.py` - Command parsing and interpretation

### MCP Configuration

MCP servers are configured per agent in `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    },
    "web-crawler": {
      "url": "http://localhost:8001/mcp"
    },
    "filesystem": {
      "url": "http://localhost:8002/mcp"
    }
  }
}
```

## Coding Standards

### KISS Philosophy

**DO:**
- Keep code simple and readable
- Use OOP where appropriate
- Follow existing patterns
- Self-documenting code

**DON'T:**
- Add comments (code should be self-explanatory)
- Add unnecessary logging
- Use inline imports
- Add extra validation/verification
- Use emojis in code

### File Structure

**Imports:**
- All imports at the top
- Standard library first
- Third-party second
- Local imports last
- No inline imports

**String Formatting:**
```python
single_line = "Some value"

multi_line = """
    This is line 1
    This is line 2
"""
```

### Prompt Management

**System Prompts:**
- Stored in `prompts/system_prompt.md`
- Markdown format
- Sections: Persona, Task, Instructions, Constraints, Output

**Loading Prompts:**
```python
from src.libs.utils.prompt_loader import load_agent_prompt
system_prompt = load_agent_prompt(__file__)
```

## Development Workflow

### Git-flow

**Branch Structure:**
- `main` - Production code
- `develop` - Active development
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `release/*` - Releases
- `hotfix/*` - Emergency fixes

**Starting Work:**
```bash
git flow feature start feature-name
```

**Finishing Work:**
```bash
git flow feature finish feature-name
```

### Adding New Agents

**1. Create Agent Structure:**
```bash
mkdir -p src/agents/new_agent/{prompts,config}
```

**2. Create Files:**
- `__init__.py` - Export agent class
- `agent.py` - Agent implementation
- `prompts/system_prompt.md` - System prompt
- `config/mcp_config.json` - MCP config (if needed)

**3. Follow Pattern:**
- Use existing agents as templates
- Decide if stateful (context memory) or stateless
- Decide if needs MCP servers
- Implement `AGENT_ID`, `__init__`, and `run()` method

**4. Import Pattern:**
```python
from src.agents.new_agent import NewAgent
```

### Adding New MCP Servers

**1. Create Server Structure:**
```bash
mkdir -p src/mcp_servers/mcp_new_server
```

**2. Create Files:**
- `__init__.py`
- `server.py` - FastMCP server implementation

**3. Server Pattern:**
```python
from mcp.server.fastmcp import FastMCP

server = FastMCP(name="Server Name", port=port)

@server.tool()
async def tool_name(arg: type) -> return_type:
    pass

if __name__=='__main__':
    server.run(transport='streamable-http')
```

**4. Add Batch File:**
Create `start_new_server.bat` for easy startup.

## Common Tasks

### Testing Agents Locally

```bash
# Story research (interactive)
python -m src.ui.cli.research_story

# Story creation (non-interactive, requires --subject)
python -m src.ui.cli.create_story --subject shadowglen
```

### Voice Navigator

```bash
# Start voice-controlled shot navigation
python -m src.ui.cli.voice_navigator --subject shadowglen
```

### YouTube Upload

```bash
# Upload video with metadata
python -m src.ui.cli.upload_youtube video.mp4 -t "Title" -d "Description" --tags "tag1,tag2" -p public

# List categories and playlists
python -m src.ui.cli.upload_youtube --list-categories
python -m src.ui.cli.upload_youtube --list-playlists

# Clear stored credentials
python -m src.ui.cli.upload_youtube --logout
```

### Checking Memory

Context memory: `.mythline/{agent_id}/context_memory/`
Long-term memory: `.mythline/{agent_id}/long_term_memory/`

### Debugging

- Check MCP server status (should be running)
- Verify `.env` configuration
- Check session files in `.mythline/`
- Review agent system prompts

## Sub-Agent Integration

### When to Create Sub-Agents

**Create separate sub-agents when:**
- Task requires specialized expertise
- Output needs context memory for coherence
- Functionality is reusable across agents
- Complexity justifies separation

**Use inline tools when:**
- Simple, stateless operations
- One-off functionality
- Minimal code (< 10 lines)

### Calling Sub-Agents

```python
self._sub_agent = SubAgent(session_id)

@self.agent.tool
async def use_sub_agent(ctx: RunContext, input: str) -> str:
    response = self._sub_agent.run(input)
    return response.output
```

## Best Practices

1. **Follow Existing Patterns**: Use current agents as templates
2. **Keep It Simple**: Avoid over-engineering
3. **Session Awareness**: Most agents need session_id for context
4. **Prompt Quality**: Clear, structured prompts in markdown
5. **Memory Usage**: Context for coherence, long-term for preferences
6. **MCP Modularity**: Only load needed MCP servers
7. **Error Handling**: Let Pydantic AI handle most errors
8. **Testing**: Test with real interactions via CLI

## Reference Files

- `PDs/pydantic_ai_coding_guide.md` - Detailed coding patterns
- `src/agents/story_research_agent/agent.py` - Research orchestrator example
- `src/agents/story_creator_agent/agent.py` - Story orchestrator example
- `src/agents/shot_creator_agent/agent.py` - Simple agent example
- `src/agents/narrator_agent/agent.py` - Stateful sub-agent example
- `src/agents/user_preference_agent/agent.py` - Stateless sub-agent example

## Environment Variables

```
OPENROUTER_API_KEY=required
LLM_MODEL=openai/gpt-4o-mini (OpenRouter format: provider/model-name)
EMBEDDING_MODEL=openai/text-embedding-3-small (OpenRouter format for knowledge base embeddings)
MCP_WEB_SEARCH_PORT=8000
MCP_WEB_CRAWLER_PORT=8001
MCP_FILESYSTEM_PORT=8002
MCP_KNOWLEDGE_BASE_PORT=8003
QDRANT_PATH=.mythline/knowledge_base
PYTHONDONTWRITEBYTECODE=1
```

**Note:** All LLM and embedding operations use OpenRouter as the unified API provider.

## Quick Start for AI Agents

When working on Mythline:

1. Read this file first
2. Check `PDs/pydantic_ai_coding_guide.md` for patterns
3. Review similar existing agents
4. Follow KISS principles
5. No comments, keep code clean
6. Test via CLI before committing
7. Use git-flow for branches
8. Commit with clear messages

## Questions?

Check existing code first. The codebase is designed to be self-documenting.
