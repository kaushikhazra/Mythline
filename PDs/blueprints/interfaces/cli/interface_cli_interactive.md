# CLI Pattern: Interactive Loop

## Overview

This pattern creates a simple interactive CLI with a continuous conversation loop. The user enters prompts, the agent responds, and the conversation continues until the user types "exit".

**Use this pattern when:**
- Building conversational interfaces with stateful agents
- User needs back-and-forth dialogue with the agent
- Session context should be maintained across interactions
- No initial automated execution needed

**Examples in codebase:**
- `src/ui/cli/research_story.py` - Story research agent
- `src/ui/cli/test_llm.py` - LLM testing agent

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
    description='{AgentName} CLI'
)
print(f"Session: {args.session_id}\n")


# ============================================================
# AGENT INSTANTIATION
# ============================================================
{agent_instance} = {AgentClass}(args.session_id)


# ============================================================
# INTERACTIVE LOOP
# ============================================================
while True:
    prompt = input("{emoji} User: ")

    if prompt == "exit":
        print(f"\n{emoji}  {AgentName}: Good Bye!! \n\n")
        break

    response = {agent_instance}.run(prompt)
    print(f"\n{emoji}  {AgentName}: {response.output} \n\n")
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
from src.agents.story_research_agent.agent import StoryResearcher
```

### 2. Agent Identifier
```python
# CUSTOMIZE: Use your agent's AGENT_ID constant
agent_id={AgentClass}.AGENT_ID
```

**Example:**
```python
agent_id=StoryResearcher.AGENT_ID
```

### 3. CLI Description
```python
# CUSTOMIZE: Provide meaningful description for --help
description='{AgentName} CLI'
```

**Example:**
```python
description='Story Research CLI'
```

### 4. Agent Instance Name
```python
# CUSTOMIZE: Use descriptive variable name
{agent_instance} = {AgentClass}(args.session_id)
```

**Example:**
```python
story_researcher = StoryResearcher(args.session_id)
```

### 5. User/Agent Emojis
```python
# CUSTOMIZE: Choose emojis that represent user and agent
prompt = input("{emoji} User: ")
print(f"\n{emoji}  {AgentName}: {response.output} \n\n")
```

**Examples:**
- 🙍 User, ✏️ Story Researcher
- 🙍 User, 🤖 LLM Tester
- 🙍 User, 🎬 Director

### 6. Exit Message
```python
# CUSTOMIZE: Personalize exit message
print(f"\n{emoji}  {AgentName}: Good Bye!! \n\n")
```

**Examples:**
```python
print(f"\n✏️  Story Researcher: Good Bye!! \n\n")
print(f"\n🤖 LLM Tester: Goodbye! \n\n")
```

### 7. Exit Condition (Optional)
```python
# OPTIONAL: Make exit condition flexible
if prompt == "exit":
    break

# OR allow multiple exit commands:
if prompt.lower() in ["exit", "quit", "bye"]:
    break
```

---

## Complete Working Example

**File:** `src/ui/cli/research_story.py`

```python
from src.agents.story_research_agent.agent import StoryResearcher
from src.libs.utils.argument_parser import get_arguments

args = get_arguments(
    agent_id=StoryResearcher.AGENT_ID,
    description='Story Research CLI'
)
print(f"Session: {args.session_id}\n")
story_researcher = StoryResearcher(args.session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        print(f"\n✏️  Story Researcher: Good Bye!! \n\n")
        break

    response = story_researcher.run(prompt)
    print(f"\n✏️  Story Researcher: {response.output} \n\n")
```

---

## Usage

### Running the CLI

```bash
# Start new session (auto-generated session ID)
python -m src.ui.cli.research_story

# Start new session with specific ID
python -m src.ui.cli.research_story --session my_session_001

# Resume latest session
python -m src.ui.cli.research_story --resume
```

### User Interaction Flow

```
$ python -m src.ui.cli.research_story
Session: 20250113_143022

🙍 User: Tell me about Shadowglen
✏️  Story Researcher: Shadowglen is the night elf starting zone...

🙍 User: What characters are found there?
✏️  Story Researcher: Key NPCs include Conservator Ilthalaine...

🙍 User: exit
✏️  Story Researcher: Good Bye!!
```

---

## Key Features

### Session Persistence
- Session ID is displayed at startup
- All conversation history is saved to `.mythline/{agent_id}/context_memory/{session_id}.json`
- Can resume previous sessions with `--resume` flag

### Context Memory
- Agent maintains conversation context throughout the session
- Each prompt/response is added to message history
- Context persists across program restarts (when resumed)

### Simple Exit
- User types "exit" to end conversation
- Clean exit message from agent
- Session is automatically saved

---

## Decision Guide

**Choose this pattern if:**
- ✅ You need conversational, back-and-forth interaction
- ✅ Agent should remember previous messages in the session
- ✅ User drives all interaction (no automated initial execution)
- ✅ Simple loop is sufficient (no complex state management)

**Choose a different pattern if:**
- ❌ Need initial automated execution → Use `interface_cli_interactive_initial_run.md`
- ❌ Single execution without loop → Use `interface_cli_async.md`
- ❌ Processing files in batch → Use `interface_cli_batch.md`
- ❌ Multiple subcommands → Use `interface_cli_subcommand.md`

---

## Related Patterns

- **interface_cli_common.md** - Shared components reference
- **interface_cli_interactive_initial_run.md** - Interactive with initial execution
- **interface_cli_async.md** - Non-interactive async pattern

---

## Common Modifications

### Add Verbose Mode

```python
args = get_arguments(
    agent_id=AgentClass.AGENT_ID,
    description='Agent CLI'
)

if args.verbose:
    print(f"Agent ID: {AgentClass.AGENT_ID}")
    print(f"Session: {args.session_id}")
    print("-" * 50)
```

### Add Multi-line Input

```python
print("Enter your prompt (type 'END' on a new line to finish):")
lines = []
while True:
    line = input()
    if line == "END":
        break
    lines.append(line)
prompt = "\n".join(lines)
```

### Add Input Validation

```python
prompt = input("🙍 User: ")

if not prompt.strip():
    print("Please enter a valid prompt.")
    continue

if prompt == "exit":
    break
```

### Add Command History

```python
import readline

while True:
    try:
        prompt = input("🙍 User: ")
    except EOFError:
        break
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Troubleshooting

**Issue:** Session not saving
- Ensure agent properly loads/saves context memory
- Check `.mythline/{agent_id}/context_memory/` directory exists

**Issue:** Agent doesn't remember context
- Verify agent is stateful (takes `session_id` in `__init__`)
- Confirm agent uses `message_history` in `run()` method

**Issue:** Exit command not working
- Check exact exit string (case-sensitive by default)
- Consider using `.lower()` for case-insensitive matching
