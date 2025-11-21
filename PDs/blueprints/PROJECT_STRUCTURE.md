# Project Structure Blueprint

**Purpose:** Single source of truth for a Pydantic AI multi-agent system's directory structure, file organization, and architectural layout.

**For:** Developers understanding where code lives and how to organize new components.

---

## Table of Contents

- [Overview](#overview)
- [Top-Level Structure](#top-level-structure)
- [Source Code Organization](#source-code-organization)
- [Configuration Files](#configuration-files)
- [Runtime Data](#runtime-data)
- [File Naming Conventions](#file-naming-conventions)
- [Where to Put New Code](#where-to-put-new-code)

---

## Overview

This architecture follows a **feature-based organization** where related code is grouped by functionality:

- **Agents** - AI agents with specific responsibilities
- **Graphs** - Multi-agent workflow orchestration
- **Libraries** - Reusable utility code
- **MCP Servers** - Tool servers for agents
- **UI** - User interfaces (CLI and web)

**Design Principles:**
- Each component is self-contained with its own dependencies
- Clear separation between orchestrators (with MCP) and workers (lightweight)
- Configuration lives with code (prompts, MCP configs)
- Runtime data separate from source code

---

## Top-Level Structure

```
project_root/
├── src/                          # All source code
│   ├── agents/                   # AI agents
│   ├── graphs/                   # LangGraph workflows
│   ├── libs/                     # Shared libraries
│   ├── mcp_servers/              # MCP tool servers
│   └── ui/                       # User interfaces
│
├── PDs/                          # Product Documents
│   ├── blueprints/               # Code blueprints (this file)
│   └── guides/                   # Development guides
│
├── docs/                         # Design documents
│   ├── design_*.md               # Feature design docs
│   └── architecture/             # Architecture decisions
│
├── tests/                        # Test suite
│   ├── agents/                   # Agent tests
│   ├── graphs/                   # Graph tests
│   └── libs/                     # Library tests
│
├── .{project_name}/              # Runtime data (gitignored)
│   ├── {agent_id}/               # Agent-specific data
│   └── knowledge_base/           # Vector database (optional)
│
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
└── start_*.bat                   # MCP server launchers
```

---

## Source Code Organization

### Agents (`src/agents/`)

AI agents that perform specific tasks. Each agent is a self-contained module.

```
src/agents/{agent_name}/
├── __init__.py                   # Exports agent class
├── agent.py                      # Main agent implementation
├── prompts/
│   ├── system_prompt.md          # Agent's system prompt
│   └── {tool_name}.md            # Tool-specific prompts (optional)
├── config/
│   └── mcp_config.json           # MCP servers (orchestrators only)
└── models/                       # Pydantic models (optional)
    ├── __init__.py
    ├── state_models.py           # Graph state models
    └── output_models.py          # Structured outputs
```

**Current Agents:**
- `chunker_agent` - Text chunking
- `dialog_creator_agent` - Dialogue generation
- `narrator_agent` - Narrative creation
- `quality_assessor` - Content quality assessment
- `shot_creator_agent` - Shot generation
- `story_creator_agent` - Story orchestration
- `story_planner_agent` - Story planning
- `story_research_agent` - Lore research
- `user_preference_agent` - Preference extraction
- `video_director_agent` - Video direction
- `llm_tester_agent` - LLM testing

**Types:**
- **Orchestrators** - Have MCP servers, coordinate workflows (e.g., `story_research_agent`)
- **Stateful Sub-agents** - Have context memory (e.g., `narrator_agent`)
- **Stateless Sub-agents** - Pure input/output (e.g., `user_preference_agent`)

### Graphs (`src/graphs/`)

LangGraph-based multi-agent workflows.

```
src/graphs/{graph_name}/
├── __init__.py                   # Exports graph
├── graph.py                      # Graph definition
├── nodes.py                      # Node implementations
└── models/                       # State models (optional)
    └── state_models.py
```

**Current Graphs:**
- `audio_generator_graph` - Audio generation workflow
- `shot_creator_graph` - Shot creation workflow
- `story_creator_graph` - Story creation workflow

**Purpose:** Coordinate multiple agents in complex workflows with state management.

### Libraries (`src/libs/`)

Reusable utilities organized by function.

```
src/libs/
├── agent_memory/                 # Context and long-term memory
│   ├── context_memory.py         # Session-based memory
│   └── long_term_memory.py       # Cross-session preferences
│
├── audio/                        # Audio generation
│   ├── cartesia_tts.py           # Cartesia TTS integration
│   └── chatterbox_utils.py       # Audio utilities
│
├── embedding/                    # Text embeddings
│   └── openai_embeddings.py      # OpenRouter embeddings
│
├── filesystem/                   # File operations
│   ├── directory_operations.py
│   └── file_operations.py
│
├── knowledge_base/               # Vector database
│   └── knowledge_vectordb.py     # Qdrant operations
│
├── parsers/                      # Content parsing
│   └── markdown_parser.py        # Markdown utilities
│
├── utils/                        # General utilities
│   ├── argument_parser.py        # CLI argument handling
│   ├── config_loader.py          # MCP config loading
│   └── prompt_loader.py          # Prompt file loading
│
└── web/                          # Web utilities
    ├── web_crawler.py            # URL content extraction
    └── web_search.py             # DuckDuckGo search
```

**Design Principle:** Libraries are stateless utilities that can be imported anywhere.

### MCP Servers (`src/mcp_servers/`)

FastMCP servers that expose tools to agents.

```
src/mcp_servers/mcp_{server_name}/
├── __init__.py                   # Exports server
└── server.py                     # Server implementation

# At project root:
start_{server_name}.bat           # Server launcher
```

**Current Servers:**
- `mcp_filesystem` (port 8002) - File/directory operations
- `mcp_knowledge_base` (port 8003) - Vector search
- `mcp_web_crawler` (port 8001) - URL content extraction
- `mcp_web_search` (port 8000) - Web search + crawling

**Ports:** Defined in `.env` as `MCP_{SERVER}_PORT`

### User Interfaces (`src/ui/`)

```
src/ui/
├── cli/                          # Command-line interfaces
│   ├── create_story.py           # Story creation CLI
│   ├── research_story.py         # Research CLI
│   └── ...
│
└── web/                          # Web interface (future)
    ├── backend/
    └── frontend/
```

**CLI Pattern:** Each CLI is a standalone script using argparse.

---

## Configuration Files

### Environment Variables

**File:** `.env` (gitignored, use `.env.example` as template)

See [ENVIRONMENT.md](ENVIRONMENT.md) for complete reference.

### Agent Configuration

**Prompts:** `src/agents/{agent_name}/prompts/*.md`
- Markdown format
- Loaded via `load_system_prompt(__file__)`

**MCP Servers:** `src/agents/{agent_name}/config/mcp_config.json`
- JSON format
- Only for orchestrator agents
- Loaded via `load_mcp_config(__file__)`

### Project Configuration

**Dependencies:** `requirements.txt`
**Git:** `.gitignore`
**Python:** `.python-version` (if using pyenv)

---

## Runtime Data

All runtime data lives in `.mythline/` (gitignored):

```
.mythline/
├── {agent_id}/                   # Per-agent data
│   ├── context_memory/           # Session conversations
│   │   └── {session_id}.json
│   └── long_term_memory/         # Cross-session data
│       └── memory.json
│
└── knowledge_base/               # Vector database
    └── qdrant_storage/           # Qdrant data
```

**Created automatically** - No need to create these directories manually.

---

## File Naming Conventions

### Python Files

- **Modules:** `snake_case.py`
- **Classes:** `PascalCase` (e.g., `StoryResearchAgent`)
- **Functions:** `snake_case()`
- **Constants:** `UPPER_SNAKE_CASE`

### Markdown Files

- **Blueprints:** `snake_case.md` or `UPPER_CASE.md`
- **Design docs:** `design_{feature}.md`
- **Prompts:** `system_prompt.md`, `{tool_name}.md`

### Directories

- **All lowercase:** `agent_name`, `lib_name`
- **Underscores:** For multi-word names
- **Prefix for namespacing:** `mcp_{name}` for MCP servers

### Batch Files

- **Format:** `start_{server_name}.bat`
- **Location:** Project root
- **Purpose:** MCP server launchers

---

## Where to Put New Code

### Adding a New Agent

```
1. Create directory: src/agents/{agent_name}/
2. Add files:
   - __init__.py
   - agent.py
   - prompts/system_prompt.md
   - config/mcp_config.json (if orchestrator)
   - models/ (if using structured output)
3. Follow blueprint: PDs/blueprints/pydantic/agents/
```

### Adding a New Graph

```
1. Create directory: src/graphs/{graph_name}/
2. Add files:
   - __init__.py
   - graph.py
   - nodes.py
   - models/state_models.py (if needed)
3. Follow blueprint: PDs/blueprints/pydantic/graphs/
```

### Adding a New Library

```
1. Add to appropriate src/libs/ subdirectory
2. If new category, create: src/libs/{category}/
3. Follow blueprint: PDs/blueprints/libs/
4. Update libs/INDEX.md
```

### Adding a New MCP Server

```
1. Create directory: src/mcp_servers/mcp_{name}/
2. Add files:
   - __init__.py
   - server.py
3. Create launcher: start_{name}.bat (at project root)
4. Add port to .env: MCP_{NAME}_PORT
5. Follow blueprint: PDs/blueprints/mcps/
```

### Adding a New CLI Interface

```
1. Create file: src/ui/cli/{command}.py
2. Follow blueprint: PDs/blueprints/interfaces/cli/
```

---

## Import Conventions

### Absolute Imports (Preferred)

```python
from src.agents.narrator_agent import NarratorAgent
from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.agent_memory.context_memory import load_context
```

### Standard Library First

```python
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_ai import Agent

from src.agents.narrator_agent import NarratorAgent
from src.libs.utils.prompt_loader import load_system_prompt
```

**Order:**
1. Standard library
2. Third-party packages
3. Local imports (src.*)

---

## Architecture Patterns

### Agent Pattern

**Single Responsibility:** Each agent has one clear purpose
**Composition:** Orchestrators delegate to sub-agents
**Isolation:** Agents don't directly call other agents (use tools)

### Graph Pattern

**State-Based:** All data flows through state
**Node Functions:** Pure functions that transform state
**Agent Integration:** Nodes can instantiate and use agents

### Library Pattern

**Stateless:** Libraries don't maintain state
**Pure Functions:** Predictable input/output
**Reusable:** Can be used anywhere in the project

### MCP Pattern

**Tool Server:** Exposes capabilities to agents
**Stateless:** No session management
**Async:** All tools are async for performance

---

## Quick Reference

| I want to...                    | Go to...                              | Blueprint                          |
|---------------------------------|---------------------------------------|------------------------------------|
| Create a new agent              | `src/agents/{name}/`                  | `pydantic/agents/`                 |
| Create a workflow               | `src/graphs/{name}/`                  | `pydantic/graphs/`                 |
| Add a utility function          | `src/libs/{category}/`                | `libs/`                            |
| Create MCP server               | `src/mcp_servers/mcp_{name}/`         | `mcps/`                            |
| Add CLI command                 | `src/ui/cli/`                         | `interfaces/cli/`                  |
| Configure environment           | `.env`                                | `ENVIRONMENT.md`                   |
| Understand the project          | This file!                            | `PROJECT_STRUCTURE.md`             |

---

## Related Blueprints

- **[ENVIRONMENT.md](ENVIRONMENT.md)** - All environment variables
- **[INDEX.md](INDEX.md)** - Master blueprint navigation
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Setup guide
- **[CLAUDE.md](../../CLAUDE.md)** - Development guidelines

---

## Notes

**This structure is established** - Follow existing patterns when adding new code.

**Don't fight the structure** - If something doesn't fit, discuss architectural changes first.

**Keep it organized** - Each component in its proper place makes the codebase maintainable.
