# Library: file_operations

Safe file I/O operations with error handling.

## Overview

**Purpose:** Provides consistent, error-handled file operations for reading, writing, and managing files.

**Location:** `src/libs/filesystem/file_operations.py`

**Use when:** Reading input files, writing output files, file management in CLIs and MCP servers.

## Import

```python
from src.libs.filesystem.file_operations import (
    read_file, write_file, append_file,
    file_exists, rename_file, delete_file
)
```

## Functions

### read_file(path: str) -> str
Read entire file content.

**Returns:** File content as string, or error message string

### write_file(path: str, content: str) -> str  
Write/overwrite file.

**Returns:** Success message or error message

### append_file(path: str, content: str) -> str
Append to existing file.

**Returns:** Success message or error message

### file_exists(path: str) -> bool
Check if file exists.

### rename_file(old_path: str, new_path: str) -> str
Rename/move file.

### delete_file(path: str) -> str
Delete file.

## Usage Examples

```python
# Read input
story = read_file('output/story.md')

# Write output
write_file('output/shots.md', shots_content)

# Incremental writing
for shot in shots:
    append_file('output/shots.md', shot + '\n')
```

## Error Handling

Returns error strings (for MCP tools):
- "Error: File not found: {path}"
- "Error: Permission denied: {path}"
- "Error: Cannot decode file: {path}"

## Examples in Codebase
- All CLI scripts (read/write files)
- MCP filesystem server
- generate_shots CLI (append mode)
