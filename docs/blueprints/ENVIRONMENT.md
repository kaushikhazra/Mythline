# Environment Variables Blueprint

**Purpose:** Single source of truth for all environment variables in a Pydantic AI multi-agent system.

**File:** `.env` (gitignored) - Use `.env.example` as template

---

## Table of Contents

- [Quick Start](#quick-start)
- [Required Variables](#required-variables)
- [LLM Configuration](#llm-configuration)
- [MCP Server Ports](#mcp-server-ports)
- [Knowledge Base](#knowledge-base)
- [Optional Variables](#optional-variables)
- [Environment File Template](#environment-file-template)
- [Usage in Code](#usage-in-code)

---

## Implementation Rules (MUST Follow)

### Rule 1: ALWAYS Load dotenv at Module Level

✓ **RIGHT - Load at module level in EVERY file that uses agents:**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # At module level, after imports

class MyClass:
    def __init__(self):
        api_key = os.getenv('OPENROUTER_API_KEY')
```

❌ **WRONG - Loading in __init__ or functions:**
```python
class MyClass:
    def __init__(self):
        load_dotenv()  # Don't do this!
        api_key = os.getenv('OPENROUTER_API_KEY')
```

❌ **WRONG - Not loading at all:**
```python
# No load_dotenv()!
from src.agents.my_agent import MyAgent

agent = MyAgent()  # Will fail if .env not loaded!
```

**Why:** Loading dotenv multiple times is safe but inefficient. NOT loading it means environment variables won't be available and agents will fail.

**CRITICAL RULE:** `load_dotenv()` MUST be called at module level in:
- ✅ All agent files (`agent.py`)
- ✅ All MCP server files (`server.py`)
- ✅ All graph files that use agents
- ✅ All CLI entry points
- ✅ All test files
- ✅ Any file that uses `os.getenv()` or instantiates agents

**It's better to call `load_dotenv()` multiple times than to forget it once!**

### Rule 2: Use OpenRouter Model Format Directly

✓ **RIGHT - Use model string directly:**
```python
llm_model = os.getenv('LLM_MODEL')
# Results in: "openai/gpt-4o-mini" (correct)
```

❌ **WRONG - Adding prefix:**
```python
llm_model = f"openai:{os.getenv('LLM_MODEL')}"
# Results in: "openai:openai/gpt-4o-mini" (double prefix!)
```

**Why:** OpenRouter models already include the provider prefix in the format `provider/model-name`.

### Rule 3: Always Provide Defaults for Optional Variables

✓ **RIGHT - Provide sensible defaults:**
```python
port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
model = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
path = os.getenv('QDRANT_PATH', '.mythline/knowledge_base')
```

❌ **WRONG - No defaults for optional vars:**
```python
port = int(os.getenv('MCP_WEB_SEARCH_PORT'))  # Crashes if not set!
```

**Why:** Optional variables should have defaults. Only OPENROUTER_API_KEY is required.

### Rule 4: Type Conversion for Non-String Variables

✓ **RIGHT - Convert to appropriate types:**
```python
# Integers
port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))

# Booleans
debug = os.getenv('DEBUG', 'false').lower() == 'true'

# Lists
allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
```

❌ **WRONG - Using strings directly:**
```python
port = os.getenv('MCP_WEB_SEARCH_PORT', '8000')  # String, not int!
if port == 8000:  # This comparison will FAIL!
    pass
```

**Why:** Environment variables are always strings. Convert to needed type.

### Rule 5: Never Commit .env Files

✓ **RIGHT - Use .env.example:**
```bash
# Create .env.example with placeholders
cp .env .env.example
# Remove real values from .env.example
# Commit .env.example to git
# Add .env to .gitignore
```

❌ **WRONG - Committing .env:**
```bash
git add .env  # NEVER do this!
git commit -m "Add env file"  # Contains secrets!
```

**Why:** .env contains secrets (API keys). Only commit .env.example as template.

### Rule 6: Port Numbers Must Match Between .env and MCP Configs

✓ **RIGHT - Consistent ports:**
```env
# In .env
MCP_WEB_SEARCH_PORT=8000
```

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

❌ **WRONG - Mismatched ports:**
```env
MCP_WEB_SEARCH_PORT=9000
```

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp"  // Different port!
    }
  }
}
```

**Why:** Agents can't connect to MCP servers if ports don't match.

### Rule 7: Environment Variable Naming Convention

✓ **RIGHT - Consistent naming:**
```env
# All uppercase with underscores
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=openai/gpt-4o-mini
MCP_WEB_SEARCH_PORT=8000
QDRANT_PATH=.mythline/knowledge_base
```

❌ **WRONG - Inconsistent naming:**
```env
openrouter_api_key=...      # Not uppercase
llmModel=...                 # Not snake_case
mcp-web-search-port=...      # Using hyphens
```

**Why:** Consistency makes environment variables easy to find and use.

### Rule 8: Validate Required Variables

✓ **RIGHT - Check required variables:**
```python
from dotenv import load_dotenv
import os

load_dotenv()

# Validate required variables
if not os.getenv('OPENROUTER_API_KEY'):
    raise EnvironmentError("OPENROUTER_API_KEY is required. Add it to .env file.")

# Continue with optional variables
llm_model = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
```

❌ **WRONG - Assuming variables exist:**
```python
api_key = os.getenv('OPENROUTER_API_KEY')  # Might be None!
# Later...
response = openrouter.call(api_key=api_key)  # Crashes if None!
```

**Why:** Required variables should be validated early to give clear error messages.

---

## Usage Examples by Context

### In Agent Files

✓ **REQUIRED pattern:**
```python
# File: src/agents/my_agent/agent.py
import os
from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv()  # MUST be at module level

class MyAgent:
    AGENT_ID = "my_agent"

    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
        self.agent = Agent(llm_model, system_prompt="...")
```

### In CLI Entry Points

✓ **REQUIRED pattern:**
```python
# File: src/ui/cli/my_cli.py
import os
from dotenv import load_dotenv
from src.agents.my_agent import MyAgent

load_dotenv()  # MUST be at module level

def main():
    session_id = "cli_session"
    agent = MyAgent(session_id)
    result = agent.run("Hello")
    print(result.output)

if __name__ == "__main__":
    main()
```

### In Graph Files

✓ **REQUIRED pattern:**
```python
# File: src/graphs/my_graph/graph.py
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from src.agents.my_agent import MyAgent

load_dotenv()  # MUST be at module level

def create_graph():
    graph = StateGraph(MyState)
    # Graph definition...
    return graph
```

### In Test Files

✓ **REQUIRED pattern:**
```python
# File: tests/agents/test_my_agent.py
import os
import pytest
from dotenv import load_dotenv
from src.agents.my_agent import MyAgent

load_dotenv()  # MUST be at module level

def test_agent_creation():
    agent = MyAgent()
    assert agent.AGENT_ID == "my_agent"

@pytest.mark.asyncio
async def test_agent_run():
    agent = MyAgent()
    result = await agent.run("test prompt")
    assert result.output
```

### In MCP Server Files

✓ **REQUIRED pattern:**
```python
# File: src/mcp_servers/mcp_my_server/server.py
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()  # MUST be at module level

port = int(os.getenv('MCP_MY_SERVER_PORT', 8000))
server = FastMCP(name="My Server", port=port)

@server.tool()
async def my_tool(param: str) -> str:
    """Tool that uses environment variables."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    # Use api_key...
    return result

if __name__ == '__main__':
    server.run(transport='streamable-http')
```

### In Utility Libraries (If Needed)

✓ **Pattern (only if library uses env vars):**
```python
# File: src/libs/my_lib/processor.py
import os
from dotenv import load_dotenv

load_dotenv()  # Only if this library directly uses os.getenv()

def process_with_api():
    api_key = os.getenv('OPENROUTER_API_KEY')
    # Process...
```

**Note:** Most libraries shouldn't need `load_dotenv()` because they receive configuration as parameters. Only add if the library directly accesses environment variables.

---

## Quick Start

**1. Copy template:**
```bash
cp .env.example .env
```

**2. Add your API key:**
```bash
# Edit .env and add:
OPENROUTER_API_KEY=your_key_here
```

**3. Verify (all other vars have defaults):**
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✓ API Key:', 'SET' if os.getenv('OPENROUTER_API_KEY') else 'MISSING')"
```

---

## Required Variables

### OPENROUTER_API_KEY

**Purpose:** API key for OpenRouter (unified LLM and embedding provider)

**Required:** Yes

**Format:** String (starts with `sk-or-v1-...`)

**Get it from:** https://openrouter.ai/keys

**Used by:**
- All agents (LLM inference)
- Embedding generation (knowledge base)
- MCP servers (when they need LLM capabilities)

**Example:**
```env
OPENROUTER_API_KEY=sk-or-v1-1234567890abcdef...
```

**Security:**
- Never commit to git (in `.gitignore`)
- Don't share in logs or error messages
- Rotate if compromised

---

## LLM Configuration

### LLM_MODEL

**Purpose:** Default language model for all agents

**Required:** No (has default)

**Default:** `openai/gpt-4o-mini`

**Format:** `provider/model-name` (OpenRouter format)

**Popular Options:**
```env
# OpenAI models
LLM_MODEL=openai/gpt-4o-mini          # Fast, cheap (default)
LLM_MODEL=openai/gpt-4o               # Most capable
LLM_MODEL=openai/gpt-5-mini           # Latest mini model

# Anthropic models
LLM_MODEL=anthropic/claude-3.5-sonnet # Great for reasoning
LLM_MODEL=anthropic/claude-3-opus     # Most capable Anthropic

# Google models
LLM_MODEL=google/gemini-pro-1.5       # Google's flagship

# Meta models
LLM_MODEL=meta-llama/llama-3.1-70b    # Open source
```

**Browse all models:** https://openrouter.ai/models

**Used by:**
- Every agent's `__init__`: `llm_model = os.getenv('LLM_MODEL')`
- Context memory summarization
- MCP server examples

**Cost Considerations:**
- `gpt-4o-mini` - Cheapest, good for most tasks
- `gpt-4o` - More expensive, better reasoning
- Check OpenRouter pricing for your model

### EMBEDDING_MODEL

**Purpose:** Model for generating text embeddings (vector search)

**Required:** No (has default)

**Default:** `openai/text-embedding-3-small`

**Format:** `provider/model-name` (OpenRouter format)

**Options:**
```env
# OpenAI embeddings (recommended)
EMBEDDING_MODEL=openai/text-embedding-3-small   # 1536 dims (default)
EMBEDDING_MODEL=openai/text-embedding-3-large   # 3072 dims (better quality)

# Alternative providers
EMBEDDING_MODEL=mistralai/mistral-embed-2312    # 1024 dims
EMBEDDING_MODEL=qwen/qwen3-embedding-8b         # 1024 dims
```

**Used by:**
- `src/libs/embedding/openai_embeddings.py`
- `src/mcp_servers/mcp_knowledge_base/server.py`
- Knowledge base indexing and search

**Important:**
- Vector dimensions must match your Qdrant configuration
- Changing this requires re-indexing knowledge base
- More dimensions = better quality but slower/more storage

---

## MCP Server Ports

MCP servers run on localhost. Ports must be unique.

### MCP_WEB_SEARCH_PORT

**Default:** `8000`

**Server:** `mcp_web_search`

**Purpose:** Web search via DuckDuckGo + auto-crawl top results

**Used by:** Agents with web research needs

```env
MCP_WEB_SEARCH_PORT=8000
```

### MCP_WEB_CRAWLER_PORT

**Default:** `8001`

**Server:** `mcp_web_crawler`

**Purpose:** Extract content from specific URLs

**Used by:** Agents needing URL content

```env
MCP_WEB_CRAWLER_PORT=8001
```

### MCP_FILESYSTEM_PORT

**Default:** `8002`

**Server:** `mcp_filesystem`

**Purpose:** File and directory operations

**Used by:** Agents that read/write files

```env
MCP_FILESYSTEM_PORT=8002
```

### MCP_KNOWLEDGE_BASE_PORT

**Default:** `8003`

**Server:** `mcp_knowledge_base`

**Purpose:** Vector search in knowledge bases

**Used by:** Agents accessing documentation/guides

```env
MCP_KNOWLEDGE_BASE_PORT=8003
```

**Port Assignment Rules:**
- Start at 8000+
- No conflicts with other services
- Update agent `config/mcp_config.json` if you change ports
- All servers use `http://localhost:{PORT}/mcp`

---

## Knowledge Base

### QDRANT_PATH

**Purpose:** Storage location for Qdrant vector database

**Required:** No (has default)

**Default:** `.mythline/knowledge_base`

**Format:** Relative or absolute path

```env
QDRANT_PATH=.mythline/knowledge_base
```

**Notes:**
- Directory created automatically
- Relative to project root
- Gitignored (in `.mythline/`)
- Contains embedded documents for vector search

**Disk Usage:**
- Grows with indexed content
- ~100MB per 1000 documents (rough estimate)
- Safe to delete to clear index (will need re-indexing)

---

## Optional Variables

### PYTHONDONTWRITEBYTECODE

**Purpose:** Prevent Python from creating `__pycache__` directories

**Default:** Not set

**Recommended:** `1`

```env
PYTHONDONTWRITEBYTECODE=1
```

**Benefits:**
- Cleaner directory structure
- Faster git operations
- No stale bytecode issues

### Development Variables

These are not currently used but may be useful:

```env
# Debug mode
DEBUG=true

# Log level
LOG_LEVEL=INFO

# Development vs Production
ENVIRONMENT=development
```

---

## Environment File Template

**Complete `.env.example`:**

```env
# ============================================
# MYTHLINE ENVIRONMENT CONFIGURATION
# ============================================

# --------------------------------------------
# REQUIRED: OpenRouter API
# --------------------------------------------
# Get your key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=

# --------------------------------------------
# LLM CONFIGURATION
# --------------------------------------------
# Format: provider/model-name (OpenRouter format)
# Browse models: https://openrouter.ai/models

# Language model for agents
LLM_MODEL=openai/gpt-4o-mini

# Embedding model for knowledge base
EMBEDDING_MODEL=openai/text-embedding-3-small

# --------------------------------------------
# MCP SERVER PORTS
# --------------------------------------------
# Keep these unique and update agent configs if changed

MCP_WEB_SEARCH_PORT=8000
MCP_WEB_CRAWLER_PORT=8001
MCP_FILESYSTEM_PORT=8002
MCP_KNOWLEDGE_BASE_PORT=8003

# --------------------------------------------
# KNOWLEDGE BASE
# --------------------------------------------
# Vector database storage location
QDRANT_PATH=.mythline/knowledge_base

# --------------------------------------------
# PYTHON CONFIGURATION
# --------------------------------------------
# Prevent __pycache__ directories
PYTHONDONTWRITEBYTECODE=1
```

---

## Usage in Code

### Loading Environment Variables

**Every agent and script:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Access variables
api_key = os.getenv('OPENROUTER_API_KEY')
model = os.getenv('LLM_MODEL')
```

**Best Practice:** Load at module level, not in functions.

### Standard Pattern in Agents

```python
import os
from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv()

class MyAgent:
    AGENT_ID = "my_agent"

    def __init__(self, session_id: str):
        self.session_id = session_id

        # Load from environment
        llm_model = os.getenv('LLM_MODEL')

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )
```

### With Defaults

```python
# Provide fallback if not set
model = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
path = os.getenv('QDRANT_PATH', '.mythline/knowledge_base')
```

### Type Conversion

```python
# Integers
port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))

# Booleans
debug = os.getenv('DEBUG', 'false').lower() == 'true'

# Lists
cors_origins = os.getenv('CORS_ORIGINS', '').split(',')
```

### Validation

```python
from dotenv import load_dotenv
import os

load_dotenv()

# Check required variables
required_vars = ['OPENROUTER_API_KEY']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    raise EnvironmentError(f"Missing required environment variables: {missing}")
```

---

## Environment by Component

### Agents
**Need:**
- `OPENROUTER_API_KEY` (required)
- `LLM_MODEL` (optional, has default)

**Example:**
```python
llm_model = os.getenv('LLM_MODEL')
```

### MCP Servers
**Need:**
- `MCP_{SERVER}_PORT` (optional, has default)
- `OPENROUTER_API_KEY` (if server uses LLM)

**Example:**
```python
port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
server = FastMCP(name="Web Search", port=port)
```

### Knowledge Base
**Need:**
- `OPENROUTER_API_KEY` (for embeddings)
- `EMBEDDING_MODEL` (optional, has default)
- `QDRANT_PATH` (optional, has default)

**Example:**
```python
from src.libs.embedding import generate_embedding

embedding = generate_embedding("text to embed")
# Uses OPENROUTER_API_KEY and EMBEDDING_MODEL from environment
```

### CLI Scripts
**Need:**
- All agent requirements (they create agents)

**Example:**
```python
from src.agents.story_research_agent import StoryResearchAgent

# Agent automatically loads from environment
researcher = StoryResearchAgent(session_id="cli_session")
```

---

## Troubleshooting

### "Missing API Key" Error

**Problem:** `OPENROUTER_API_KEY` not set

**Solution:**
```bash
# Check if .env exists
ls -la .env

# If not, copy template
cp .env.example .env

# Edit and add your key
nano .env  # or your editor
```

### "Model not found" Error

**Problem:** Invalid model name format

**Solution:**
```env
# Wrong (old OpenAI format)
LLM_MODEL=gpt-4o

# Right (OpenRouter format)
LLM_MODEL=openai/gpt-4o
```

### Port Already in Use

**Problem:** MCP server port conflict

**Solution:**
```env
# Change to unused port
MCP_WEB_SEARCH_PORT=9000

# Update agent's config/mcp_config.json to match
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:9000/mcp"  # Must match .env
    }
  }
}
```

### Changes Not Taking Effect

**Problem:** Environment not reloaded

**Solution:**
```bash
# Restart Python process
# Or in code:

from importlib import reload
import os
from dotenv import load_dotenv

load_dotenv(override=True)  # Force reload
```

---

## Security Best Practices

### Never Commit `.env`

**Already in `.gitignore`:**
```gitignore
.env
.env.local
.env.*.local
```

**If accidentally committed:**
```bash
# Remove from git history
git rm --cached .env
git commit -m "Remove .env from tracking"

# Rotate your API key immediately!
```

### Use `.env.example` for Documentation

**What to include:**
- All variable names
- Comments explaining purpose
- Example values (not real keys!)
- Defaults where applicable

**What NOT to include:**
- Real API keys
- Sensitive data
- Production values

### Rotate Keys if Compromised

1. Generate new key at https://openrouter.ai/keys
2. Update `.env` with new key
3. Revoke old key in OpenRouter dashboard
4. Test that everything still works

---

## Related Documentation

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Where environment is used
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Initial setup
- **[.env.example](../../.env.example)** - Template file
- **[OpenRouter Docs](https://openrouter.ai/docs)** - API provider

---

## Summary

| Variable                 | Required | Default                           | Purpose                        |
|--------------------------|----------|-----------------------------------|--------------------------------|
| OPENROUTER_API_KEY       | ✓        | -                                 | API authentication             |
| LLM_MODEL                |          | openai/gpt-4o-mini                | Agent language model           |
| EMBEDDING_MODEL          |          | openai/text-embedding-3-small     | Vector embeddings              |
| MCP_WEB_SEARCH_PORT      |          | 8000                              | Web search server              |
| MCP_WEB_CRAWLER_PORT     |          | 8001                              | Web crawler server             |
| MCP_FILESYSTEM_PORT      |          | 8002                              | Filesystem server              |
| MCP_KNOWLEDGE_BASE_PORT  |          | 8003                              | Knowledge base server          |
| QDRANT_PATH              |          | .mythline/knowledge_base          | Vector DB location             |
| PYTHONDONTWRITEBYTECODE  |          | -                                 | Prevent __pycache__            |

**Remember:** Only `OPENROUTER_API_KEY` is required. All others have sensible defaults!
