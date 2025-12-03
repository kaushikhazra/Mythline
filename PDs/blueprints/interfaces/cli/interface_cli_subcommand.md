# CLI Pattern: Subcommand Utility

## Overview

This pattern creates a utility CLI with multiple subcommands, each performing a different operation. Ideal for management tools, administrative utilities, and CLIs that provide multiple related functions.

**Use this pattern when:**
- Multiple related operations in one CLI tool
- Each operation has different parameters
- Building management or utility tools
- No agent needed (direct library function calls)
- Want organized command structure

**Example in codebase:**
- `src/ui/cli/manage_knowledge_base.py` - Knowledge base management with load, rebuild, search, list, clear commands

---

## Common Components Template

```python
# ============================================================
# IMPORTS
# ============================================================
import argparse
from termcolor import colored
from {library_module} import {function1}, {function2}, {function3}


# ============================================================
# COMMAND HANDLER FUNCTIONS
# ============================================================
def command1_handler(args):
    print(colored(f"Starting {command1}...", "cyan"))

    # CUSTOMIZE: Add validation or confirmation
    if {requires_confirmation}:
        print(colored("Warning: This action will...", "yellow"))
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    try:
        result = {function1}(args.{param1})
        print(colored(f"Success: {result}", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def command2_handler(args):
    print(colored(f"Starting {command2}...", "cyan"))

    try:
        result = {function2}(args.{param1}, args.{param2})
        print(colored(f"Result: {result}", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


# Add handler for each subcommand...


# ============================================================
# MAIN FUNCTION WITH ARGUMENT PARSING
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="{Utility Name} - {Description}"
    )
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands'
    )

    # COMMAND 1
    command1_parser = subparsers.add_parser(
        '{command1}',
        help='{Command 1 description}'
    )
    command1_parser.add_argument(
        '--{param1}',
        default='{default_value}',
        help='{Parameter description}'
    )

    # COMMAND 2
    command2_parser = subparsers.add_parser(
        '{command2}',
        help='{Command 2 description}'
    )
    command2_parser.add_argument(
        '--{param1}',
        required=True,
        help='{Parameter description}'
    )
    command2_parser.add_argument(
        '--{param2}',
        type=int,
        default=10,
        help='{Parameter description}'
    )

    # Add parser for each subcommand...

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Command dispatch
    commands = {
        '{command1}': command1_handler,
        '{command2}': command2_handler,
        # Add mapping for each command...
    }

    commands[args.command](args)


# ============================================================
# EXECUTION
# ============================================================
if __name__ == '__main__':
    main()
```

---

## Function-Specific Customization Points

### 1. Library Imports
```python
# CUSTOMIZE: Import functions your commands will use
from {library_module} import {function1}, {function2}, {function3}
```

**Examples:**
```python
from src.libs.knowledge_base.knowledge_vectordb import (
    index_knowledge, search_knowledge, list_all_chunks,
    clear_collection, collection_exists
)

from src.libs.database.operations import create, read, update, delete
from src.libs.utils.config_manager import load_config, save_config
```

### 2. Command Handler Pattern
```python
# CUSTOMIZE: Create handler function for each command
def {command}_handler(args):
    print(colored(f"Starting {command}...", "cyan"))

    try:
        result = {library_function}(args.param)
        print(colored(f"Success!", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))
```

### 3. Validation and Confirmation
```python
# CUSTOMIZE: Add checks before executing
if collection_exists(args.knowledge_dir):
    print(colored("Warning: Collection already exists.", "yellow"))
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
```

### 4. Subcommand Definition
```python
# CUSTOMIZE: Define each subcommand with its arguments
{command}_parser = subparsers.add_parser(
    '{command}',
    help='{Command description}'
)
{command}_parser.add_argument(
    '--{param}',
    type={type},
    required={True/False},
    default={default_value},
    help='{Parameter description}'
)
```

**Examples:**
```python
# Simple command with optional argument
load_parser = subparsers.add_parser('load', help='Load knowledge from directory')
load_parser.add_argument('--knowledge-dir', default='guides', help='Directory')

# Command with required argument
search_parser = subparsers.add_parser('search', help='Search knowledge base')
search_parser.add_argument('--query', required=True, help='Search query')

# Command with multiple arguments
create_parser = subparsers.add_parser('create', help='Create new item')
create_parser.add_argument('--name', required=True, help='Item name')
create_parser.add_argument('--type', choices=['a', 'b', 'c'], help='Item type')
create_parser.add_argument('--count', type=int, default=1, help='Quantity')
```

### 5. Command Dispatch Dictionary
```python
# CUSTOMIZE: Map command names to handler functions
commands = {
    '{command1}': {command1}_handler,
    '{command2}': {command2}_handler,
    '{command3}': {command3}_handler,
}
```

### 6. Output Formatting
```python
# CUSTOMIZE: Use colored output for different message types
print(colored("Information message", "cyan"))
print(colored("Warning message", "yellow"))
print(colored("Success message", "green"))
print(colored("Error message", "red"))
```

---

## Complete Working Example

**File:** `src/ui/cli/manage_knowledge_base.py`

```python
import argparse
from termcolor import colored
from src.libs.knowledge_base.knowledge_vectordb import (
    index_knowledge, search_knowledge, list_all_chunks,
    clear_collection, collection_exists
)

def load_command(args):
    print(colored(f"Loading knowledge from '{args.knowledge_dir}' into knowledge base...", "cyan"))
    if collection_exists(args.knowledge_dir):
        print(colored("Warning: Collection already exists. Use 'rebuild' to regenerate.", "yellow"))
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    try:
        num_chunks = index_knowledge(args.knowledge_dir)
        print(colored(f"Successfully indexed {num_chunks} chunks from '{args.knowledge_dir}'", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))

def rebuild_command(args):
    print(colored(f"Rebuilding knowledge base from '{args.knowledge_dir}'...", "cyan"))
    try:
        clear_collection(args.knowledge_dir)
        num_chunks = index_knowledge(args.knowledge_dir)
        print(colored(f"Successfully rebuilt with {num_chunks} chunks", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))

def search_command(args):
    print(colored(f"Searching for: '{args.query}'", "cyan"))
    try:
        results = search_knowledge(args.query, args.knowledge_dir, n_results=args.results)
        print(colored(f"\nFound {len(results)} results:", "green"))
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(result)
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))

def list_command(args):
    print(colored(f"Listing all chunks from '{args.knowledge_dir}'...", "cyan"))
    try:
        chunks = list_all_chunks(args.knowledge_dir)
        print(colored(f"\nTotal chunks: {len(chunks)}", "green"))
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))

def clear_command(args):
    print(colored(f"WARNING: This will delete all data from '{args.knowledge_dir}' collection!", "yellow"))
    response = input("Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    try:
        clear_collection(args.knowledge_dir)
        print(colored(f"Successfully cleared collection '{args.knowledge_dir}'", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))

def main():
    parser = argparse.ArgumentParser(description="Manage knowledge bases")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    load_parser = subparsers.add_parser('load', help='Load knowledge from directory')
    load_parser.add_argument('--knowledge-dir', default='guides', help='Directory containing knowledge files')

    rebuild_parser = subparsers.add_parser('rebuild', help='Rebuild knowledge base from scratch')
    rebuild_parser.add_argument('--knowledge-dir', default='guides', help='Directory containing knowledge files')

    search_parser = subparsers.add_parser('search', help='Search the knowledge base')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--knowledge-dir', default='guides', help='Knowledge base to search')
    search_parser.add_argument('--results', type=int, default=5, help='Number of results to return')

    list_parser = subparsers.add_parser('list', help='List all chunks in knowledge base')
    list_parser.add_argument('--knowledge-dir', default='guides', help='Knowledge base to list')

    clear_parser = subparsers.add_parser('clear', help='Clear all data from knowledge base')
    clear_parser.add_argument('--knowledge-dir', default='guides', help='Knowledge base to clear')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'load': load_command,
        'rebuild': rebuild_command,
        'search': search_command,
        'list': list_command,
        'clear': clear_command
    }

    commands[args.command](args)

if __name__ == '__main__':
    main()
```

---

## Usage

### Displaying Help

```bash
# Show all available commands
python -m src.ui.cli.manage_knowledge_base

# Show help for specific command
python -m src.ui.cli.manage_knowledge_base search --help
```

### Running Commands

```bash
# Load knowledge with default directory
python -m src.ui.cli.manage_knowledge_base load

# Load from specific directory
python -m src.ui.cli.manage_knowledge_base load --knowledge-dir custom_guides

# Search knowledge base
python -m src.ui.cli.manage_knowledge_base search --query "pydantic ai" --results 10

# Rebuild knowledge base
python -m src.ui.cli.manage_knowledge_base rebuild --knowledge-dir guides

# List all chunks
python -m src.ui.cli.manage_knowledge_base list

# Clear knowledge base (requires confirmation)
python -m src.ui.cli.manage_knowledge_base clear --knowledge-dir guides
```

### Example Interactions

**Load command:**
```
$ python -m src.ui.cli.manage_knowledge_base load --knowledge-dir guides
Loading knowledge from 'guides' into knowledge base...
Successfully indexed 127 chunks from 'guides'
```

**Search command:**
```
$ python -m src.ui.cli.manage_knowledge_base search --query "agent patterns"
Searching for: 'agent patterns'

Found 3 results:

--- Result 1 ---
Agent patterns include stateful agents with session management...

--- Result 2 ---
Common agent patterns: orchestrator agents, sub-agents...
```

**Clear command with confirmation:**
```
$ python -m src.ui.cli.manage_knowledge_base clear
WARNING: This will delete all data from 'guides' collection!
Are you sure? (yes/no): yes
Successfully cleared collection 'guides'
```

---

## Key Features

### Subcommand Structure
- Each operation is a separate subcommand
- Clean, organized command structure
- Easy to extend with new commands

### Colored Output
- Cyan for informational messages
- Yellow for warnings
- Green for success
- Red for errors

### User Confirmation
- Destructive operations require explicit confirmation
- Prevents accidental data loss
- Clear warning messages

### Flexible Arguments
- Each subcommand has its own arguments
- Optional and required parameters
- Default values for common arguments

### Error Handling
- Try/except in each handler
- Clear error messages
- Non-zero exit for errors (implicit)

---

## Decision Guide

**Choose this pattern if:**
- ✅ Multiple related operations
- ✅ Each operation has different parameters
- ✅ Building utility or management tool
- ✅ No agent needed (direct function calls)
- ✅ Want organized command structure

**Choose a different pattern if:**
- ❌ Single operation → Use `interface_cli_async.md`
- ❌ Need conversation loop → Use `interface_cli_interactive.md`
- ❌ Batch file processing → Use `interface_cli_batch.md`
- ❌ Need agent with context → Use interactive patterns

---

## Related Patterns

- **interface_cli_common.md** - Shared components reference
- **interface_cli_async.md** - Single async operation
- **interface_cli_batch.md** - Batch processing

---

## Common Modifications

### Add Global Arguments

```python
parser = argparse.ArgumentParser(description="Manage knowledge bases")
parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
parser.add_argument('--config', '-c', type=str, help='Config file path')

subparsers = parser.add_subparsers(dest='command', help='Available commands')
# ... define subcommands

args = parser.parse_args()

if args.verbose:
    print("Verbose mode enabled")

commands[args.command](args)
```

### Add Dry-Run Mode

```python
parser.add_argument('--dry-run', action='store_true', help='Show what would happen')

def clear_command(args):
    if args.dry_run:
        print(colored("DRY RUN: Would clear collection", "yellow"))
        return

    # Actual operation
    clear_collection(args.knowledge_dir)
```

### Add Output Formatting Options

```python
search_parser.add_argument(
    '--format',
    choices=['text', 'json', 'table'],
    default='text',
    help='Output format'
)

def search_command(args):
    results = search_knowledge(args.query)

    if args.format == 'json':
        import json
        print(json.dumps(results, indent=2))
    elif args.format == 'table':
        from tabulate import tabulate
        print(tabulate(results, headers='keys'))
    else:
        for result in results:
            print(result)
```

### Add Logging

```python
import logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log-level', default='INFO', help='Logging level')

    # ... setup subparsers

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)

    logger.info(f"Executing command: {args.command}")
    commands[args.command](args)
```

### Add Command Aliases

```python
commands = {
    'load': load_command,
    'l': load_command,  # Alias
    'search': search_command,
    's': search_command,  # Alias
    'rebuild': rebuild_command,
    'r': rebuild_command,  # Alias
}
```

---

## Advanced Variations

### Command Chaining

```python
parser.add_argument('--chain', nargs='+', help='Chain multiple commands')

args = parser.parse_args()

if args.chain:
    for cmd in args.chain:
        print(f"\nExecuting: {cmd}")
        commands[cmd](args)
else:
    commands[args.command](args)
```

### Configuration File Support

```python
import json

def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Config file')
    # ... subparsers

    args = parser.parse_args()

    if args.config:
        config = load_config(args.config)
        for key, value in config.items():
            if not hasattr(args, key) or getattr(args, key) is None:
                setattr(args, key, value)

    commands[args.command](args)
```

### Interactive Mode

```python
def interactive_mode():
    print("Entering interactive mode. Type 'help' for commands, 'exit' to quit.")

    while True:
        try:
            user_input = input("\n> ").strip()

            if user_input == 'exit':
                break

            if user_input == 'help':
                parser.print_help()
                continue

            args = parser.parse_args(user_input.split())
            commands[args.command](args)

        except Exception as e:
            print(colored(f"Error: {str(e)}", "red"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    # ... subparsers

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.command:
        commands[args.command](args)
    else:
        parser.print_help()
```

### Progress Tracking for Long Operations

```python
from tqdm import tqdm

def load_command(args):
    print(colored("Loading knowledge...", "cyan"))

    files = get_files(args.knowledge_dir)

    for file in tqdm(files, desc="Processing files"):
        process_file(file)

    print(colored("Complete!", "green"))
```

---

## Troubleshooting

**Issue:** No command specified shows no output
- Add check for `if not args.command:` and call `parser.print_help()`

**Issue:** Shared arguments across multiple commands
- Define common arguments on main parser before subparsers
- Or create parent parser and pass to subparsers via `parents` parameter

**Issue:** Confirmation prompts don't work in scripts
- Add `--force` or `--yes` flag to skip confirmations
- Check for flag before prompting

**Issue:** Color not showing in terminal
- Install `termcolor`: `pip install termcolor`
- Some terminals don't support colors; add `--no-color` flag option

**Issue:** Help text not clear enough
- Use `description` parameter in `add_parser()` for detailed help
- Add examples in help text using `epilog` parameter

**Example with clear help:**
```python
search_parser = subparsers.add_parser(
    'search',
    help='Search the knowledge base',
    description='Search for content in the knowledge base using semantic search.',
    epilog='Example: python -m cli search --query "agent patterns" --results 10'
)
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---
