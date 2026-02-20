# Library Blueprint - Index

This is the master index for library modules in Pydantic AI projects. Use this guide to find the right library for your needs.

---

## Quick Library Selector

**I need to...**

- **Save/load conversation history** → [`agent_memory/context_memory.md`](#context-memory)
- **Store user preferences across sessions** → [`agent_memory/long_term_memory.md`](#long-term-memory)
- **Read/write files** → [`filesystem/file_operations.md`](#file-operations)
- **List/create directories** → [`filesystem/directory_operations.md`](#directory-operations)
- **Load agent system prompts** → [`utils/prompt_loader.md`](#prompt-loader)
- **Load MCP configuration** → [`utils/config_loader.md`](#config-loader)
- **Parse CLI arguments** → [`utils/argument_parser.md`](#argument-parser)
- **Chunk markdown files** → [`parsers/markdown_parser.md`](#markdown-parser)
- **Crawl web pages** → [`web/web_crawler.md`](#web-crawler)
- **Search the web** → [`web/web_search.md`](#web-search)
- **Generate embeddings** → [`embedding/openai_embeddings.md`](#openai-embeddings)
- **Index/search knowledge base** → [`knowledge_base/knowledge_vectordb.md`](#knowledge-vectordb)

---

## Library Categories

### Memory Management
Session and cross-session data persistence

- **context_memory** - Conversation history per session
- **long_term_memory** - User preferences across sessions

### File System
File and directory operations

- **file_operations** - Read, write, append, delete files
- **directory_operations** - List, create, manage directories

### Configuration & Setup
Loading configuration and prompts

- **prompt_loader** - Load agent system prompts
- **config_loader** - Load MCP configuration
- **argument_parser** - Parse CLI arguments with session management

### Parsing
Content parsing and transformation

- **markdown_parser** (parsers/) - Advanced markdown chunking with metadata
- **markdown_parser** (utils/) - Legacy H2-based chunking

### Web Operations
Web search and content extraction

- **web_crawler** - Extract content from web pages
- **web_search** - DuckDuckGo search integration

### AI/ML Operations
Embeddings and vector database

- **openai_embeddings** - Generate OpenAI embeddings
- **knowledge_vectordb** - Vector database for knowledge retrieval

---

## Library Overview

### Memory Management

#### Context Memory
**File:** `agent_memory/context_memory.md`

Manages conversation history for multi-turn agent interactions.

**Key Functions:**
- `save_context()` - Save message history to disk
- `load_context()` - Load message history from disk
- `get_latest_session()` - Find most recent session
- `summarize_context()` - Summarize long conversations

**Use When:**
- Building stateful agents
- Need conversation continuity
- Agent should remember previous interactions
- Multi-turn dialogues

**Examples in codebase:**
- All stateful agents (StoryResearcher, VideoDirector, etc.)

---

#### Long-term Memory
**File:** `agent_memory/long_term_memory.md`

Stores user preferences across sessions.

**Key Functions:**
- `save_long_term_memory()` - Append new preference
- `load_long_term_memory()` - Load all preferences

**Use When:**
- Tracking user preferences
- Cross-session personalization
- Building user profiles
- Preference-based behavior

**Examples in codebase:**
- UserPreferenceAgent extracts and stores preferences

---

### File System

#### File Operations
**File:** `filesystem/file_operations.md`

Safe file I/O with error handling.

**Key Functions:**
- `read_file()` - Read file content
- `write_file()` - Write/overwrite file
- `append_file()` - Append to file
- `file_exists()` - Check file existence
- `rename_file()` - Rename file
- `delete_file()` - Delete file

**Use When:**
- Reading input files
- Writing output files
- Incremental file writing
- File management

**Examples in codebase:**
- CLI scripts (read stories, write shots)
- MCP filesystem server

---

#### Directory Operations
**File:** `filesystem/directory_operations.md`

Directory management with metadata.

**Key Functions:**
- `list_directory()` - List contents with metadata (CSV)
- `create_directory()` - Create directory recursively
- `file_exists()` - Check path existence

**Use When:**
- Listing directory contents
- Creating output directories
- File system exploration
- MCP filesystem tools

**Examples in codebase:**
- MCP filesystem server

---

### Configuration & Setup

#### Prompt Loader
**File:** `utils/prompt_loader.md`

Load system prompts from agent directory structure.

**Key Functions:**
- `load_system_prompt()` - Load system_prompt.md
- `load_prompt()` - Load named prompt file

**Use When:**
- Initializing agents
- Loading system prompts
- Multi-prompt agents
- Following standard structure

**Examples in codebase:**
- Every agent's `__init__` method

---

#### Config Loader
**File:** `utils/config_loader.md`

Load MCP configuration file path.

**Key Functions:**
- `load_mcp_config()` - Get path to mcp_config.json

**Use When:**
- Initializing orchestrator agents
- Need MCP servers
- Following standard structure

**Examples in codebase:**
- StoryResearcher, StoryCreatorAgent (orchestrator agents)

---

#### Argument Parser
**File:** `utils/argument_parser.md`

Standardized CLI argument parsing with session management.

**Key Functions:**
- `get_arguments()` - Parse CLI args, return CLIArgs

**Returns:**
```python
CLIArgs(
    session_id: str,
    input_file: Optional[str],
    output_file: Optional[str],
    verbose: bool
)
```

**Use When:**
- Building CLI interfaces
- Need session management
- Standard argument handling
- Input/output files

**Examples in codebase:**
- All CLI scripts (research_story, generate_shots, etc.)

---

### Parsing

#### Markdown Parser (Advanced)
**File:** `parsers/markdown_parser.md`

Advanced markdown chunking with metadata for knowledge indexing.

**Key Functions:**
- `chunk_markdown_by_headers()` - Split by H2+ with metadata

**Returns:**
```python
[{
    'text': str,
    'source_file': str,
    'section_header': str,
    'chunk_index': int
}]
```

**Use When:**
- Indexing knowledge bases
- Need metadata with chunks
- Building vector databases
- Structured content processing

**Examples in codebase:**
- knowledge_vectordb indexing

---

#### Markdown Parser (Legacy)
**File:** `utils/markdown_parser.md`

Simple H2-based markdown chunking.

**Key Functions:**
- `parse_markdown()` - Split by H2 headers

**Use When:**
- Simple markdown splitting
- Legacy code compatibility
- No metadata needed

**Examples in codebase:**
- generate_shots CLI (legacy)

**Note:** Consider using `parsers/markdown_parser` for new code.

---

### Web Operations

#### Web Crawler
**File:** `web/web_crawler.md`

Extract clean content from web pages.

**Key Functions:**
- `crawl_content()` - Async web page crawling (returns markdown)

**Use When:**
- Extracting web content
- Need clean markdown
- MCP web tools
- Research agents

**Examples in codebase:**
- MCP web_crawler server
- MCP web_search server (crawls top results)

---

#### Web Search
**File:** `web/web_search.md`

DuckDuckGo search integration.

**Key Functions:**
- `search()` - Search and return top 5 results

**Use When:**
- Web search capability
- Finding URLs
- MCP search tools
- Research agents

**Examples in codebase:**
- MCP web_search server

---

### AI/ML Operations

#### OpenAI Embeddings
**File:** `embedding/openai_embeddings.md`

Generate OpenAI embeddings for text.

**Key Functions:**
- `generate_embedding()` - Generate 1536-dim vector
- `get_openai_client()` - Get OpenAI client (singleton)
- `get_embedding_model()` - Get configured model

**Use When:**
- Vectorizing text
- Building knowledge bases
- Semantic search
- Vector operations

**Examples in codebase:**
- knowledge_vectordb indexing/search

---

#### Knowledge VectorDB
**File:** `knowledge_base/knowledge_vectordb.md`

Complete vector database system with Qdrant.

**Key Functions:**
- `index_knowledge()` - Index markdown directory
- `search_knowledge()` - Semantic search across collections
- `create_collection()` - Initialize collection
- `clear_collection()` - Delete collection
- `collection_exists()` - Check existence
- `list_all_chunks()` - List indexed content

**Use When:**
- Building knowledge bases
- Semantic search
- RAG systems
- Documentation retrieval

**Examples in codebase:**
- manage_knowledge_base CLI
- MCP knowledge server

---

## Decision Tree

```
What do you need?

├─ Memory/State Management
│  ├─ Within a session → context_memory
│  └─ Across sessions → long_term_memory
│
├─ File System Operations
│  ├─ File I/O → file_operations
│  └─ Directory mgmt → directory_operations
│
├─ Configuration
│  ├─ System prompts → prompt_loader
│  ├─ MCP config → config_loader
│  └─ CLI arguments → argument_parser
│
├─ Content Processing
│  ├─ Advanced markdown → parsers/markdown_parser
│  └─ Simple markdown → utils/markdown_parser (legacy)
│
├─ Web Operations
│  ├─ Crawl pages → web_crawler
│  └─ Search web → web_search
│
└─ AI/ML
   ├─ Generate embeddings → openai_embeddings
   └─ Vector search → knowledge_vectordb
```

---

## Common Import Patterns

### Direct Function Imports
```python
# Memory
from src.libs.agent_memory.context_memory import save_context, load_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory

# File System
from src.libs.filesystem.file_operations import read_file, write_file
from src.libs.filesystem.directory_operations import create_directory

# Configuration
from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.utils.argument_parser import get_arguments

# Parsing
from src.libs.parsers import chunk_markdown_by_headers
from src.libs.utils.markdown_parser import parse_markdown

# Web
from src.libs.web.crawl import crawl_content
from src.libs.web.duck_duck_go import search

# AI/ML
from src.libs.embedding import generate_embedding
from src.libs.knowledge_base import search_knowledge, index_knowledge
```

### Package-Level Imports (via __init__.py)
```python
from src.libs.embedding import generate_embedding
from src.libs.parsers import chunk_markdown_by_headers
from src.libs.knowledge_base import search_knowledge
```

---

## Library Usage by Component

### Agents (Stateful)
- `prompt_loader` - Load system prompts
- `context_memory` - Maintain conversation
- `config_loader` - Load MCP config (orchestrators only)
- `long_term_memory` - Access preferences (optional)

### Agents (Stateless)
- `prompt_loader` - Load system prompts

### CLI Scripts
- `argument_parser` - Parse arguments
- `file_operations` - Read/write files
- `context_memory` - Session management (interactive CLIs)

### MCP Servers
- `file_operations` / `directory_operations` - Filesystem server
- `web_crawler` / `web_search` - Web servers
- `knowledge_vectordb` - Knowledge server

---

## Getting Started

**To use a library:**

1. **Find the library** using quick selector above
2. **Read the blueprint** for detailed documentation
3. **Read `COMMON.md`** for shared patterns
4. **Copy import statement** from blueprint
5. **Follow usage examples** from real code

---

## File Structure

```
PDs/blueprints/libs/
├── INDEX.md (this file)
├── COMMON.md (shared patterns)
├── agent_memory/
│   ├── context_memory.md
│   └── long_term_memory.md
├── filesystem/
│   ├── file_operations.md
│   └── directory_operations.md
├── utils/
│   ├── prompt_loader.md
│   ├── config_loader.md
│   ├── argument_parser.md
│   └── markdown_parser.md
├── web/
│   ├── web_crawler.md
│   └── web_search.md
├── embedding/
│   └── openai_embeddings.md
├── knowledge_base/
│   └── knowledge_vectordb.md
└── parsers/
    └── markdown_parser.md
```

---

## Environment Variables

Libraries may require these environment variables:

```env
# OpenRouter (for embeddings and knowledge base)
OPENROUTER_API_KEY=required
EMBEDDING_MODEL=openai/text-embedding-3-small (optional)

# Qdrant (for knowledge base)
QDRANT_PATH=.mythline/knowledge_base (optional)

# Context/Memory (automatically created)
CONTEXT_DIR=.mythline (hardcoded in library)
```

---

## Directory Structure Conventions

```
.mythline/
├── {agent_id}/
│   ├── context_memory/
│   │   └── {session_id}.json
│   └── long_term_memory/
│       └── memory.json
└── knowledge_base/
    └── (Qdrant vector DB files)
```

---

## Related Documentation

- `COMMON.md` - Shared library patterns (this directory)
- `../interfaces/` - CLI interface patterns
- `../pydantic/pydantic_ai_agent_guide.md` - Agent development guide
- `../pydantic/pydantic_ai_project_structure.md` - Project structure

---

## Library Comparison

| Library | Category | Stateful | Async | Requires Config | Used By |
|---------|----------|----------|-------|-----------------|---------|
| context_memory | Memory | Yes | No | No | All stateful agents |
| long_term_memory | Memory | Yes | No | No | UserPreferenceAgent |
| file_operations | Filesystem | No | No | No | CLI, MCP, agents |
| directory_operations | Filesystem | No | No | No | MCP |
| prompt_loader | Config | No | No | No | All agents |
| config_loader | Config | No | No | No | Orchestrator agents |
| argument_parser | Config | No | No | No | All CLIs |
| markdown_parser (parsers) | Parsing | No | No | No | knowledge_vectordb |
| markdown_parser (utils) | Parsing | No | No | No | generate_shots (legacy) |
| web_crawler | Web | No | Yes | Yes | MCP servers |
| web_search | Web | No | No | No | MCP servers |
| openai_embeddings | AI/ML | No | No | Yes | knowledge_vectordb |
| knowledge_vectordb | AI/ML | Yes | No | Yes | MCP, CLI |

---

## Quick Examples

### Save/Load Context
```python
from src.libs.agent_memory.context_memory import save_context, load_context

messages = load_context('story_research', session_id)
response = agent.run(prompt, message_history=messages)
save_context('story_research', session_id, response.all_messages())
```

### Read/Write Files
```python
from src.libs.filesystem.file_operations import read_file, write_file

content = read_file('input.md')
write_file('output.md', processed_content)
```

### Load System Prompt
```python
from src.libs.utils.prompt_loader import load_system_prompt

system_prompt = load_system_prompt(__file__)
```

### Parse CLI Arguments
```python
from src.libs.utils.argument_parser import get_arguments

args = get_arguments(agent_id='my_agent', description='My CLI')
```

### Search Knowledge Base
```python
from src.libs.knowledge_base import search_knowledge

results = search_knowledge('How to create characters?', top_k=3)
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Support

For detailed information about each library, refer to its specific blueprint file in the appropriate category directory.
