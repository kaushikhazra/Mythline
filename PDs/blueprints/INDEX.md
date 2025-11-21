# Pydantic AI Multi-Agent System - Blueprint Library

**Welcome to the Blueprint Library!**

This is your comprehensive guide to building multi-agent AI systems using Pydantic AI, LangGraph, and FastMCP. Whether you're creating new agents, adding features, or understanding the architecture, start here.

---

## 🚀 Quick Navigation

**New to this architecture?**
1. Read [GETTING_STARTED.md](GETTING_STARTED.md) - Setup and first steps
2. Review [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Understand the layout
3. Check [ENVIRONMENT.md](ENVIRONMENT.md) - Configure your environment
4. Pick a blueprint below and start building!

**Need something specific?**
- Jump to [Quick Reference](#quick-reference) for common tasks
- Use [Blueprint Directory](#blueprint-directory) to find what you need
- See [Architecture Overview](#architecture-overview) for the big picture

---

## 📋 Core Documentation

These blueprints provide foundational knowledge for the entire project:

### [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
**Single source of truth for project organization**
- Complete directory structure
- Where to put new code
- File naming conventions
- Import patterns

### [ENVIRONMENT.md](ENVIRONMENT.md)
**All environment variables in one place**
- Required vs optional variables
- Configuration for LLM, MCP, and knowledge base
- Security best practices
- Troubleshooting

### [GETTING_STARTED.md](GETTING_STARTED.md)
**Setup guide for new developers**
- Installation steps
- First agent creation
- Testing your setup
- Common pitfalls

### [ROOT_STRUCTURE.md](ROOT_STRUCTURE.md)
**Guidelines for organizing the project root directory**
- What files belong in root vs subdirectories
- Runtime artifacts and batch files
- Decision tree for file placement
- Best practices for clean root

---

## 🎯 Core Coding Principles

**CRITICAL:** All code generated using these blueprints MUST follow these three principles:

### 1. Separation of Concerns (SoC)

**Principle:** Each module, class, or function should have a single, well-defined responsibility.

✓ **RIGHT:**
```python
# Agent delegates to specialized sub-agents
class StoryCreator:
    def __init__(self, session_id: str):
        self._narrator = NarratorAgent(session_id)  # Narration concern
        self._dialog_creator = DialogCreatorAgent(session_id)  # Dialog concern

# Complex logic in separate library
from src.libs.audio.processor import process_audio_file

@server.tool()
async def convert_audio(file_path: str) -> str:
    return await process_audio_file(file_path)  # Delegates to library
```

❌ **WRONG:**
```python
# Everything in one class
class StoryCreator:
    def create_story(self, prompt: str):
        # Research lore (mixing concerns)
        lore = self._search_web(prompt)

        # Generate narration (mixing concerns)
        narration = self._create_narration(lore)

        # Create dialog (mixing concerns)
        dialog = self._create_dialog(lore)

        # 500 lines of mixed logic...
```

**Apply this to:**
- Agents → Use sub-agents for specialized tasks
- MCP Tools → Delegate complex logic to libraries
- Graphs → Separate nodes handle specific steps
- Libraries → Each module has one clear purpose

---

### 2. KISS Principle (Keep It Simple, Stupid)

**Principle:** Code should be as simple as possible to solve the problem. No over-engineering.

✓ **RIGHT:**
```python
# Simple, clear, direct
def load_context(agent_id: str, session_id: str) -> list:
    context_path = f".mythline/{agent_id}/context_memory/{session_id}.json"
    if os.path.exists(context_path):
        with open(context_path, 'r') as f:
            return json.load(f)
    return []
```

❌ **WRONG:**
```python
# Over-engineered abstraction
class ContextMemoryManager:
    def __init__(self, storage_backend: StorageBackend):
        self.backend = storage_backend
        self.cache = LRUCache(maxsize=100)
        self.serializer = JSONSerializer()

    def load_with_retry_and_fallback(self, agent_id: str, session_id: str,
                                      max_retries: int = 3,
                                      fallback_strategy: FallbackStrategy = None):
        # 100 lines of unnecessary complexity...
```

**Apply this to:**
- Use OOP only where it adds clarity
- No unnecessary abstractions or design patterns
- Direct solutions over clever solutions
- Readable code over "smart" code

---

### 3. No Comments (Until Code is Tested and Stable)

**Principle:** Write self-documenting code. Add comments only AFTER the code is completely tested and stable.

**Why this rule:**
1. Comments become outdated when code changes during development
2. Maintaining comments during rapid iteration is inefficient
3. Self-documenting code (clear names, simple logic) is better than comments
4. Comments should explain "why", not "what" - only needed after code stabilizes

✓ **RIGHT - Self-documenting code:**
```python
def save_context(agent_id: str, session_id: str, messages: list):
    context_dir = f".mythline/{agent_id}/context_memory"
    os.makedirs(context_dir, exist_ok=True)

    context_path = f"{context_dir}/{session_id}.json"

    with open(context_path, 'w') as f:
        json.dump(messages, f, indent=2)
```

❌ **WRONG - Premature commenting:**
```python
def save_context(agent_id: str, session_id: str, messages: list):
    # Create the context directory for the agent
    context_dir = f".mythline/{agent_id}/context_memory"

    # Make the directory if it doesn't exist
    os.makedirs(context_dir, exist_ok=True)

    # Build the full path to the context file
    context_path = f"{context_dir}/{session_id}.json"

    # Write the messages to the JSON file with indentation
    with open(context_path, 'w') as f:
        json.dump(messages, f, indent=2)
```

**When to add comments (AFTER testing):**
- Complex business logic that isn't obvious
- Non-intuitive algorithms or workarounds
- Important architectural decisions
- Warning about gotchas or edge cases

**Example of good comment (after code is stable):**
```python
def _load_preferences(self) -> str:
    preferences = load_long_term_memory(self.AGENT_ID)
    if not preferences:
        return ""

    # Preferences are appended to system prompt so agent remembers
    # user preferences across all sessions (cross-session memory)
    preferences_text = "\n\n##Memory:\n"
    for pref in preferences:
        preferences_text += f"- {pref['preference']}\n"

    return preferences_text
```

---

## 📐 How These Principles Work Together

```python
# Good example: All three principles applied

# 1. Separation of Concerns: Audio processing in separate library
from src.libs.audio.chatterbox_utils import generate_audio_cartesia

# 2. KISS: Simple, direct tool implementation
@server.tool()
async def generate_speech(text: str, voice_id: str) -> str:
    output_path = f".mythline/audio/{uuid.uuid4()}.mp3"

    # 3. No comments: Self-documenting names and simple logic
    await generate_audio_cartesia(
        text=text,
        voice_id=voice_id,
        output_path=output_path
    )

    return output_path
```

**Remember:**
- **Separate concerns** → Use agents, sub-agents, libraries, and MCP servers appropriately
- **Keep it simple** → Direct solutions, no over-engineering
- **No comments** → Until code is tested and stable, then add "why" not "what"

---

## 🏗️ Architecture Overview

This multi-agent system architecture is built on these core components:

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│                  (CLI, Web - Future)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Graph Orchestration                      │
│              (LangGraph Workflows)                       │
└────┬───────────────────────────────────────────┬────────┘
     │                                           │
┌────▼────────────────────┐         ┌───────────▼─────────┐
│  Orchestrator Agents    │         │   Sub-Agents        │
│  (With MCP Servers)     │────────▶│   (Lightweight)     │
└────┬────────────────────┘         └─────────────────────┘
     │
┌────▼────────────────────────────────────────────────────┐
│                  MCP Tool Servers                        │
│        (Web, Files, Knowledge Base, etc.)                │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Utility Libraries                         │
│    (Memory, Embeddings, Parsing, etc.)                   │
└─────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Separation of Concerns** - Each component has a clear role
- **Composability** - Agents use other agents and tools
- **Configurability** - Behavior controlled via prompts and config
- **Statelessness** - Libraries are pure functions

---

## 📚 Blueprint Directory

### Pydantic AI Components

#### Agents
Build AI agents with specific capabilities.

**[pydantic/agents/agent_orchestrator.md](pydantic/agents/agent_orchestrator.md)**
- Full-featured agents with MCP servers
- Coordinate multiple tools and sub-agents
- Maintain conversation context and preferences
- Use cases: Research, content creation, complex workflows

**[pydantic/agents/agent_stateful_subagent.md](pydantic/agents/agent_stateful_subagent.md)**
- Agents with conversation memory
- Coherent multi-turn interactions
- No MCP servers (lightweight)
- Use cases: Content generation, dialog creation, summarization

**[pydantic/agents/agent_stateless_subagent.md](pydantic/agents/agent_stateless_subagent.md)**
- Pure input-output transformations
- No memory, fast and simple
- Analysis and extraction tasks
- Use cases: Data extraction, classification, validation

#### Graphs
Orchestrate multi-agent workflows with state management.

**[pydantic/graphs/graph_base.md](pydantic/graphs/graph_base.md)**
- Basic LangGraph structure
- State models and nodes
- Conditional routing

**[pydantic/graphs/graph_stateful.md](pydantic/graphs/graph_stateful.md)**
- Graphs with persistent state
- Session management
- Complex workflows

**[pydantic/graphs/graph_with_agents.md](pydantic/graphs/graph_with_agents.md)**
- Integrating agents into graphs
- Agent nodes and state passing
- Examples: StoryCreatorGraph, ShotCreatorGraph

#### Prompts
Craft effective prompts for agents.

**[pydantic/prompts/prompt_engineering.md](pydantic/prompts/prompt_engineering.md)**
- Prompt structure and best practices
- Tool descriptions
- Output formatting
- Examples from production agents

### MCP Servers
Create tool servers that agents can use.

**[mcps/mcp_base.md](mcps/mcp_base.md)**
- FastMCP server basics
- Tool registration
- Port management
- Testing servers

**[mcps/web/mcp_web_search.md](mcps/web/mcp_web_search.md)**
- Web search with DuckDuckGo
- Auto-crawl top results
- Example: Web research capability

**[mcps/web/mcp_web_crawler.md](mcps/web/mcp_web_crawler.md)**
- Extract content from URLs
- Markdown conversion
- Example: Fetch specific pages

**[mcps/filesystem/mcp_filesystem.md](mcps/filesystem/mcp_filesystem.md)**
- File and directory operations
- Read, write, append, delete
- Example: Story persistence

**[mcps/knowledge_base/mcp_knowledge_base.md](mcps/knowledge_base/mcp_knowledge_base.md)**
- Vector search in knowledge bases
- Semantic document retrieval
- Example: Lore research

### Libraries
Reusable utility code for common tasks.

**[libs/INDEX.md](libs/INDEX.md)** - Complete library reference

**Core Libraries:**
- **[libs/agent_memory/context_memory.md](libs/agent_memory/context_memory.md)** - Session-based conversation history
- **[libs/agent_memory/long_term_memory.md](libs/agent_memory/long_term_memory.md)** - Cross-session preferences
- **[libs/embedding/openai_embeddings.md](libs/embedding/openai_embeddings.md)** - Text vectorization
- **[libs/knowledge_base/knowledge_vectordb.md](libs/knowledge_base/knowledge_vectordb.md)** - Vector database operations
- **[libs/utils/prompt_loader.md](libs/utils/prompt_loader.md)** - Load prompts from markdown
- **[libs/utils/config_loader.md](libs/utils/config_loader.md)** - Load MCP configurations
- **[libs/web/web_search.md](libs/web/web_search.md)** - DuckDuckGo search
- **[libs/web/web_crawler.md](libs/web/web_crawler.md)** - URL content extraction

**[libs/COMMON.md](libs/COMMON.md)** - Shared patterns across all libraries

### Interfaces
User-facing interfaces for interacting with the system.

**[interfaces/web/INDEX.md](interfaces/web/INDEX.md)** - Web interface reference (future)

**CLI Interfaces:**
- **[interfaces/cli/interface_cli_interactive.md](interfaces/cli/interface_cli_interactive.md)** - Interactive CLI sessions
- **[interfaces/cli/interface_cli_batch.md](interfaces/cli/interface_cli_batch.md)** - Non-interactive batch processing
- **[interfaces/cli/interface_cli_common.md](interfaces/cli/interface_cli_common.md)** - Shared CLI patterns

---

## 🎯 Quick Reference

**I want to...**

### Create Components
| Task                              | Blueprint                                | Quick Start                           |
|-----------------------------------|------------------------------------------|---------------------------------------|
| Build a research agent            | pydantic/agents/agent_orchestrator.md    | Copy StoryResearchAgent structure     |
| Create a focused sub-agent        | pydantic/agents/agent_stateful_subagent.md | Copy NarratorAgent structure        |
| Add quick analysis agent          | pydantic/agents/agent_stateless_subagent.md | Copy UserPreferenceAgent           |
| Build multi-agent workflow        | pydantic/graphs/graph_with_agents.md     | Copy StoryCreatorGraph                |
| Add tool server                   | mcps/mcp_base.md                         | Copy mcp_web_search structure         |
| Create CLI command                | interfaces/cli/interface_cli_interactive.md | Copy research_story.py             |

### Work with Data
| Task                              | Blueprint                                | Key Functions                         |
|-----------------------------------|------------------------------------------|---------------------------------------|
| Save conversation history         | libs/agent_memory/context_memory.md      | save_context(), load_context()        |
| Store user preferences            | libs/agent_memory/long_term_memory.md    | save_long_term_memory()               |
| Generate embeddings               | libs/embedding/openai_embeddings.md      | generate_embedding()                  |
| Search knowledge base             | libs/knowledge_base/knowledge_vectordb.md | search_knowledge()                   |
| Search the web                    | libs/web/web_search.md                   | search_web()                          |
| Crawl a URL                       | libs/web/web_crawler.md                  | crawl_url()                           |

### Configure & Setup
| Task                              | Reference                                | Section                               |
|-----------------------------------|------------------------------------------|---------------------------------------|
| Set up environment                | ENVIRONMENT.md                           | Quick Start                           |
| Configure API keys                | ENVIRONMENT.md                           | Required Variables                    |
| Change LLM model                  | ENVIRONMENT.md                           | LLM Configuration                     |
| Add MCP server                    | ENVIRONMENT.md                           | MCP Server Ports                      |
| Understand project structure      | PROJECT_STRUCTURE.md                     | Full document                         |

---

## 🔍 Finding What You Need

### By Component Type

**Building Agents?** → `pydantic/agents/`
- Start with agent type (orchestrator, stateful, stateless)
- Check examples in each blueprint
- Review prompt engineering guide

**Creating Workflows?** → `pydantic/graphs/`
- Understand state models first
- See agent integration patterns
- Study existing graphs

**Adding Tools?** → `mcps/`
- Start with mcp_base.md
- Pick similar existing server as template
- Follow port and config conventions

**Writing Utilities?** → `libs/`
- Check if functionality exists in libs/INDEX.md
- Follow patterns in libs/COMMON.md
- Keep libraries stateless

**Building UI?** → `interfaces/`
- CLI for command-line tools
- Web for future web interface

### By Task

**Research & Planning**
- Web search: `mcps/web/mcp_web_search.md`
- Knowledge base: `mcps/knowledge_base/mcp_knowledge_base.md`
- Orchestrator: `pydantic/agents/agent_orchestrator.md`

**Content Generation**
- Narration: `pydantic/agents/agent_stateful_subagent.md`
- Dialogue: `pydantic/agents/agent_stateful_subagent.md`
- Structured output: See agent blueprints' Pydantic models section

**Memory & State**
- Conversation: `libs/agent_memory/context_memory.md`
- Preferences: `libs/agent_memory/long_term_memory.md`
- Workflow state: `pydantic/graphs/graph_stateful.md`

**Integration & Tools**
- MCP servers: `mcps/mcp_base.md`
- Agent tools: `pydantic/agents/agent_orchestrator.md` (custom tools section)
- External APIs: Create MCP server or library

---

## 📖 Learning Path

### For New Developers

**Week 1: Foundations**
1. Read GETTING_STARTED.md - Set up environment
2. Read PROJECT_STRUCTURE.md - Understand layout
3. Read ENVIRONMENT.md - Configure properly
4. Study one simple agent (UserPreferenceAgent)

**Week 2: Building Blocks**
5. Read pydantic/agents/agent_stateless_subagent.md
6. Create your own stateless agent
7. Read libs/COMMON.md - Understand utilities
8. Read pydantic/prompts/prompt_engineering.md

**Week 3: Advanced Agents**
9. Read pydantic/agents/agent_stateful_subagent.md
10. Study NarratorAgent implementation
11. Read libs/agent_memory/context_memory.md
12. Create a stateful agent

**Week 4: Orchestration**
13. Read pydantic/agents/agent_orchestrator.md
14. Read mcps/mcp_base.md
15. Study StoryResearchAgent
16. Create orchestrator with MCP servers

**Week 5: Workflows**
17. Read pydantic/graphs/graph_base.md
18. Read pydantic/graphs/graph_with_agents.md
19. Study StoryCreatorGraph
20. Build your own workflow

### For AI/Claude

When helping users:
1. Always reference relevant blueprints
2. Follow established patterns exactly
3. Update blueprints when patterns change
4. Keep examples consistent with codebase

---

## 🔧 Blueprint Maintenance

### Keeping Blueprints Updated

**When to update blueprints:**
- Adding new patterns or components
- Changing project structure
- Updating dependencies or APIs
- Discovering better practices

**How to update:**
1. Identify affected blueprints
2. Update examples and patterns
3. Check cross-references
4. Update this INDEX.md if needed

**Consistency checklist:**
- [ ] Examples use current import paths
- [ ] Environment variables match ENVIRONMENT.md
- [ ] Structure matches PROJECT_STRUCTURE.md
- [ ] Code follows current patterns
- [ ] Cross-references are valid

---

## 🌟 Blueprint Philosophy

**Blueprints should be:**
- **Practical** - Real examples, not theory
- **Complete** - Everything you need to implement
- **Consistent** - Follow same structure and style
- **Updated** - Reflect current codebase state
- **Discoverable** - Easy to find what you need

**Blueprints are NOT:**
- API documentation (use docstrings)
- Tutorials (use guides in docs/)
- Design docs (use docs/design_*.md)

**Think of blueprints as:**
- Construction plans for code
- Templates to copy and modify
- Reference for established patterns

---

## 📝 Related Documentation

**In this directory:**
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project organization
- [ENVIRONMENT.md](ENVIRONMENT.md) - Configuration reference
- [GETTING_STARTED.md](GETTING_STARTED.md) - Setup guide

**Elsewhere in project:**
- [../../CLAUDE.md](../../CLAUDE.md) - Development guidelines for AI
- [../../docs/](../../docs/) - Design documents
- [../../PDs/guides/](../guides/) - Development guides

**External:**
- [Pydantic AI Docs](https://ai.pydantic.dev/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [FastMCP Docs](https://github.com/jlowin/fastmcp)
- [OpenRouter Docs](https://openrouter.ai/docs)

---

## 💡 Tips for Using Blueprints

**Before you code:**
1. Check if a blueprint exists for what you're building
2. Read the blueprint completely
3. Study the real example in the codebase
4. Adapt the pattern to your needs

**While coding:**
1. Keep blueprint open for reference
2. Follow the established structure
3. Use same naming conventions
4. Copy patterns, don't reinvent

**After coding:**
1. Compare your code to blueprint examples
2. Update blueprints if you found better patterns
3. Document any deviations in comments

**Remember:**
- Blueprints save time - use them!
- Consistency matters - follow them!
- Blueprints evolve - update them!

---

## 🤝 Contributing to Blueprints

**Found an issue?**
- Outdated example: Update the blueprint
- Missing pattern: Add a new section
- Unclear explanation: Improve the docs

**Adding a new blueprint?**
1. Follow existing blueprint structure
2. Include practical examples
3. Cross-reference related blueprints
4. Update this INDEX.md

**Blueprint structure:**
```markdown
# [Component] Blueprint

**Purpose:** One-line description

**For:** Target audience

## Overview
High-level explanation

## Implementation Pattern
Code examples

## Key Components
Detailed explanations

## Usage
How to use it

## Examples
Real-world cases

## Related Blueprints
Cross-references
```

---

**Happy building! 🚀**

*This index is your starting point. Dive into specific blueprints as needed, and don't hesitate to update them when you discover improvements.*
