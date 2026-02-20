# CLI Pattern: Interactive with Initial Run

## Overview

This pattern creates an interactive CLI that performs an initial automated execution before entering the interactive loop. Useful when you want to process an input file or run a startup task, then allow the user to interact with the results.

**Use this pattern when:**
- Need to process an input file at startup
- Want automated initial execution followed by user interaction
- User should be able to continue/refine after initial run
- Session context maintained across all interactions

**Example in codebase:**
- `src/ui/cli/direct_shots.py` - Video director agent that processes shots then allows refinement

---

## Common Components Template

```python
# ============================================================
# IMPORTS
# ============================================================
from src.agents.{agent_module}.agent import {AgentClass}
from src.libs.utils.argument_parser import get_arguments


# ============================================================
# ARGUMENT PARSING & SESSION SETUP
# ============================================================
args = get_arguments(
    agent_id={AgentClass}.AGENT_ID,
    description='{AgentName} CLI',
    require_input=False  # Set to True if input is mandatory
)
print(f"Session: {args.session_id}\n")


# ============================================================
# AGENT INSTANTIATION
# ============================================================
{agent_instance} = {AgentClass}(args.session_id)


# ============================================================
# INITIAL AUTOMATED RUN
# ============================================================
if args.input_file:
    initial_prompt = f"{action_verb} from {args.input_file}"
    response = {agent_instance}.run(initial_prompt)
    print(f"\n{emoji} {AgentName}: {response.output}\n\n")
else:
    response = {agent_instance}.run("{default_initial_prompt}")
    print(f"\n{emoji} {AgentName}: {response.output}\n\n")


# ============================================================
# INTERACTIVE LOOP
# ============================================================
while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        print(f"\n{emoji} {AgentName}: {exit_message}\n\n")
        break

    response = {agent_instance}.run(user_input)
    print(f"\n{emoji} {AgentName}: {response.output}\n\n")
```

---

## Function-Specific Customization Points

### 1. Agent Import and Class
```python
# CUSTOMIZE: Replace with your agent's module and class name
from src.agents.{agent_module}.agent import {AgentClass}
```

**Example:**
```python
from src.agents.video_director_agent.agent import VideoDirector
```

### 2. Input File Requirement
```python
# CUSTOMIZE: Set to True if input file is mandatory
require_input=False  # Optional input file
# OR
require_input=True   # Mandatory input file
```

### 3. Initial Prompt Logic
```python
# CUSTOMIZE: Define what happens during initial run
if args.input_file:
    initial_prompt = f"{action_verb} from {args.input_file}"
    response = {agent_instance}.run(initial_prompt)
else:
    # CUSTOMIZE: Default behavior when no input file provided
    response = {agent_instance}.run("{default_initial_prompt}")
```

**Examples:**
```python
# File processing
if args.input_file:
    initial_prompt = f"Direct the shots from {args.input_file}"
else:
    initial_prompt = "Continue directing"

# Analysis
if args.input_file:
    initial_prompt = f"Analyze the content in {args.input_file}"
else:
    initial_prompt = "Start analysis"
```

### 4. Exit Conditions
```python
# CUSTOMIZE: Define how user can exit
if user_input.lower() in ["exit", "quit"]:
    break

# OR single exit command:
if user_input == "exit":
    break

# OR more options:
if user_input.lower() in ["exit", "quit", "done", "bye"]:
    break
```

### 5. Exit Message
```python
# CUSTOMIZE: Personalize exit message
print(f"\n{emoji} {AgentName}: {exit_message}\n\n")
```

**Examples:**
```python
print(f"\n🎬 Director: That's a wrap! Good work.\n\n")
print(f"\n🤖 Agent: Session saved. Goodbye!\n\n")
```

### 6. Input Prompt Label
```python
# CUSTOMIZE: Change input prompt label
user_input = input("You: ")

# OR use emoji:
user_input = input("🙍 User: ")

# OR use role-specific label:
user_input = input("Director: ")
```

---

## Complete Working Example

**File:** `src/ui/cli/direct_shots.py`

```python
from src.agents.video_director_agent.agent import VideoDirector
from src.libs.utils.argument_parser import get_arguments

args = get_arguments(
    agent_id=VideoDirector.AGENT_ID,
    description='Video Director CLI',
    require_input=False
)

print(f"Session: {args.session_id}\n")
director = VideoDirector(args.session_id)

if args.input_file:
    initial_prompt = f"Direct the shots from {args.input_file}"
    response = director.run(initial_prompt)
    print(f"\n🎬 Director: {response.output}\n\n")
else:
    response = director.run("Continue directing")
    print(f"\n🎬 Director: {response.output}\n\n")

while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        print(f"\n🎬 Director: That's a wrap! Good work.\n\n")
        break

    response = director.run(user_input)
    print(f"\n🎬 Director: {response.output}\n\n")
```

---

## Usage

### Running the CLI

```bash
# Start with input file
python -m src.ui.cli.direct_shots -i output/story/shots.md

# Start without input file (uses default behavior)
python -m src.ui.cli.direct_shots

# Resume session with input file
python -m src.ui.cli.direct_shots --resume -i output/story/shots.md

# Start with specific session ID
python -m src.ui.cli.direct_shots --session my_session -i input.md
```

### User Interaction Flow

**With input file:**
```
$ python -m src.ui.cli.direct_shots -i shots.md
Session: 20250113_143022

🎬 Director: I've analyzed the shots from shots.md. Shot 1 needs better lighting...

You: Can you suggest camera angles for shot 3?
🎬 Director: For shot 3, I recommend a low angle to emphasize...

You: exit
🎬 Director: That's a wrap! Good work.
```

**Without input file:**
```
$ python -m src.ui.cli.direct_shots
Session: 20250113_143022

🎬 Director: Ready to direct! What would you like to work on?

You: Let's review the opening sequence
🎬 Director: Looking at the opening sequence...

You: quit
🎬 Director: That's a wrap! Good work.
```

---

## Key Features

### Conditional Initial Execution
- Checks for `args.input_file` presence
- Runs different prompts based on input availability
- Both paths lead to interactive loop

### Flexible Exit
- Multiple exit commands supported (exit, quit)
- Case-insensitive matching with `.lower()`
- Personalized exit message

### Session Continuity
- Initial run and interactive loop share same session
- Agent maintains context from initial run through all interactions
- Can resume previous sessions

---

## Decision Guide

**Choose this pattern if:**
- ✅ Need to process input file before user interaction
- ✅ Want automated startup task followed by refinement
- ✅ User should interact with initial results
- ✅ Optional or conditional initial execution

**Choose a different pattern if:**
- ❌ No initial automated execution needed → Use `interface_cli_interactive.md`
- ❌ Single execution only (no loop) → Use `interface_cli_async.md`
- ❌ Batch file processing → Use `interface_cli_batch.md`
- ❌ Multiple subcommands → Use `interface_cli_subcommand.md`

---

## Related Patterns

- **interface_cli_common.md** - Shared components reference
- **interface_cli_interactive.md** - Simple interactive loop (no initial run)
- **interface_cli_async.md** - Non-interactive async pattern

---

## Common Modifications

### Add File Validation

```python
if args.input_file:
    import os
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    initial_prompt = f"Process {args.input_file}"
    response = agent.run(initial_prompt)
```

### Add Progress Indication

```python
if args.input_file:
    print(f"Processing {args.input_file}...")
    print("-" * 50)
    response = agent.run(f"Process {args.input_file}")
    print("-" * 50)
    print(f"\n{emoji} Agent: {response.output}\n\n")
```

### Make Input File Mandatory

```python
args = get_arguments(
    agent_id=AgentClass.AGENT_ID,
    description='Agent CLI',
    require_input=True  # Input file is required
)

# No need for conditional - input file always present
initial_prompt = f"Process {args.input_file}"
response = agent.run(initial_prompt)
```

### Add Multiple Initial Actions

```python
if args.input_file:
    print("Step 1: Loading file...")
    load_response = agent.run(f"Load {args.input_file}")

    print("Step 2: Analyzing content...")
    analyze_response = agent.run("Analyze the content")

    print("Step 3: Generating recommendations...")
    recommend_response = agent.run("Generate recommendations")

    print(f"\n{emoji} Agent: Ready for your input!\n\n")
```

### Add Confirmation Before Loop

```python
if args.input_file:
    response = agent.run(f"Process {args.input_file}")
    print(f"\n{emoji} Agent: {response.output}\n\n")

    continue_prompt = input("Continue to interactive mode? (y/n): ")
    if continue_prompt.lower() != 'y':
        print("Exiting.")
        sys.exit(0)

while True:
    user_input = input("You: ")
    # ... rest of loop
```

### Add Output File Writing

```python
if args.input_file:
    response = agent.run(f"Process {args.input_file}")
    print(f"\n{emoji} Agent: {response.output}\n\n")

    # Save initial results
    if args.output_file:
        from src.libs.filesystem.file_operations import write_file
        write_file(args.output_file, response.output)
        print(f"Results saved to {args.output_file}")
```

---

## Advanced Variations

### Multiple Input Files

```python
args = get_arguments(
    agent_id=AgentClass.AGENT_ID,
    description='Agent CLI',
    require_input=False
)

# Custom argument for additional files
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--files', nargs='+', help='Multiple input files')
custom_args = parser.parse_args()

if custom_args.files:
    for file in custom_args.files:
        response = agent.run(f"Process {file}")
        print(f"\n{emoji} Agent: {response.output}\n\n")
```

### Automatic vs Manual Mode

```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auto', action='store_true', help='Run in automatic mode')
custom_args = parser.parse_args()

if custom_args.auto and args.input_file:
    # Automatic processing without interaction
    response = agent.run(f"Process {args.input_file}")
    print(f"\n{emoji} Agent: {response.output}\n\n")
    sys.exit(0)
else:
    # Interactive mode with optional initial run
    if args.input_file:
        response = agent.run(f"Process {args.input_file}")
        print(f"\n{emoji} Agent: {response.output}\n\n")

    while True:
        # ... interactive loop
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Troubleshooting

**Issue:** Initial run executes but context not preserved in loop
- Verify agent shares same session_id for initial run and loop
- Ensure agent is stateful (takes `session_id` in `__init__`)

**Issue:** Input file not found
- Add file existence validation with `os.path.exists()`
- Provide clear error message with expected path

**Issue:** User confused about when to interact
- Add clear separator between initial run and interactive mode
- Print message indicating interactive mode is ready

**Issue:** Want to skip initial run on resume
- Check if session exists and skip initial run if resuming
- Store state flag in session to detect first vs resumed run
