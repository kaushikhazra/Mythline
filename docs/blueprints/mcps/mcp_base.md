# MCP Server Base Blueprint

**Purpose:** Executable specification for creating MCP (Model Context Protocol) servers using FastMCP.

**For:** AI assistants and developers building tool servers for agents.

---

## Overview

MCP servers expose tools and functionality to AI agents through a standardized protocol. Each MCP server is a standalone service that runs on its own port and can be accessed by agents through their `mcp_config.json` configuration.

**Key concepts:**
- **MCP Server**: Standalone HTTP service that exposes tools
- **Tool**: Python function decorated with `@server.tool()` that agents can call
- **FastMCP**: Framework for creating MCP servers easily
- **Port**: Each server runs on unique port (configured in .env)
- **Automatic Integration**: Agents automatically get access to tools when server is loaded

**When to create an MCP server:**
- Tools need to be shared across multiple agents
- Functionality involves external services (web, databases, APIs)
- Tools are resource-intensive and should run separately
- Tools perform I/O operations (files, network, etc.)

**When NOT to create an MCP server:**
- Tool is agent-specific → Use custom agent tool instead
- No I/O operations needed → Use pure Python function
- Simple computation → Use utility library

## Base Structure

```
src/mcp_servers/mcp_<server_name>/
├── __init__.py
└── server.py

start_<server_name>.bat (at project root)
```

---

## Default Implementation Pattern

### MUST Follow This Exact Structure

This is the canonical MCP server pattern. Copy this template and fill in placeholders `{like_this}`.

**File:** `src/mcp_servers/mcp_{server_name}/server.py`

```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

port = int(os.getenv('MCP_<SERVER_NAME>_PORT', 8000))
server = FastMCP(name="<Server Display Name>", port=port)

@server.tool()
async def tool_name(arg1: str, arg2: int) -> str:
    """Brief description of what the tool does.

    Args:
        arg1 (str): Description of first argument
        arg2 (int): Description of second argument

    Returns:
        str: Description of return value
    """
    print(f"Tool called with: {arg1}, {arg2}")

    result = perform_operation(arg1, arg2)

    return result

if __name__=='__main__':
    server.run(transport='streamable-http')
```

### `__init__.py`

```python
from .server import server

__all__ = ['server']
```

### `start_<server_name>.bat` (at project root)

```batch
@echo off
echo Starting <Server Name> MCP Server...
python -m src.mcp_servers.mcp_<server_name>.server
```

**File:** `start_{server_name}.bat` (at project root)

```batch
@echo off
echo Starting {Server Display Name} MCP Server...
python -m src.mcp_servers.mcp_{server_name}.server
```

**Environment Configuration (.env):**

```env
MCP_{SERVER_NAME_UPPERCASE}_PORT=8xxx
```

---

## Implementation Rules (MUST Follow)

### 1. Import Order

✓ **REQUIRED order:**
```python
# 1. Standard library
import os

# 2. Third-party (dotenv first, then others)
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 3. Local imports (if needed)
from src.libs.{category}.{module} import {function}

# 4. Load environment AT MODULE LEVEL
load_dotenv()
```

### 2. Server Initialization

✓ **REQUIRED pattern:**
```python
load_dotenv()  # At module level

port = int(os.getenv('MCP_{SERVER_NAME}_PORT', {default_port}))
server = FastMCP(name="{Display Name}", port=port)
```

❌ **WRONG - Hardcoded port:**
```python
server = FastMCP(name="My Server", port=8000)  # Don't hardcode!
```

❌ **WRONG - No port variable:**
```python
server = FastMCP(name="My Server", port=int(os.getenv('MCP_MY_PORT')))  # Can't debug
```

### 3. Tool Decorator

✓ **REQUIRED - Use @server.tool() with parentheses:**
```python
@server.tool()
async def my_tool(param: str) -> str:
    """Tool description."""
    return result
```

❌ **WRONG - Missing parentheses:**
```python
@server.tool  # Missing ()! Will fail!
async def my_tool(param: str) -> str:
    pass
```

### 4. Type Hints

✓ **REQUIRED - All parameters and return types:**
```python
@server.tool()
async def process_data(text: str, count: int, enabled: bool) -> dict:
    """Process data."""
    return {"result": text, "count": count}
```

❌ **WRONG - Missing type hints:**
```python
@server.tool()
async def process_data(text, count):  # No types!
    return {"result": text}
```

### 5. Docstrings

✓ **REQUIRED - Comprehensive docstring:**
```python
@server.tool()
async def search_content(query: str, limit: int) -> list[dict]:
    """Searches for content matching the query.

    Args:
        query (str): Search query string
        limit (int): Maximum number of results (1-100)

    Returns:
        list[dict]: List of search results with title and url
    """
    pass
```

❌ **WRONG - Vague or missing docstring:**
```python
@server.tool()
async def search_content(query: str, limit: int) -> list[dict]:
    """Searches."""  # Too vague!
    pass
```

### 6. Async vs Sync

✓ **RIGHT - Async for I/O operations:**
```python
@server.tool()
async def fetch_url(url: str) -> str:
    """Fetches URL content."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

✓ **RIGHT - Sync for pure computation:**
```python
@server.tool()
def calculate(x: int, y: int) -> int:
    """Calculates sum."""
    return x + y
```

❌ **WRONG - Sync for I/O operations:**
```python
@server.tool()
def fetch_url(url: str) -> str:  # Should be async!
    response = requests.get(url)  # Blocking I/O
    return response.text
```

### 7. Main Guard

✓ **REQUIRED - Always use main guard:**
```python
if __name__ == '__main__':
    server.run(transport='streamable-http')
```

❌ **WRONG - No main guard:**
```python
# At module level (wrong!)
server.run(transport='streamable-http')
```

### 8. Error Handling

✓ **RIGHT - Let FastMCP handle most errors:**
```python
@server.tool()
async def risky_operation(param: str) -> str:
    """Does risky operation."""
    # FastMCP handles basic errors automatically
    result = await external_call(param)
    return result
```

✓ **RIGHT - Handle specific errors when needed:**
```python
@server.tool()
async def careful_operation(param: str) -> dict:
    """Operation with specific error handling."""
    try:
        result = await external_call(param)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": f"Invalid input: {e}"}
```

### 9. Tool Logging

✓ **REQUIRED - Print progress for clarity:**
```python
@server.tool()
async def process_file(path: str) -> str:
    """Processes file."""
    print(f"Processing file: {path}")

    content = read_file(path)
    result = process(content)

    print(f"Processed {len(result)} items")
    return result
```

### 10. Port Assignment

✓ **REQUIRED - Follow port conventions:**
- 8000: Web Search MCP
- 8001: Web Crawler MCP
- 8002: Filesystem MCP
- 8003: Knowledge Base MCP
- 8004+: New servers

❌ **WRONG - Conflicting ports:**
```python
# Don't use 8000-8003 for new servers!
port = int(os.getenv('MCP_MY_NEW_SERVER_PORT', 8000))  # Conflicts!
```

---

## Anti-Patterns (Common Mistakes)

### Anti-Pattern 1: Missing @server.tool() Parentheses

❌ **WRONG:**
```python
@server.tool  # Missing ()!
async def my_tool(param: str) -> str:
    return param
```

✓ **RIGHT:**
```python
@server.tool()  # With ()!
async def my_tool(param: str) -> str:
    return param
```

**Why:** `@server.tool` without parentheses doesn't register the tool correctly.

### Anti-Pattern 2: Hardcoded Ports

❌ **WRONG:**
```python
server = FastMCP(name="My Server", port=8000)
```

✓ **RIGHT:**
```python
port = int(os.getenv('MCP_MY_SERVER_PORT', 8000))
server = FastMCP(name="My Server", port=port)
```

**Why:** Hardcoded ports prevent configuration and cause conflicts.

### Anti-Pattern 3: No Main Guard

❌ **WRONG:**
```python
# server.py module level
server.run(transport='streamable-http')  # Runs on import!
```

✓ **RIGHT:**
```python
if __name__ == '__main__':
    server.run(transport='streamable-http')
```

**Why:** Without main guard, server runs when module is imported.

### Anti-Pattern 4: Missing Type Hints

❌ **WRONG:**
```python
@server.tool()
async def process(data):
    return {"result": data}
```

✓ **RIGHT:**
```python
@server.tool()
async def process(data: str) -> dict:
    return {"result": data}
```

**Why:** Type hints enable FastMCP to validate inputs and generate proper tool schemas.

### Anti-Pattern 5: Vague Docstrings

❌ **WRONG:**
```python
@server.tool()
async def search(query: str) -> list:
    """Searches."""  # Too vague!
    pass
```

✓ **RIGHT:**
```python
@server.tool()
async def search(query: str, limit: int = 10) -> list[dict]:
    """Searches web for query and returns top results.

    Args:
        query (str): Search query string
        limit (int): Max results to return (default: 10)

    Returns:
        list[dict]: Search results with title, url, and snippet
    """
    pass
```

**Why:** LLMs need clear descriptions to know when and how to use tools.

### Anti-Pattern 6: Blocking I/O in Sync Tools

❌ **WRONG:**
```python
@server.tool()
def fetch_url(url: str) -> str:
    response = requests.get(url)  # Blocking!
    return response.text
```

✓ **RIGHT:**
```python
@server.tool()
async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

**Why:** Blocking I/O prevents server from handling other requests.

### Anti-Pattern 7: Port Conflicts

❌ **WRONG:**
```env
# In .env
MCP_NEW_SERVER_PORT=8000  # Conflicts with web_search!
```

✓ **RIGHT:**
```env
# In .env
MCP_NEW_SERVER_PORT=8004  # Unique port!
```

**Why:** Port conflicts prevent servers from starting.

### Anti-Pattern 8: Not Loading dotenv

❌ **WRONG:**
```python
from mcp.server.fastmcp import FastMCP

# No load_dotenv()!
port = int(os.getenv('MCP_MY_PORT', 8000))
```

✓ **RIGHT:**
```python
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
port = int(os.getenv('MCP_MY_PORT', 8000))
```

**Why:** Environment variables won't be loaded from .env file.

### Anti-Pattern 9: Complex Logic in Tools

❌ **WRONG:**
```python
@server.tool()
async def do_everything(params: dict) -> dict:
    """Does everything."""
    # 200 lines of complex logic here...
    pass
```

✓ **RIGHT:**
```python
# In src/libs/my_module/processor.py
async def process_complex_task(params: dict) -> dict:
    # Complex logic here
    pass

# In server.py
from src.libs.my_module.processor import process_complex_task

@server.tool()
async def do_task(params: dict) -> dict:
    """Does task using helper library."""
    return await process_complex_task(params)
```

**Why:** Tools should delegate to libraries, not contain complex logic.

### Anti-Pattern 10: Inconsistent Return Types

❌ **WRONG:**
```python
@server.tool()
async def search(query: str) -> str:  # Says str
    """Searches."""
    return {"results": [...]}  # Returns dict!
```

✓ **RIGHT:**
```python
@server.tool()
async def search(query: str) -> dict:  # Says dict
    """Searches."""
    return {"results": [...]}  # Returns dict!
```

**Why:** Return type must match actual return value for proper tool schema generation.

---

## Code Generation Guide (For AI Assistants)

When generating an MCP server, follow these steps exactly:

### Step 1: Understand Requirements
- What tools will this server provide?
- What external services/APIs are needed?
- Will tools perform I/O operations (async) or pure computation (sync)?
- What port should this server use?

### Step 2: Choose Port Number
- Check existing servers: 8000-8003 are taken
- Use next available port (8004+)
- Add to .env: `MCP_{SERVER_NAME}_PORT={port}`

### Step 3: Create Directory Structure
```bash
mkdir -p src/mcp_servers/mcp_{server_name}
```

### Step 4: Generate server.py
1. Copy the [Default Implementation Pattern](#default-implementation-pattern) exactly
2. Replace placeholders:
   - `{server_name}` → your_server_name
   - `{SERVER_NAME}` → YOUR_SERVER_NAME (uppercase)
   - `{default_port}` → port number
   - `{Display Name}` → Human-readable name
3. Add tool functions with `@server.tool()`
4. Use `async def` for I/O tools, `def` for computation
5. Add comprehensive docstrings
6. Include print statements for logging

### Step 5: Generate __init__.py
```python
from .server import server

__all__ = ['server']
```

### Step 6: Generate Batch File
Create `start_{server_name}.bat` at project root:
```batch
@echo off
echo Starting {Server Display Name} MCP Server...
python -m src.mcp_servers.mcp_{server_name}.server
```

### Step 7: Add Environment Variable
Add to `.env.example` and update ENVIRONMENT.md blueprint:
```env
MCP_{SERVER_NAME}_PORT={port}
```

### Step 8: Test Server
1. Run: `python -m src.mcp_servers.mcp_{server_name}.server`
2. Verify output: "Server running on http://localhost:{port}"
3. Test with agent (add to mcp_config.json)

### Step 9: Validate Against Checklist
Use the [Validation Checklist](#validation-checklist) below.

---

## Validation Checklist

**IMPORTANT:** Before validating, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

Before completing MCP server implementation, verify:

### File Structure
- [ ] Directory created: `src/mcp_servers/mcp_{server_name}/`
- [ ] `__init__.py` exists and exports server
- [ ] `server.py` exists with complete implementation
- [ ] Batch file created at project root: `start_{server_name}.bat`

### Imports
- [ ] Import order correct: stdlib → dotenv → fastmcp → local
- [ ] `load_dotenv()` at module level (not in function)
- [ ] All required imports present
- [ ] No unused imports

### Server Initialization
- [ ] Port loaded from environment with default
- [ ] Port variable created (for debugging)
- [ ] FastMCP initialized with name and port
- [ ] Port number doesn't conflict with existing servers

### Tools
- [ ] All tools use `@server.tool()` with parentheses
- [ ] All tools have type hints for parameters
- [ ] All tools have return type hints
- [ ] All tools have comprehensive docstrings
- [ ] I/O tools are `async def`
- [ ] Computation tools are `def` (or `async def` if using async libs)
- [ ] Tools print progress/debug info
- [ ] Error handling appropriate for tool complexity

### Docstrings
- [ ] Each tool has docstring
- [ ] Docstring describes what tool does
- [ ] Parameters documented with types
- [ ] Return value documented with type
- [ ] Docstring is LLM-friendly (clear, specific)

### Main Guard
- [ ] `if __name__ == '__main__':` guard present
- [ ] `server.run(transport='streamable-http')` inside guard
- [ ] No server.run() at module level

### Environment Configuration
- [ ] Port variable added to .env
- [ ] Port follows naming convention: `MCP_{SERVER_NAME}_PORT`
- [ ] Default port in code matches .env
- [ ] Port documented in ENVIRONMENT.md blueprint

### Batch File
- [ ] Batch file created at project root
- [ ] File name: `start_{server_name}.bat`
- [ ] Echoes descriptive message
- [ ] Runs correct module path

### Code Quality
- [ ] No inline imports
- [ ] No unnecessary comments
- [ ] Consistent indentation
- [ ] Print statements for debugging/progress
- [ ] Follows KISS principle

### Integration
- [ ] Server can be added to agent mcp_config.json
- [ ] Tools automatically available to agents
- [ ] Port documented for other developers

---

## Agent Configuration

To use the MCP server in an agent:

1. Add it to the agent's `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

2. Load MCP servers in agent's `__init__`:

```python
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

servers = load_mcp_servers(load_mcp_config(__file__))

self.agent = Agent(
    llm_model,
    system_prompt=system_prompt,
    toolsets=servers
)
```

MCP tools are then automatically available to the agent without any additional code.

## Key Principles

### Tool Naming
- Use clear, descriptive function names
- Use snake_case for function names
- Keep names concise but meaningful

### Type Hints
- Always provide type hints for parameters
- Always provide return type hints
- Use appropriate types (str, int, bool, dict, list, etc.)

### Documentation
- Include comprehensive docstrings
- Document all parameters with types and descriptions
- Document return values
- Keep docstrings focused on what and why, not how

### Error Handling
- Let FastMCP handle most errors automatically
- Add specific error handling only when needed
- Print informative messages for debugging

### Async vs Sync
- Use `async def` when the tool performs I/O operations (web requests, file operations)
- Use regular `def` for pure computation or when using synchronous libraries
- FastMCP handles both patterns transparently

## Tool Registration

Tools are registered using the `@server.tool()` decorator:

```python
@server.tool()
async def my_tool(param: str) -> dict:
    """Tool description."""
    return {"result": param}
```

## Testing MCP Servers

### Start the Server

```bash
python -m src.mcp_servers.mcp_<server_name>.server
```

Or use the batch file:

```bash
start_<server_name>.bat
```

### Verify Server is Running

The server should output:
```
Starting <Server Name> MCP Server...
Server running on http://localhost:<port>
```

### Test from Agent

Use the server in an agent that has it configured in `mcp_config.json`:

```python
@agent.tool
async def use_mcp_tool(ctx: RunContext, input: str) -> str:
    """Uses the MCP server tool."""
    return await ctx.deps.mcp_client.call_tool("tool_name", {"arg1": input})
```

## Port Management

Default ports for Mythline MCP servers:
- 8000: Web Search MCP
- 8001: Web Crawler MCP
- 8002: Filesystem MCP
- 8003+: Available for new servers

## Best Practices

### Keep Servers Focused
- Each server should have a single responsibility
- Group related tools in the same server
- Don't create too many small servers

### Performance
- Use async operations for I/O-bound tasks
- Keep tool execution time reasonable
- Print progress for long-running operations

### Logging
- Print informative messages during tool execution
- Include relevant parameters in print statements
- Keep output concise but useful

### Dependencies
- Import only what's needed
- Use standard library when possible
- Document any external dependencies

### Security
- Validate input parameters
- Sanitize file paths for filesystem operations
- Avoid exposing sensitive data in responses

## Common Patterns

### Configuration Loading

```python
import os
from dotenv import load_dotenv

load_dotenv()
port = int(os.getenv('MCP_SERVER_PORT', 8000))
```

### Using Helper Libraries

```python
from src.libs.web.crawl import crawl_content
from src.libs.filesystem.file_operations import read_file

@server.tool()
async def use_helper(url: str) -> str:
    """Uses a helper library."""
    content = await crawl_content(url)
    return content
```

### Multiple Tools in One Server

```python
@server.tool()
async def tool_one(param: str) -> str:
    """First tool."""
    return f"Result: {param}"

@server.tool()
async def tool_two(param: int) -> int:
    """Second tool."""
    return param * 2

@server.tool()
async def tool_three(param: bool) -> dict:
    """Third tool."""
    return {"enabled": param}
```

## Integration with Agents

### Loading MCP Configuration

Load MCP servers in the agent's `__init__` method:

```python
import os
from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

load_dotenv()

llm_model = os.getenv('LLM_MODEL')
system_prompt = "Your system prompt"

servers = load_mcp_servers(load_mcp_config(__file__))

self.agent = Agent(
    llm_model,
    system_prompt=system_prompt,
    toolsets=servers
)
```

### Using MCP Tools

MCP tools are automatically available to the agent. The agent can call them directly by name in its reasoning process. You don't need to create wrapper tools or manually call MCP tools.

**Example:** If your MCP server has a `web_search` tool, the agent can use it automatically:

```python
# The agent will automatically have access to web_search tool
# No additional code needed - just ensure the MCP server is loaded via toolsets
```

If you want to create a custom tool that uses MCP functionality, you would call the MCP tool through the agent's normal tool mechanism (though this is rarely needed since the agent can use MCP tools directly).

## Troubleshooting

### Server Won't Start
- Check if port is already in use
- Verify `.env` has correct port configuration
- Check for syntax errors in server.py

### Agent Can't Connect
- Verify server is running
- Check `mcp_config.json` has correct URL
- Ensure port matches between `.env` and config

### Tool Not Found
- Verify tool is decorated with `@server.tool()`
- Check function name matches what agent is calling
- Ensure server restarted after adding tool

## Examples

See specific MCP blueprints:
- `web/mcp_web_search.md` - Web search with DuckDuckGo
- `web/mcp_web_crawler.md` - URL content extraction
- `filesystem/mcp_filesystem.md` - File and directory operations
