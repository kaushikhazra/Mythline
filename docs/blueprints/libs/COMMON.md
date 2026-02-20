# Library Common Patterns

Shared patterns and conventions used across all library modules.

---

## Import Patterns

### Direct Function Imports (Recommended)

```python
# Memory management
from src.libs.agent_memory.context_memory import save_context, load_context
from src.libs.agent_memory.long_term_memory import save_long_term_memory

# File system
from src.libs.filesystem.file_operations import read_file, write_file, append_file
from src.libs.filesystem.directory_operations import create_directory

# Configuration
from src.libs.utils.prompt_loader import load_system_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.utils.argument_parser import get_arguments

# Parsing
from src.libs.utils.markdown_parser import parse_markdown

# Web
from src.libs.web.crawl import crawl_content
from src.libs.web.duck_duck_go import search
```

### Package-Level Imports (via __init__.py)

```python
from src.libs.embedding import generate_embedding
from src.libs.parsers import chunk_markdown_by_headers
from src.libs.knowledge_base import search_knowledge, index_knowledge
```

---

## Function Naming Conventions

### Action Verbs

- **load_*** - Load data from storage (`load_context`, `load_system_prompt`)
- **save_*** - Save data to storage (`save_context`, `save_long_term_memory`)
- **get_*** - Retrieve or calculate value (`get_arguments`, `get_latest_session`)
- **create_*** - Initialize new resource (`create_directory`, `create_collection`)
- **generate_*** - Compute or produce output (`generate_embedding`)
- **search_*** - Query or find data (`search_knowledge`, `search`)
- **index_*** - Process and store for retrieval (`index_knowledge`)
- **chunk_*** - Split into pieces (`chunk_markdown_by_headers`)
- **crawl_*** - Fetch web content (`crawl_content`)

### Noun Suffixes

- ***_context** - Session memory operations
- ***_memory** - Storage operations
- ***_file** / ***_directory** - File system operations
- ***_prompt** - Prompt loading
- ***_config** - Configuration
- ***_knowledge** - Knowledge base operations
- ***_embedding** - Vector generation

---

## Error Handling Patterns

### Pattern 1: Return Error Strings

Used when library is exposed as MCP tool:

```python
def read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
```

**Used by:** `file_operations`, `directory_operations`

### Pattern 2: Return Empty/None on Failure

Used when absence is acceptable:

```python
def load_context(agent_id: str, session_id: str) -> list[ModelMessage]:
    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")
    if not file_path.exists():
        return []
    # ... load and return
```

**Used by:** `context_memory`, `long_term_memory`

### Pattern 3: Raise Exceptions

Used for critical operations:

```python
def clear_collection(knowledge_dir: str):
    if not client.collection_exists(collection_name):
        raise ValueError(f"Collection '{collection_name}' does not exist")
    client.delete_collection(collection_name)
```

**Used by:** `knowledge_vectordb`

---

## Return Type Patterns

### Simple Types

```python
str          # File content, error messages, paths
bool         # Existence checks, success flags
int          # Counts, IDs
list[float]  # Embeddings (1536-dimensional vectors)
```

### Structured Types

```python
list[ModelMessage]      # Context memory
list[dict]              # Search results, chunks, preferences
CLIArgs (dataclass)     # CLI arguments
QdrantClient            # Database client (context manager)
```

### Example Structured Returns

**Search results:**
```python
[{
    'text': str,
    'source_file': str,
    'section_header': str,
    'score': float,
    'collection': str
}]
```

**Markdown chunks:**
```python
[{
    'text': str,
    'source_file': str,
    'section_header': str,
    'chunk_index': int
}]
```

**User preferences:**
```python
[{
    'preference': str,
    'timestamp': str  # ISO format
}]
```

---

## Configuration Patterns

### Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Required
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Optional with defaults
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'openai/text-embedding-3-small')
QDRANT_PATH = os.getenv('QDRANT_PATH', '.mythline/knowledge_base')
```

**Common environment variables:**
- `OPENROUTER_API_KEY` - OpenRouter API key (required for embeddings, knowledge base)
- `EMBEDDING_MODEL` - Embedding model name in OpenRouter format (default: openai/text-embedding-3-small)
- `QDRANT_PATH` - Vector database location (default: .mythline/knowledge_base)

### Module-Level Constants

```python
# Directory paths
CONTEXT_DIR = ".mythline"

# Processing limits
MAX_MESSAGES_BEFORE_SUMMARY = 50
KEEP_RECENT_MESSAGES = 20
```

### Function Parameters with Defaults

```python
def search_knowledge(query: str, top_k: int = 3) -> list[dict]
def index_knowledge(knowledge_dir: str, fresh: bool = False) -> int
def get_arguments(
    agent_id: str,
    description: str = "CLI Application",
    require_input: bool = False,
    require_output: bool = False
) -> CLIArgs
```

---

## Path Handling Patterns

### Using pathlib (Preferred)

```python
from pathlib import Path

# Create path
file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")

# Create parent directories
file_path.parent.mkdir(parents=True, exist_ok=True)

# Check existence
if file_path.exists():
    # Load file

# Iterate files
for md_file in Path(knowledge_dir).glob("**/*.md"):
    process_file(md_file)
```

### Using os.path (For compatibility)

```python
import os

# Resolve paths relative to caller
agent_dir = os.path.dirname(os.path.abspath(caller_file))
prompt_path = os.path.join(agent_dir, "prompts", "system_prompt.md")

# Check existence
if os.path.exists(file_path):
    # Process file

# Create directory
os.makedirs(directory_path, exist_ok=True)
```

---

## Directory Structure Conventions

### Memory Storage

```
.mythline/
├── {agent_id}/
│   ├── context_memory/
│   │   ├── {session_id_1}.json
│   │   └── {session_id_2}.json
│   └── long_term_memory/
│       └── memory.json
└── knowledge_base/
    └── (Qdrant vector DB files)
```

### Knowledge Base Structure

```
guides/                         # Knowledge directory
├── character_guide.md
├── story_guide.md
└── ...

.mythline/knowledge_base/       # Qdrant storage
└── (collection: guides_knowledge)
```

---

## Design Patterns

### Singleton Pattern

Used for expensive resources:

```python
from typing import Optional
from openai import OpenAI

_openai_client: Optional[OpenAI] = None

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv('OPENROUTER_API_KEY')
        )
    return _openai_client
```

**Used by:** `openai_embeddings`

**Note:** Uses OpenAI SDK with OpenRouter endpoint for unified API access.

### Context Manager Pattern

Used for resource cleanup:

```python
from contextlib import contextmanager
from qdrant_client import QdrantClient

@contextmanager
def qdrant_client():
    client = QdrantClient(path=QDRANT_PATH)
    try:
        yield client
    finally:
        client.close()

# Usage
with qdrant_client() as client:
    results = client.search(...)
```

**Used by:** `knowledge_vectordb`

---

## Async Patterns

Some libraries require async operations:

```python
import asyncio

# Async function
async def crawl_content(url: str) -> str:
    # Async operations...
    return content

# Calling from sync code
content = asyncio.run(crawl_content(url))

# Calling from async code
content = await crawl_content(url)
```

**Used by:** `web_crawler`

---

## Data Serialization

### Pydantic Models

```python
from pydantic_ai.messages import ModelMessage

# Save
messages: list[ModelMessage] = agent_output.all_messages()
with open(file_path, 'w') as f:
    json.dump([msg.model_dump() for msg in messages], f, indent=2)

# Load
with open(file_path, 'r') as f:
    messages = [ModelMessage.model_validate(msg) for msg in json.load(f)]
```

### Plain Dictionaries

```python
import json

# Save
data = [{'key': 'value', 'timestamp': '2024-11-13T10:30:00'}]
with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

# Load
with open(file_path, 'r') as f:
    data = json.load(f)
```

---

## Performance Considerations

### Lazy Loading

Only import heavy libraries when needed:

```python
def search_command(args):
    # Import only when needed
    from src.libs.knowledge_base import search_knowledge
    results = search_knowledge(args.query)
```

### Caching

Use singletons for expensive resources:

```python
# Don't recreate client on every call
client = get_openai_client()  # Returns cached client
```

### Batch Processing

Process in chunks with progress indication:

```python
from tqdm import tqdm

for chunk in tqdm(chunks, desc="Processing"):
    embedding = generate_embedding(chunk)
    store_embedding(embedding)
```

---

## Common Pitfalls

### File Encoding

Always specify UTF-8:

```python
# Correct
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Wrong (platform-dependent)
with open(file_path, 'r') as f:
    content = f.read()
```

### Path Separators

Use `os.path.join()` or `Path` for cross-platform:

```python
# Correct
path = os.path.join(base, subdir, filename)
path = Path(base) / subdir / filename

# Wrong (Windows issues)
path = f"{base}/{subdir}/{filename}"
```

### Async/Sync Mismatch

Don't call async functions from sync code without `asyncio.run()`:

```python
# Correct
content = asyncio.run(crawl_content(url))

# Wrong (returns coroutine object)
content = crawl_content(url)
```

### Missing Directory Creation

Always create parent directories:

```python
# Correct
file_path.parent.mkdir(parents=True, exist_ok=True)
with open(file_path, 'w') as f:
    f.write(content)

# Wrong (fails if directory doesn't exist)
with open(file_path, 'w') as f:
    f.write(content)
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Related Documentation

- `INDEX.md` - Master library index (this directory)
- Individual library blueprints in category directories
- `../pydantic/pydantic_ai_agent_guide.md` - Agent development patterns
- `../interfaces/` - CLI interface patterns
