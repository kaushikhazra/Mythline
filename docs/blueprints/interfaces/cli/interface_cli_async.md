# CLI Pattern: Async Single Execution

## Overview

This pattern creates a non-interactive CLI that performs a single asynchronous operation and exits. Ideal for long-running automated tasks that require prerequisite validation and graceful error handling.

**Use this pattern when:**
- Single automated execution (no user interaction loop)
- Long-running operations that benefit from async/await
- Need prerequisite file/data validation
- Want comprehensive error handling with resume capability
- Operation should complete and exit

**Example in codebase:**
- `src/ui/cli/create_story.py` - Story creation from research notes

---

## Common Components Template

```python
# ============================================================
# IMPORTS
# ============================================================
import os
import sys
import argparse
import asyncio
import traceback
from src.agents.{agent_module}.agent import {AgentClass}


# ============================================================
# CUSTOM ARGUMENT PARSING
# ============================================================
parser = argparse.ArgumentParser(
    description='{AgentName} CLI - Non-Interactive {Operation}'
)
parser.add_argument(
    '--{arg1}', '-{short1}',
    type=str,
    required=True,
    help='{arg1_description}'
)
parser.add_argument(
    '--{arg2}', '-{short2}',
    type=str,
    required=True,
    help='{arg2_description}'
)
args = parser.parse_args()


# ============================================================
# PREREQUISITE VALIDATION
# ============================================================
prerequisite_path = f"path/to/{args.arg1}/required_file.ext"
if not os.path.exists(prerequisite_path):
    print(f"Error: Required file not found at {prerequisite_path}")
    print(f"Please run {prerequisite_step} first.")
    sys.exit(1)


# ============================================================
# ASYNC MAIN FUNCTION
# ============================================================
async def main():
    session_id = {determine_session_id}
    agent = {AgentClass}(session_id=session_id, {additional_params})

    print(f"Starting {operation} for: {args.arg1}")
    print(f"Session ID: {session_id}")
    print(f"Required file: {prerequisite_path}")
    print("-" * 50)

    try:
        await agent.run({operation_params})
        print("\n" + "=" * 50)
        print("{Operation} complete!")
        print("=" * 50)
        sys.exit(0)
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"Error during {operation}:")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)
        print(f"Session saved. You can resume by running the same command again.")
        print("=" * 50)
        sys.exit(1)


# ============================================================
# EXECUTION
# ============================================================
asyncio.run(main())
```

---

## Function-Specific Customization Points

### 1. Agent Import
```python
# CUSTOMIZE: Import your agent class
from src.agents.{agent_module}.agent import {AgentClass}
```

**Example:**
```python
from src.agents.story_creator_agent.agent import StoryCreatorAgent
```

### 2. Custom Arguments
```python
# CUSTOMIZE: Define required and optional arguments
parser.add_argument('--{name}', '-{short}', type=str, required=True, help='...')
parser.add_argument('--{name}', '-{short}', type=str, required=False, help='...')
```

**Examples:**
```python
parser.add_argument('--subject', '-s', type=str, required=True, help='Story subject')
parser.add_argument('--player', '-p', type=str, required=True, help='Player character name')
parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
```

### 3. Prerequisite Validation
```python
# CUSTOMIZE: Validate required files or data before execution
prerequisite_path = f"path/to/{args.subject}/file.ext"
if not os.path.exists(prerequisite_path):
    print(f"Error: Required file not found at {prerequisite_path}")
    print(f"Please run {prerequisite_step} first.")
    sys.exit(1)
```

**Examples:**
```python
# Check research file
research_path = f"output/{args.subject}/research.md"
if not os.path.exists(research_path):
    print(f"Error: Research file not found at {research_path}")
    print(f"Please run story_research_agent first to create research notes.")
    sys.exit(1)

# Check multiple prerequisites
if not os.path.exists(file1) or not os.path.exists(file2):
    print("Error: Missing required files")
    sys.exit(1)
```

### 4. Session ID Strategy
```python
# CUSTOMIZE: Determine how session ID is generated
session_id = {determine_session_id}
```

**Examples:**
```python
# Use argument as session ID
session_id = args.subject

# Generate from timestamp
from datetime import datetime
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Use provided argument or generate
session_id = args.session if args.session else args.subject

# Fixed session for singleton operations
session_id = "default"
```

### 5. Agent Instantiation
```python
# CUSTOMIZE: Pass required parameters to agent
agent = {AgentClass}(session_id=session_id, {additional_params})
```

**Examples:**
```python
agent = StoryCreatorAgent(session_id=session_id, player_name=args.player)
agent = AnalysisAgent(session_id=session_id)
agent = ProcessorAgent(session_id=session_id, config=args.config)
```

### 6. Status Messages
```python
# CUSTOMIZE: Provide meaningful status information
print(f"Starting {operation} for: {args.arg1}")
print(f"Session ID: {session_id}")
print(f"Input: {input_description}")
print("-" * 50)
```

### 7. Agent Execution
```python
# CUSTOMIZE: Call agent method with appropriate parameters
await agent.run({operation_params})
```

**Examples:**
```python
await agent.run(subject=args.subject)
await agent.run(input_file=args.input, output_file=args.output)
await agent.run()  # No parameters needed
result = await agent.run(args.subject)
```

### 8. Success Message
```python
# CUSTOMIZE: Celebrate success
print("\n" + "=" * 50)
print("{Operation} complete!")
print("=" * 50)
```

---

## Complete Working Example

**File:** `src/ui/cli/create_story.py`

```python
import os
import sys
import argparse
import asyncio
import traceback
from src.agents.story_creator_agent.agent import StoryCreatorAgent

parser = argparse.ArgumentParser(
    description='Story Creator CLI - Non-Interactive Story Generation'
)
parser.add_argument(
    '--subject', '-s',
    type=str,
    required=True,
    help='Story subject (e.g., shadowglen, elwynn_forest)'
)
parser.add_argument(
    '--player', '-p',
    type=str,
    required=True,
    help='Player character name'
)
args = parser.parse_args()

research_path = f"output/{args.subject}/research.md"
if not os.path.exists(research_path):
    print(f"Error: Research file not found at {research_path}")
    print(f"Please run story_research_agent first to create research notes.")
    sys.exit(1)

async def main():
    session_id = args.subject
    story_creator = StoryCreatorAgent(session_id=session_id, player_name=args.player)

    print(f"Starting story generation for: {args.subject}")
    print(f"Player character: {args.player}")
    print(f"Session ID: {session_id}")
    print(f"Research file: {research_path}")
    print("-" * 50)

    try:
        await story_creator.run(subject=args.subject)
        print("\n" + "=" * 50)
        print("Story generation complete!")
        print("=" * 50)
        sys.exit(0)
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"Error during story generation:")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)
        print(f"Session saved. You can resume by running the same command again.")
        print("=" * 50)
        sys.exit(1)

asyncio.run(main())
```

---

## Usage

### Running the CLI

```bash
# Basic execution
python -m src.ui.cli.create_story --subject shadowglen --player Sarephine

# Using short flags
python -m src.ui.cli.create_story -s shadowglen -p Sarephine

# With additional optional arguments
python -m src.ui.cli.create_story -s elwynn_forest -p Thorin --verbose
```

### Execution Flow

```
$ python -m src.ui.cli.create_story -s shadowglen -p Sarephine
Starting story generation for: shadowglen
Player character: Sarephine
Session ID: shadowglen
Research file: output/shadowglen/research.md
--------------------------------------------------
[Agent processing... may take several minutes]

==================================================
Story generation complete!
==================================================
```

### Error Flow

```
$ python -m src.ui.cli.create_story -s shadowglen -p Sarephine
Error: Research file not found at output/shadowglen/research.md
Please run story_research_agent first to create research notes.
```

---

## Key Features

### Prerequisite Validation
- Checks required files exist before execution
- Provides clear error messages with remediation steps
- Exits early if prerequisites not met

### Async Execution
- Uses `async/await` for long-running operations
- Allows agent to perform concurrent tasks
- Better resource utilization

### Comprehensive Error Handling
- Catches all exceptions with try/except
- Prints full traceback for debugging
- Saves session state before exit
- Provides resume instructions

### Exit Codes
- `sys.exit(0)` - Success
- `sys.exit(1)` - Error
- Allows shell scripts to detect success/failure

### Visual Feedback
- Progress separators (`-` * 50)
- Completion banners (`=` * 50)
- Clear status messages throughout

---

## Decision Guide

**Choose this pattern if:**
- ✅ Single automated execution (no loop)
- ✅ Long-running async operation
- ✅ Need prerequisite validation
- ✅ Want comprehensive error handling
- ✅ Operation should complete and exit

**Choose a different pattern if:**
- ❌ Need user interaction → Use `interface_cli_interactive.md`
- ❌ Want interactive loop after initial run → Use `interface_cli_interactive_initial_run.md`
- ❌ Processing files in batch → Use `interface_cli_batch.md`
- ❌ Multiple subcommands → Use `interface_cli_subcommand.md`

---

## Related Patterns

- **interface_cli_common.md** - Shared components reference
- **interface_cli_batch.md** - Batch processing pattern
- **interface_cli_interactive.md** - Interactive loop pattern

---

## Common Modifications

### Add Progress Updates

```python
async def main():
    agent = AgentClass(session_id=session_id)

    print("Step 1: Initializing...")
    await agent.initialize()

    print("Step 2: Processing...")
    await agent.process()

    print("Step 3: Finalizing...")
    await agent.finalize()

    print("Complete!")
```

### Add Output File Specification

```python
parser.add_argument('--output', '-o', type=str, help='Output file path')
args = parser.parse_args()

async def main():
    result = await agent.run(subject=args.subject)

    if args.output:
        from src.libs.filesystem.file_operations import write_file
        write_file(args.output, result.output)
        print(f"Output saved to {args.output}")
```

### Add Verbose Mode

```python
parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
args = parser.parse_args()

async def main():
    if args.verbose:
        print(f"Debug: Session ID = {session_id}")
        print(f"Debug: Agent class = {AgentClass.__name__}")

    await agent.run(subject=args.subject)
```

### Add Retry Logic

```python
async def main():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await agent.run(subject=args.subject)
            print("Success!")
            sys.exit(0)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying...")
            else:
                print("All retries exhausted")
                traceback.print_exc()
                sys.exit(1)
```

### Add Configuration File Support

```python
parser.add_argument('--config', '-c', type=str, help='Configuration file')
args = parser.parse_args()

if args.config:
    import json
    with open(args.config, 'r') as f:
        config = json.load(f)
else:
    config = {}

async def main():
    agent = AgentClass(session_id=session_id, config=config)
    await agent.run(subject=args.subject)
```

### Add Time Tracking

```python
import time

async def main():
    start_time = time.time()

    await agent.run(subject=args.subject)

    elapsed = time.time() - start_time
    print(f"Completed in {elapsed:.2f} seconds")
```

---

## Advanced Variations

### Multiple Async Operations

```python
async def main():
    agent1 = Agent1(session_id=session_id)
    agent2 = Agent2(session_id=session_id)

    print("Running operations in parallel...")
    results = await asyncio.gather(
        agent1.run(args.input1),
        agent2.run(args.input2)
    )

    print("Both operations complete!")
```

### Streaming Progress

```python
async def main():
    agent = AgentClass(session_id=session_id)

    async for progress in agent.run_with_progress(subject=args.subject):
        print(f"Progress: {progress}%")

    print("Complete!")
```

### Conditional Execution

```python
async def main():
    agent = AgentClass(session_id=session_id)

    if args.fast:
        await agent.run_fast(subject=args.subject)
    elif args.thorough:
        await agent.run_thorough(subject=args.subject)
    else:
        await agent.run(subject=args.subject)
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Troubleshooting

**Issue:** Script hangs indefinitely
- Check if agent method is properly async
- Ensure all async calls use `await`
- Verify no blocking I/O in async functions

**Issue:** Error not showing full traceback
- Ensure `traceback.print_exc()` is called
- Check that exception is not being silenced elsewhere

**Issue:** Prerequisite check fails incorrectly
- Verify path construction matches actual file structure
- Use `os.path.abspath()` for debugging paths
- Check for case sensitivity in file names

**Issue:** Cannot resume after error
- Ensure agent saves context/state properly
- Verify session_id is consistent between runs
- Check that error doesn't corrupt session files

**Issue:** Exit code not propagating to shell
- Ensure using `sys.exit(0)` and `sys.exit(1)`
- Check no code after asyncio.run() that could override
- Verify exception handling doesn't mask exit calls
