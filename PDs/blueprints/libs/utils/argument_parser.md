# Library: argument_parser

Standardized CLI argument parsing with session management.

## Overview

**Location:** `src/libs/utils/argument_parser.py`

**Use when:** Building CLI interfaces with standard argument handling.

## Import

```python
from src.libs.utils.argument_parser import get_arguments
```

## Function

### get_arguments(agent_id, description, require_input=False, require_output=False) -> CLIArgs

**Returns:**
```python
@dataclass
class CLIArgs:
    session_id: str
    input_file: Optional[str]
    output_file: Optional[str]
    verbose: bool
```

## Command-Line Arguments

```bash
--session, -s <id>    # Use specific session
--resume, -r          # Resume latest session
--input, -i <file>    # Input file
--output, -o <file>   # Output file
--verbose, -v         # Verbose output
```

## Usage Examples

```python
# Interactive CLI
args = get_arguments(
    agent_id='story_research',
    description='Story Research CLI'
)

# Batch processing CLI
args = get_arguments(
    agent_id='shot_creator',
    description='Shot Generator',
    require_input=True,
    require_output=True
)

# Use args
agent = Agent(session_id=args.session_id)
if args.verbose:
    print("Debug info")
```

## Session ID Logic

- No args: Creates new session `YYYYMMDD_HHMMSS`
- `--resume`: Loads latest session
- `--session <id>`: Uses specified session

## Examples in Codebase
All CLI scripts use this for argument parsing.
