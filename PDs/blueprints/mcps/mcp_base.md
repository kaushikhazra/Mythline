# MCP Server Base Blueprint

This blueprint provides the foundational structure for creating MCP (Model Context Protocol) servers using FastMCP in the Mythline project.

## Overview

MCP servers expose tools and functionality to AI agents through a standardized protocol. Each MCP server is a standalone service that runs on its own port and can be accessed by agents through their `mcp_config.json` configuration.

## Base Structure

```
src/mcp_servers/mcp_<server_name>/
├── __init__.py
└── server.py

start_<server_name>.bat (at project root)
```

## Basic Server Template

### `server.py`

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

This file should be placed at the root of the project for easy access.

## Environment Configuration

Add the server port to `.env`:

```
MCP_<SERVER_NAME>_PORT=8000
```

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
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

llm_model = "openai:gpt-4o"
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
