# CLI Interface Blueprint - Index

This is the master index for CLI patterns in Pydantic AI projects. Use this guide to choose the right CLI pattern for your needs.

---

## Quick Pattern Selector

**I need a CLI that...**

- **Has a conversation loop with the user** → [`interface_cli_interactive.md`](#interactive-loop)
- **Processes a file then enters conversation mode** → [`interface_cli_interactive_initial_run.md`](#interactive-with-initial-run)
- **Runs once async and exits** → [`interface_cli_async.md`](#async-single-execution)
- **Processes files in batches with progress bar** → [`interface_cli_batch.md`](#batch-processing)
- **Has multiple subcommands (utility tool)** → [`interface_cli_subcommand.md`](#subcommand-utility)

---

## Pattern Overview

### 1. Common Components
**File:** `interface_cli_common.md`

Shared components used across all CLI patterns:
- Import structure
- Argument parser utility
- Session management
- Agent instantiation (stateful vs stateless)
- Error handling strategies
- Output formatting conventions
- File operations
- Module execution patterns

**Read this first** to understand foundational components.

---

### 2. Interactive Loop
**File:** `interface_cli_interactive.md`

Simple conversational CLI with continuous user interaction loop.

**Pattern:**
```
Start → Display Session → Loop(User Input → Agent Response) → Exit
```

**Key Features:**
- Stateful agent with session context
- Continuous conversation loop
- User types prompts, agent responds
- Exit on "exit" command

**Use when:**
- Need back-and-forth conversation
- Agent should remember context
- User drives all interaction
- No automated initial execution

**Examples in codebase:**
- `src/ui/cli/research_story.py`
- `src/ui/cli/test_llm.py`

---

### 3. Interactive with Initial Run
**File:** `interface_cli_interactive_initial_run.md`

Interactive CLI that performs initial automated execution before entering conversation loop.

**Pattern:**
```
Start → Display Session → Initial Automated Run → Loop(User Input → Agent Response) → Exit
```

**Key Features:**
- Optional input file processing at startup
- Conditional initial execution
- Conversation loop after initial run
- Flexible exit conditions

**Use when:**
- Need to process input file first
- Want automated startup + refinement
- User should interact with results
- Optional or conditional initial run

**Examples in codebase:**
- `src/ui/cli/direct_shots.py`

---

### 4. Async Single Execution
**File:** `interface_cli_async.md`

Non-interactive CLI that performs single async operation and exits.

**Pattern:**
```
Start → Validate Prerequisites → Async Execution → Success/Error → Exit
```

**Key Features:**
- Custom argument parsing
- Prerequisite file validation
- Async/await execution
- Comprehensive error handling
- Exit codes (0=success, 1=error)
- Resume capability

**Use when:**
- Single automated execution
- Long-running async operation
- Need prerequisite validation
- No user interaction needed
- Operation should complete and exit

**Examples in codebase:**
- `src/ui/cli/create_story.py`

---

### 5. Batch Processing
**File:** `interface_cli_batch.md`

CLI that processes input files in batches with progress tracking.

**Pattern:**
```
Start → Read Input → Parse into Chunks → Loop(Process Chunk → Append to Output) → Complete
```

**Key Features:**
- Progress bar with `tqdm`
- Stateless agent (no session)
- Incremental output appending
- Verbose mode for debugging
- File I/O operations

**Use when:**
- Processing files chunk by chunk
- Need progress tracking
- Agent is stateless
- Transforming input to output format
- Want incremental results

**Examples in codebase:**
- `src/ui/cli/generate_shots.py`

---

### 6. Subcommand Utility
**File:** `interface_cli_subcommand.md`

Utility CLI with multiple subcommands for different operations.

**Pattern:**
```
Start → Parse Subcommand → Execute Handler → Success/Error → Exit
```

**Key Features:**
- Multiple subcommands in one CLI
- Each subcommand has own arguments
- Command dispatch dictionary
- Colored terminal output
- User confirmation for destructive operations
- No agent (direct library calls)

**Use when:**
- Multiple related operations
- Each operation has different parameters
- Building utility/management tool
- No agent needed
- Want organized command structure

**Examples in codebase:**
- `src/ui/cli/manage_knowledge_base.py`

---

## Decision Tree

```
Do you need user interaction?
├─ Yes
│  ├─ Need initial automated execution first?
│  │  ├─ Yes → Interactive with Initial Run (Pattern 3)
│  │  └─ No → Interactive Loop (Pattern 2)
│  └─ Multiple different commands?
│     └─ Yes → Subcommand Utility (Pattern 6)
│
└─ No
   ├─ Processing files in batches?
   │  └─ Yes → Batch Processing (Pattern 5)
   └─ Single automated operation?
      └─ Yes → Async Single Execution (Pattern 4)
```

---

## Pattern Comparison

| Feature | Interactive | Interactive + Initial | Async Single | Batch | Subcommand |
|---------|-------------|----------------------|--------------|-------|------------|
| **User Interaction** | Loop | Loop | No | No | One-off |
| **Initial Run** | No | Yes | Yes | No | No |
| **Session Context** | Yes | Yes | Yes | No | No |
| **Progress Bar** | No | No | No | Yes | No |
| **Multiple Commands** | No | No | No | No | Yes |
| **Async/Await** | No | No | Yes | No | No |
| **Exit on Complete** | User exit | User exit | Yes | Yes | Yes |
| **Agent Type** | Stateful | Stateful | Stateful | Stateless | None |
| **Use Shared arg_parser** | Yes | Yes | No | Yes | No |

---

## Module Execution Pattern

All CLIs use Python module execution:

```bash
python -m src.ui.cli.{cli_name}
```

**Why module execution?**
- Proper Python package imports
- Consistent path resolution
- Works from project root

**File placement:**
```
src/
└── ui/
    └── cli/
        ├── __init__.py
        ├── research_story.py
        ├── create_story.py
        ├── generate_shots.py
        └── manage_knowledge_base.py
```

---

## Common CLI Patterns Across All Types

### Import Organization
1. Standard library imports
2. Third-party imports
3. Agent imports
4. Utility imports

### Session Management
- New session: Auto-generated timestamp
- Resume session: `--resume` flag
- Specific session: `--session <id>` flag

### Output Formatting
- Emoji prefixes for user/agent distinction
- Visual separators (`-` * 50, `=` * 50)
- Colored output (cyan, yellow, green, red)

### Error Handling
- Try/except blocks
- Clear error messages
- Traceback for debugging
- Exit codes for automation

---

## Getting Started

**To create a new CLI:**

1. **Choose a pattern** from the quick selector above
2. **Read `interface_cli_common.md`** for shared components
3. **Read the specific pattern file** for your use case
4. **Copy the template** and customize marked sections
5. **Test with** `python -m src.ui.cli.your_cli`

---

## File Location

All blueprint files are in `PDs/blueprints/interfaces/`:

```
PDs/blueprints/interfaces/
├── interface_cli.md (this file)
├── interface_cli_common.md
├── interface_cli_interactive.md
├── interface_cli_interactive_initial_run.md
├── interface_cli_async.md
├── interface_cli_batch.md
└── interface_cli_subcommand.md
```

---

## Pattern Evolution

As new CLI patterns emerge in the project:
1. Document the pattern in a new file
2. Add to this index
3. Update decision tree
4. Add to pattern comparison table

---

## Related Documentation

- `interface_cli_common.md` - Shared CLI components (this directory)
- `../libs/` - Library blueprints
- `../pydantic/pydantic_ai_agent_guide.md` - Agent development patterns
- `../pydantic/pydantic_ai_project_structure.md` - Project organization

---

## Examples by Use Case

### Research & Exploration
- Interactive Loop → Research WoW lore, test LLM responses

### Content Generation
- Async Single → Generate complete story from research
- Batch Processing → Convert story to individual shots

### Content Refinement
- Interactive + Initial → Review/refine generated shots

### Utility & Management
- Subcommand → Manage knowledge bases, config, databases

---

## Quick Reference

**Simple conversation:**
```python
while True:
    prompt = input("User: ")
    if prompt == "exit": break
    print(agent.run(prompt).output)
```

**Batch processing:**
```python
for chunk in tqdm(chunks):
    result = agent.run(chunk)
    append_file(output, result.output)
```

**Async single execution:**
```python
async def main():
    await agent.run(subject)

asyncio.run(main())
```

**Subcommands:**
```python
commands = {'load': load_handler, 'search': search_handler}
commands[args.command](args)
```

---

## Support

For questions about:
- **CLI patterns** → Read specific pattern file
- **Shared utilities** → Read `interface_cli_common.md`
- **Agent development** → Read `PDs/pydantic_ai_coding_guide.md`
- **Project structure** → Read `PDs/pydantic_ai_project_structure.md`
