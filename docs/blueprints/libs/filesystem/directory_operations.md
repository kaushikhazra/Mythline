# Library: directory_operations

Directory management with metadata for MCP tools.

## Overview

**Location:** `src/libs/filesystem/directory_operations.py`

**Use when:** Listing directory contents, creating directories, file system exploration in MCP servers.

## Import

```python
from src.libs.filesystem.directory_operations import (
    list_directory, create_directory, file_exists
)
```

## Functions

### list_directory(path: str) -> str
List directory contents with metadata in CSV format.

**Returns:** CSV string with columns: name, path, is_dir, is_file, is_symlink, size, modified_time, created_time

### create_directory(path: str) -> str
Create directory recursively.

### file_exists(path: str) -> str
Check if path exists (file or directory).

## Usage Example

```python
# Create output directory
create_directory('output/stories/session_001')

# List contents
listing = list_directory('output/stories')
```

## CSV Output Format
```
name,path,is_dir,is_file,is_symlink,size,modified_time,created_time
story.md,/path/story.md,False,True,False,1024,2024-11-13T10:30:00,2024-11-12T09:00:00
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Examples in Codebase
- MCP filesystem server
