# CLI Common Components

This document contains shared components used across all CLI patterns in Pydantic AI projects.

## Overview

All CLIs follow consistent patterns for imports, argument parsing, session management, and agent instantiation. Use this as a reference when building any CLI interface.

---

## Standard Import Structure

All CLIs organize imports in the following order:

```python
# Standard library imports
import os
import sys
import argparse
import asyncio
from datetime import datetime

# Third-party imports
from tqdm import tqdm
from termcolor import colored

# Agent imports
from src.agents.{agent_name}.agent import {AgentClass}

# Utility imports
from src.libs.utils.argument_parser import get_arguments
from src.libs.filesystem.file_operations import read_file, append_file
from src.libs.utils.markdown_parser import parse_markdown
```

**Rules:**
- All imports at the top of file
- No inline imports
- Group by type (standard → third-party → local)

---

## Argument Parser Utility

### Shared Utility: `get_arguments()`

**Location:** `src/libs/utils/argument_parser.py`

**Signature:**
```python
@dataclass
class CLIArgs:
    session_id: str
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    verbose: bool = False

def get_arguments(
    agent_id: str,
    description: str = "CLI Application",
    require_input: bool = False,
    require_output: bool = False
) -> CLIArgs
```

### Usage Patterns

**Basic Usage (Interactive CLI):**
```python
from src.libs.utils.argument_parser import get_arguments

args = get_arguments(
    agent_id={AgentClass}.AGENT_ID,
    description='{Agent} CLI'
)
```

**With Required Input/Output (Batch CLI):**
```python
args = get_arguments(
    agent_id='shot_creator',
    description='Shot Generator CLI',
    require_input=True,
    require_output=True
)
```

**Custom Argument Parser (Non-Interactive CLI):**
```python
import argparse

parser = argparse.ArgumentParser(description='Story Creator CLI')
parser.add_argument('--subject', '-s', type=str, required=True, help='Story subject')
parser.add_argument('--player', '-p', type=str, required=True, help='Player character name')
args = parser.parse_args()
```

### Command-Line Arguments Provided

The `get_arguments()` utility provides:

- `--session <session_id>` - Use specific session ID
- `--resume` - Resume from latest session
- `-i, --input <file>` - Input file path (if `require_input=True`)
- `-o, --output <file>` - Output file path (if `require_output=True`)
- `-v, --verbose` - Enable verbose output

**Session Management:**
- If no `--session` or `--resume`: Creates new session with timestamp (`YYYYMMDD_HHMMSS`)
- If `--resume`: Retrieves latest session for the agent
- If `--session <id>`: Uses specified session ID

---

## Session Management

### Display Session ID

**Pattern:**
```python
print(f"Session: {args.session_id}\n")
```

**Usage:** All interactive CLIs display session at startup.

### Session-based Directory Structure

Context memory is stored per session:
```
.mythline/
└── {agent_id}/
    └── context_memory/
        └── {session_id}.json
```

---

## Agent Instantiation

### Stateful Agents (With Session)

For agents that maintain conversation context:

```python
from src.agents.{agent_name}.agent import {AgentClass}

agent = {AgentClass}(session_id=args.session_id)
```

**Examples:**
- `StoryResearcher(session_id)`
- `VideoDirector(session_id)`
- `StoryCreatorAgent(session_id, player_name)`

### Stateless Agents (No Session)

For agents that process each input independently:

```python
from src.agents.shot_creator_agent.agent import ShotCreator

agent = ShotCreator()
```

**Examples:**
- `ShotCreator()`
- `UserPreferenceAgent()`

---

## Agent Execution Patterns

### Synchronous Execution

**Pattern:**
```python
response = agent.run(prompt)
output = response.output
```

**Usage:** Most CLIs use synchronous execution.

### Asynchronous Execution

**Pattern:**
```python
async def main():
    agent = {AgentClass}(session_id=args.session_id)
    response = await agent.run_async(prompt)
    output = response.output

asyncio.run(main())
```

**Usage:** Non-interactive CLIs with long-running operations.

---

## Error Handling

### Graceful Error Handling with Resume

**Pattern (Async CLIs):**
```python
try:
    await agent.run(subject=args.subject)
    print("\n" + "=" * 50)
    print("Operation complete!")
    print("=" * 50)
    sys.exit(0)
except Exception as e:
    print("\n" + "=" * 50)
    print(f"Error during operation:")
    print("=" * 50)
    traceback.print_exc()
    print("=" * 50)
    print(f"Session saved. You can resume by running the same command again.")
    print("=" * 50)
    sys.exit(1)
```

**Usage:** Provides clear error messages and guides user to resume.

### Colored Error Messages

**Pattern (Utility CLIs):**
```python
from termcolor import colored

try:
    operation()
    print(colored(f"Success message", "green"))
except Exception as e:
    print(colored(f"Error: {str(e)}", "red"))
```

---

## Output Formatting

### Emoji Prefixes

**Pattern:**
```python
# User input
prompt = input("🙍 User: ")

# Agent output
print(f"\n✏️  Agent: {response.output} \n\n")
```

**Common Emojis:**
- 🙍 User
- ✏️ Story Researcher
- 🤖 Generic Agent
- 🎬 Video Director

### Visual Separators

**Progress separators:**
```python
print("-" * 50)
```

**Completion/Error separators:**
```python
print("=" * 50)
```

**Section headers:**
```python
print(f"\n{'='*60}")
print(f"SECTION TITLE")
print(f"{'='*60}\n")
```

### Colored Output

**Pattern:**
```python
from termcolor import colored

print(colored("Information message", "cyan"))
print(colored("Warning message", "yellow"))
print(colored("Success message", "green"))
print(colored("Error message", "red"))
```

---

## Progress Indication

### Progress Bar (Batch Processing)

**Pattern:**
```python
from tqdm import tqdm

for i, item in tqdm(enumerate(items, 1), total=len(items), desc="Processing items"):
    process(item)
```

### Status Messages

**Pattern:**
```python
print(f"Starting operation for: {args.subject}")
print(f"Session ID: {session_id}")
print(f"Input file: {input_path}")
print("-" * 50)
```

---

## File Operations

### Read File

**Pattern:**
```python
from src.libs.filesystem.file_operations import read_file

content = read_file(file_path)
```

### Append to File

**Pattern:**
```python
from src.libs.filesystem.file_operations import append_file

append_file(output_file, content + '\n')
```

### File Existence Check

**Pattern:**
```python
import os

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
    sys.exit(1)
```

---

## Module Execution Pattern

All CLIs use module execution:

```bash
python -m src.ui.cli.{cli_name}
```

**File Structure:**
```python
# All imports

# Argument parsing

# Agent instantiation

# Main logic

# No if __name__ == '__main__' needed for simple CLIs
# Use it only for CLIs with helper functions
```

---

## Exit Handling

### Interactive CLI Exit

**Pattern:**
```python
while True:
    prompt = input("User: ")

    if prompt == "exit":
        print(f"\n✏️  Agent: Good Bye!! \n\n")
        break
```

**Flexible exit conditions:**
```python
if user_input.lower() in ["exit", "quit"]:
    print(f"\n🎬 Agent: That's a wrap! Good work.\n\n")
    break
```

### Non-Interactive CLI Exit

**Pattern:**
```python
sys.exit(0)  # Success
sys.exit(1)  # Error
```

---

## Prerequisite Validation

**Pattern:**
```python
prerequisite_path = f"output/{args.subject}/required_file.md"
if not os.path.exists(prerequisite_path):
    print(f"Error: Required file not found at {prerequisite_path}")
    print(f"Please run prerequisite_step first.")
    sys.exit(1)
```

---

## Complete Minimal Example

```python
from src.agents.example_agent.agent import ExampleAgent
from src.libs.utils.argument_parser import get_arguments

args = get_arguments(
    agent_id=ExampleAgent.AGENT_ID,
    description='Example CLI'
)

print(f"Session: {args.session_id}\n")
agent = ExampleAgent(args.session_id)

while True:
    prompt = input("🙍 User: ")

    if prompt == "exit":
        print(f"\n🤖 Agent: Good Bye!! \n\n")
        break

    response = agent.run(prompt)
    print(f"\n🤖 Agent: {response.output} \n\n")
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Reference

This document provides the building blocks. Refer to specific CLI pattern templates for complete implementations:

- `interface_cli_interactive.md` - Simple interactive loop
- `interface_cli_interactive_initial_run.md` - Interactive with initial execution
- `interface_cli_async.md` - Async single execution
- `interface_cli_batch.md` - Batch processing
- `interface_cli_subcommand.md` - Utility with subcommands
