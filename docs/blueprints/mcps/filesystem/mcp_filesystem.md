# MCP Filesystem Server Blueprint

This blueprint provides a comprehensive MCP server for file and directory operations.

## Overview

The Filesystem MCP server provides tools for reading, writing, and managing files and directories. It offers a safe, controlled interface for AI agents to interact with the filesystem.

## Structure

```
src/mcp_servers/mcp_filesystem/
├── __init__.py
└── server.py

start_filesystem.bat (at project root)
```

## Implementation

### `server.py`

```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.filesystem.file_operations import read_file, write_file, append_file
from src.libs.filesystem.directory_operations import list_directory, create_directory, file_exists

load_dotenv()

port = int(os.getenv('MCP_FILESYSTEM_PORT', 8002))
server = FastMCP(name="Filesystem MCP", port=port)

@server.tool()
def read(path: str) -> str:
    """Reads the content of a file.

    Args:
        path (str): The file path to read from

    Returns:
        str: The content of the file
    """
    print(f"Reading file: {path}")
    return read_file(path)

@server.tool()
def write(path: str, content: str) -> bool:
    """Writes content to a file, overwriting existing content.

    Args:
        path (str): The file path to write to
        content (str): The content to write

    Returns:
        bool: True if successful
    """
    print(f"Writing to file: {path}")
    return write_file(path, content)

@server.tool()
def append(path: str, content: str) -> bool:
    """Appends content to the end of a file.

    Args:
        path (str): The file path to append to
        content (str): The content to append

    Returns:
        bool: True if successful
    """
    print(f"Appending to file: {path}")
    return append_file(path, content)

@server.tool()
def list_dir(path: str) -> list:
    """Lists all files and directories in a directory.

    Args:
        path (str): The directory path to list

    Returns:
        list: List of file and directory names
    """
    print(f"Listing directory: {path}")
    return list_directory(path)

@server.tool()
def create_dir(path: str) -> bool:
    """Creates a directory, including parent directories if needed.

    Args:
        path (str): The directory path to create

    Returns:
        bool: True if successful
    """
    print(f"Creating directory: {path}")
    return create_directory(path)

@server.tool()
def exists(path: str) -> bool:
    """Checks if a file or directory exists.

    Args:
        path (str): The file or directory path to check

    Returns:
        bool: True if exists, False otherwise
    """
    print(f"Checking existence: {path}")
    return file_exists(path)

if __name__=='__main__':
    server.run(transport='streamable-http')
```

### `__init__.py`

```python
from .server import server

__all__ = ['server']
```

### `start_filesystem.bat` (at project root)

```batch
@echo off
echo Starting Filesystem MCP Server...
python -m src.mcp_servers.mcp_filesystem.server
```

This file should be placed at the root of the project for easy access.

## Configuration

### Environment Variables

Add to `.env`:

```
MCP_FILESYSTEM_PORT=8002
```

### Agent Configuration

Add to agent's `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "url": "http://localhost:8002/mcp"
    }
  }
}
```

## Available Tools

### File Operations

#### read(path: str) -> str
Reads and returns file content. The agent uses this tool automatically when instructed to read files.

#### write(path: str, content: str) -> bool
Writes content to a file, overwriting existing content. The agent uses this tool automatically when instructed to write files.

#### append(path: str, content: str) -> bool
Appends content to the end of a file. The agent uses this tool automatically when instructed to append to files.

### Directory Operations

#### list_dir(path: str) -> list
Lists all files and directories in a directory. The agent uses this tool automatically when instructed to list directory contents.

#### create_dir(path: str) -> bool
Creates a directory and any necessary parent directories. The agent uses this tool automatically when instructed to create directories.

#### exists(path: str) -> bool
Checks if a file or directory exists. The agent uses this tool automatically when instructed to check file/directory existence.

## Usage in Agents

### Agent Integration

Load the MCP server in the agent's `__init__` method:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

class StorageAgent:
    AGENT_ID = "storage_agent"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )
```

### Using the Tools

All filesystem tools are automatically available to the agent. Instruct the agent about these capabilities in the system prompt.

**System Prompt Example:**
```markdown
You have access to the following filesystem tools:
- read(path): Read content from a file
- write(path, content): Write content to a file (overwrites existing)
- append(path, content): Append content to end of file
- list_dir(path): List files and directories
- create_dir(path): Create a directory
- exists(path): Check if file or directory exists

Use these tools to manage files and directories as needed.
```

The agent will automatically use the appropriate tools based on the task.

## Dependencies

### Required Libraries

```python
from src.libs.filesystem.file_operations import read_file, write_file, append_file
from src.libs.filesystem.directory_operations import list_directory, create_directory, file_exists
```

### Helper Functions

The filesystem helper functions handle:
- Path validation
- Error handling
- Directory creation
- File encoding
- Cross-platform compatibility

## Best Practices

### Path Handling

```python
import os

@server.tool()
def read(path: str) -> str:
    """Reads file with normalized path."""
    normalized_path = os.path.normpath(path)
    print(f"Reading file: {normalized_path}")
    return read_file(normalized_path)
```

### Error Handling

```python
@server.tool()
def read(path: str) -> str:
    """Reads file with error handling."""
    try:
        print(f"Reading file: {path}")

        if not file_exists(path):
            return f"Error: File not found: {path}"

        content = read_file(path)
        return content

    except Exception as e:
        error_msg = f"Error reading {path}: {str(e)}"
        print(error_msg)
        return error_msg
```

### Safe Writing

```python
@server.tool()
def write(path: str, content: str) -> bool:
    """Writes file with directory creation."""
    try:
        print(f"Writing to file: {path}")

        directory = os.path.dirname(path)
        if directory and not file_exists(directory):
            create_directory(directory)

        return write_file(path, content)

    except Exception as e:
        print(f"Error writing {path}: {e}")
        return False
```

## Customization Options

### File Metadata

```python
import os
from datetime import datetime

@server.tool()
def get_file_info(path: str) -> dict:
    """Gets detailed file information."""
    print(f"Getting info for: {path}")

    if not file_exists(path):
        return {"error": "File not found"}

    stat = os.stat(path)

    return {
        "path": path,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "is_file": os.path.isfile(path),
        "is_directory": os.path.isdir(path)
    }
```

### Pattern Matching

```python
import glob

@server.tool()
def find_files(pattern: str) -> list:
    """Finds files matching a pattern."""
    print(f"Finding files matching: {pattern}")
    return glob.glob(pattern)
```

### Batch Operations

```python
@server.tool()
def read_multiple(paths: list[str]) -> dict:
    """Reads multiple files."""
    print(f"Reading {len(paths)} files...")

    results = {}

    for path in paths:
        try:
            results[path] = read_file(path)
        except Exception as e:
            results[path] = f"Error: {str(e)}"

    return results
```

### Content Search

```python
@server.tool()
def search_in_file(path: str, search_term: str) -> list:
    """Searches for a term in a file."""
    print(f"Searching for '{search_term}' in {path}")

    content = read_file(path)
    lines = content.split('\n')

    matches = []
    for i, line in enumerate(lines, 1):
        if search_term in line:
            matches.append({
                "line_number": i,
                "content": line
            })

    return matches
```

## Advanced Features

### Backup Before Write

```python
import shutil

@server.tool()
def write_with_backup(path: str, content: str) -> bool:
    """Writes file with automatic backup."""
    print(f"Writing to file with backup: {path}")

    if file_exists(path):
        backup_path = f"{path}.backup"
        shutil.copy2(path, backup_path)
        print(f"Created backup: {backup_path}")

    return write_file(path, content)
```

### Atomic Write

```python
import tempfile
import shutil

@server.tool()
def write_atomic(path: str, content: str) -> bool:
    """Writes file atomically."""
    print(f"Writing atomically to: {path}")

    directory = os.path.dirname(path) or '.'

    with tempfile.NamedTemporaryFile(mode='w', dir=directory, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    shutil.move(tmp_path, path)

    print(f"Atomic write completed: {path}")

    return True
```

### Directory Tree

```python
@server.tool()
def get_tree(path: str, max_depth: int = 3) -> dict:
    """Gets directory tree structure."""
    print(f"Getting tree for: {path}")

    def build_tree(current_path: str, depth: int = 0):
        if depth >= max_depth:
            return None

        if not os.path.isdir(current_path):
            return None

        tree = {}

        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)

            if os.path.isdir(item_path):
                tree[item] = build_tree(item_path, depth + 1)
            else:
                tree[item] = None

        return tree

    return build_tree(path)
```

### File Comparison

```python
import difflib

@server.tool()
def compare_files(path1: str, path2: str) -> dict:
    """Compares two files."""
    print(f"Comparing {path1} and {path2}")

    content1 = read_file(path1).splitlines()
    content2 = read_file(path2).splitlines()

    diff = list(difflib.unified_diff(content1, content2, lineterm=''))

    return {
        "identical": content1 == content2,
        "diff_lines": len(diff),
        "diff": '\n'.join(diff)
    }
```

## Testing

### Start Server

```bash
python -m src.mcp_servers.mcp_filesystem.server
```

Or:

```bash
start_filesystem.bat
```

### Test Operations

```python
from src.mcp_servers.mcp_filesystem.server import write, read, exists

write("test.txt", "Hello World")

content = read("test.txt")
print(content)

file_exists = exists("test.txt")
print(f"Exists: {file_exists}")
```

### Verify Agent Integration

Test that agents can:
1. Read existing files
2. Write new files
3. Append to files
4. List directories
5. Create directories
6. Check file existence

## Common Use Cases

### Story Storage

**System Prompt:**
```markdown
When saving stories:
1. Use create_dir to ensure the stories directory exists
2. Use write to save the story content to a file
3. Format filenames by replacing spaces with underscores
```

### Session Logging

**System Prompt:**
```markdown
For logging interactions:
1. Format log entries with timestamp
2. Use append to add entries to the log file
3. Keep entries on separate lines
```

### Configuration Management

**System Prompt:**
```markdown
For configuration management:
1. Use write to save configuration as JSON
2. Use read to load configuration
3. Parse JSON content appropriately
```

### Data Export

**System Prompt:**
```markdown
For data export:
1. Format data appropriately (CSV, JSON, etc.)
2. Use create_dir to ensure export directory exists
3. Use write to save exported data
```

The agent will automatically use the filesystem tools based on these instructions.

## Security Considerations

### Path Traversal Prevention

```python
import os

def validate_path(path: str, base_dir: str = "data") -> bool:
    """Validates path is within base directory."""
    abs_path = os.path.abspath(path)
    abs_base = os.path.abspath(base_dir)

    return abs_path.startswith(abs_base)

@server.tool()
def read(path: str) -> str:
    """Reads file with path validation."""
    if not validate_path(path):
        return "Error: Access denied"

    print(f"Reading file: {path}")
    return read_file(path)
```

### File Size Limits

```python
@server.tool()
def read(path: str, max_size: int = 10_000_000) -> str:
    """Reads file with size limit."""
    if not file_exists(path):
        return "Error: File not found"

    size = os.path.getsize(path)

    if size > max_size:
        return f"Error: File too large ({size} bytes)"

    print(f"Reading file: {path}")
    return read_file(path)
```

## Performance Considerations

### Lazy Reading

```python
@server.tool()
def read_chunk(path: str, offset: int = 0, size: int = 1024) -> str:
    """Reads a chunk of a file."""
    print(f"Reading chunk from {path} at offset {offset}")

    with open(path, 'r') as f:
        f.seek(offset)
        return f.read(size)
```

### Streaming Large Files

```python
@server.tool()
def read_lines(path: str, limit: int = 100) -> list:
    """Reads first N lines of a file."""
    print(f"Reading {limit} lines from {path}")

    lines = []

    with open(path, 'r') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            lines.append(line.rstrip())

    return lines
```

## Troubleshooting

### Permission Denied

- Check file permissions
- Verify directory access
- Run with appropriate privileges

### File Not Found

- Verify path is correct
- Check directory exists
- Use absolute paths

### Encoding Issues

- Specify encoding explicitly
- Handle special characters
- Use UTF-8 by default

## Related Blueprints

- `mcp_base.md` - Base MCP server structure
- `web/mcp_web_crawler.md` - Web content operations
- `web/mcp_web_search.md` - Web search operations
