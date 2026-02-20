# Stateful Graph Blueprint

This blueprint covers Pydantic Graphs with state management, enabling nodes to share data across the workflow without passing everything through node parameters.

## Overview

Stateful graphs:
- Maintain shared state across all nodes
- State persists throughout workflow execution
- Nodes can read and write to shared state
- Reduces parameter passing complexity
- Ideal for complex workflows with shared data
- Type-safe state access

## Graph Structure

```
src/graphs/{graph_name}/
├── __init__.py
├── graph.py
├── nodes.py
└── models/
    └── state_models.py
```

## State Model Definition

**File:** `models/state_models.py`

```python
from dataclasses import dataclass

@dataclass
class {GraphName}State:
    """Shared state for the graph workflow."""
    # Required fields
    session_id: str
    user_input: str

    # Workflow data
    processed_data: str = ""
    results: list[str] = None
    error_message: str = ""

    # Tracking
    step_count: int = 0
    is_complete: bool = False

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.results is None:
            self.results = []
```

## Implementation Pattern

### Stateful Nodes

**File:** `nodes.py`

```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.{graph_name}.models.state_models import {GraphName}State


@dataclass
class Step1(BaseNode[{GraphName}State]):
    """First step with access to shared state."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> Step2 | End[str]:
        # Read from state
        user_input = ctx.state.user_input
        session_id = ctx.state.session_id

        print(f"[Step 1] Processing: {user_input}")

        # Process data
        processed = user_input.upper()

        # Write to state
        ctx.state.processed_data = processed
        ctx.state.step_count += 1

        if not processed:
            ctx.state.error_message = "No data to process"
            return End("Error: No data")

        return Step2()


@dataclass
class Step2(BaseNode[{GraphName}State]):
    """Second step reading from state."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> Step3:
        # Read processed data from state
        data = ctx.state.processed_data

        print(f"[Step 2] Transforming: {data}")

        # Transform and update state
        transformed = f"[{data}]"
        ctx.state.results.append(transformed)
        ctx.state.step_count += 1

        return Step3()


@dataclass
class Step3(BaseNode[{GraphName}State]):
    """Final step with state access."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> End[dict]:
        # Read from state
        results = ctx.state.results
        step_count = ctx.state.step_count

        print(f"[Step 3] Completed {step_count} steps")

        # Mark complete
        ctx.state.is_complete = True

        # Return state data
        return End({
            "results": results,
            "steps": step_count,
            "session": ctx.state.session_id
        })
```

### Graph with State

**File:** `graph.py`

```python
from pydantic_graph import Graph

from src.graphs.{graph_name}.models.state_models import {GraphName}State
from src.graphs.{graph_name}.nodes import Step1, Step2, Step3


class {GraphName}:
    def __init__(self, session_id: str):
        self.session_id = session_id

        self.graph = Graph(nodes=[Step1, Step2, Step3])

    async def run(self, user_input: str) -> dict:
        """Runs graph with state."""
        # Initialize state
        state = {GraphName}State(
            session_id=self.session_id,
            user_input=user_input
        )

        # Run graph with state
        result = await self.graph.run(Step1(), state=state)

        return result.output
```

## Key Concepts

### State Declaration in Nodes

```python
# Stateful node - include state type as generic
@dataclass
class MyNode(BaseNode[MyGraphState]):
    async def run(self, ctx: GraphRunContext[MyGraphState]) -> NextNode:
        # Access state via ctx.state
        value = ctx.state.some_field
        ctx.state.another_field = "new value"
        return NextNode()
```

### State Access Patterns

**Reading from State:**
```python
async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
    # Read single field
    user_id = ctx.state.user_id

    # Read multiple fields
    name = ctx.state.name
    email = ctx.state.email

    # Use state data
    result = self.process(user_id, name, email)
    return NextNode()
```

**Writing to State:**
```python
async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
    # Update single field
    ctx.state.processed_count += 1

    # Set new value
    ctx.state.result = "Success"

    # Append to list
    ctx.state.results.append(new_item)

    # Update complex field
    ctx.state.metadata = {"timestamp": time.time(), "status": "complete"}

    return NextNode()
```

**Conditional Logic Based on State:**
```python
async def run(self, ctx: GraphRunContext[MyState]) -> NodeA | NodeB | End[str]:
    if ctx.state.error_message:
        return End(f"Error: {ctx.state.error_message}")

    if ctx.state.retry_count > 3:
        return NodeB()  # Error handling path

    if ctx.state.is_complete:
        return End("Already complete")

    return NodeA()  # Normal path
```

## State Model Patterns

### Basic State

```python
@dataclass
class WorkflowState:
    """Minimal state for simple workflow."""
    session_id: str
    input_data: str
    output_data: str = ""
```

### Tracking State

```python
@dataclass
class ProcessingState:
    """State with progress tracking."""
    session_id: str
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    current_item: str = ""
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
```

### Accumulator State

```python
@dataclass
class AggregatorState:
    """State for accumulating results."""
    session_id: str
    source_data: list[str]
    results: list[dict] = None
    summary: dict = None

    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.summary is None:
            self.summary = {}

    def add_result(self, key: str, value: any):
        """Helper method for adding results."""
        self.results.append({"key": key, "value": value})
```

### Configuration State

```python
@dataclass
class ConfiguredWorkflowState:
    """State with configuration."""
    session_id: str
    config: dict
    data: str = ""

    # Derived from config
    max_retries: int = 3
    timeout_seconds: int = 30
    enable_logging: bool = True

    def __post_init__(self):
        """Extract configuration."""
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout_seconds = self.config.get("timeout", 30)
        self.enable_logging = self.config.get("logging", True)
```

## Real-World Example: Story Creator Graph

**File:** `models/state_models.py`

```python
from dataclasses import dataclass

@dataclass
class Todo:
    """A todo item in the workflow."""
    id: str
    item_type: str
    description: str
    completed: bool = False

@dataclass
class StorySession:
    """Shared state for story creation workflow."""
    # Session info
    session_id: str
    subject: str
    player: str

    # Workflow state
    todo_list: list[Todo]
    current_todo: Todo = None
    completed_todos: list[str] = None

    # Data accumulation
    research_content: str = ""
    story_segments: list[str] = None

    # Progress tracking
    total_todos: int = 0
    completed_count: int = 0

    def __post_init__(self):
        if self.completed_todos is None:
            self.completed_todos = []
        if self.story_segments is None:
            self.story_segments = []
        self.total_todos = len(self.todo_list)
```

**File:** `nodes.py` (excerpt)

```python
@dataclass
class CreateTODO(BaseNode[StorySession]):
    research_content: str

    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO:
        print("[*] Generating story plan...")

        # Create todo list
        todo_list = await self.planner.create_plan(self.research_content, ctx.state.player)

        # Update state
        ctx.state.todo_list = todo_list
        ctx.state.total_todos = len(todo_list)
        ctx.state.research_content = self.research_content

        print(f"[+] Plan created with {len(todo_list)} todos")

        return GetNextTODO()


@dataclass
class GetNextTODO(BaseNode[StorySession]):
    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | End[dict]:
        # Check if todos remain
        incomplete_todos = [t for t in ctx.state.todo_list if not t.completed]

        if not incomplete_todos:
            # All done - return final result
            return End({
                "subject": ctx.state.subject,
                "segments": ctx.state.story_segments,
                "completed": ctx.state.completed_count
            })

        # Get next todo
        next_todo = incomplete_todos[0]
        ctx.state.current_todo = next_todo

        print(f"[*] Next todo: {next_todo.description}")

        return CreateStorySegment()


@dataclass
class CreateStorySegment(BaseNode[StorySession]):
    async def run(self, ctx: GraphRunContext[StorySession]) -> ReviewOutput:
        current_todo = ctx.state.current_todo

        print(f"[*] Creating: {current_todo.item_type}")

        # Create content based on todo
        segment = await self.creator.create(current_todo, ctx.state.research_content)

        # Add to state
        ctx.state.story_segments.append(segment)

        return ReviewOutput(segment=segment)
```

## State vs Parameters

### When to Use State

**Use State for:**
- Data shared across multiple nodes
- Accumulated results
- Progress tracking
- Configuration used by many nodes
- Session information
- Workflow metadata

### When to Use Parameters

**Use Parameters for:**
- Node-specific input
- Data that doesn't need to be shared
- Temporary processing values
- Direct node-to-node data flow

### Combined Approach

```python
@dataclass
class ProcessNode(BaseNode[MyState]):
    # Node-specific parameter
    operation_type: str

    async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
        # Read shared data from state
        input_data = ctx.state.current_data

        # Use node parameter for logic
        if self.operation_type == "transform":
            result = self.transform(input_data)
        else:
            result = self.process(input_data)

        # Write result to state
        ctx.state.result = result

        # Pass parameter to next node
        return NextNode(operation_type="validate")
```

## Advanced Patterns

### State Validation Node

```python
@dataclass
class ValidateState(BaseNode[WorkflowState]):
    """Validates state before proceeding."""

    async def run(self, ctx: GraphRunContext[WorkflowState]) -> ProcessData | End[str]:
        errors = []

        if not ctx.state.session_id:
            errors.append("Missing session_id")

        if not ctx.state.input_data:
            errors.append("Missing input_data")

        if ctx.state.retry_count > 5:
            errors.append("Too many retries")

        if errors:
            ctx.state.error_messages = errors
            return End(f"Validation failed: {', '.join(errors)}")

        return ProcessData()
```

### State Snapshot Node

```python
@dataclass
class SnapshotState(BaseNode[WorkflowState]):
    """Saves state snapshot for recovery."""

    async def run(self, ctx: GraphRunContext[WorkflowState]) -> NextNode:
        import json
        from pathlib import Path

        # Create snapshot
        snapshot = {
            "session_id": ctx.state.session_id,
            "step_count": ctx.state.step_count,
            "results": ctx.state.results,
            "timestamp": time.time()
        }

        # Save to file
        snapshot_dir = Path(f".mythline/snapshots/{ctx.state.session_id}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_file = snapshot_dir / f"step_{ctx.state.step_count}.json"
        snapshot_file.write_text(json.dumps(snapshot, indent=2))

        print(f"[+] State snapshot saved: {snapshot_file}")

        return NextNode()
```

### Progress Reporting Node

```python
@dataclass
class ReportProgress(BaseNode[ProcessingState]):
    """Reports progress to external system."""

    async def run(self, ctx: GraphRunContext[ProcessingState]) -> NextNode:
        progress = {
            "session_id": ctx.state.session_id,
            "current": ctx.state.processed_items,
            "total": ctx.state.total_items,
            "percent": ctx.state.progress_percent,
            "failures": ctx.state.failed_items
        }

        # Save progress for polling
        self.save_progress_file(ctx.state.session_id, progress)

        print(f"[*] Progress: {progress['percent']:.1f}%")

        return NextNode()

    def save_progress_file(self, session_id: str, progress: dict):
        from pathlib import Path
        import json

        progress_dir = Path(".mythline/progress")
        progress_dir.mkdir(parents=True, exist_ok=True)

        progress_file = progress_dir / f"{session_id}.json"
        progress_file.write_text(json.dumps(progress))
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class/node
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Best Practices

### State Initialization

```python
# GOOD: Initialize state with all required fields
state = WorkflowState(
    session_id="session_123",
    user_input="data",
    results=[],  # Initialize mutable defaults
    metadata={}
)

result = await graph.run(StartNode(), state=state)

# BAD: Partial initialization
state = WorkflowState()  # Missing required fields
```

### Mutable Defaults

```python
# GOOD: Initialize mutable defaults in __post_init__
@dataclass
class MyState:
    session_id: str
    results: list[str] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

# BAD: Mutable default in field
@dataclass
class MyState:
    session_id: str
    results: list[str] = []  # DON'T DO THIS! Shared across instances
```

### State Documentation

```python
@dataclass
class WorkflowState:
    """State for data processing workflow.

    Tracks processing progress and accumulates results across
    multiple processing steps.

    Attributes:
        session_id: Unique identifier for this workflow run
        input_data: Original data to process
        processed_count: Number of items processed successfully
        failed_count: Number of items that failed processing
        results: List of successful processing results
        errors: List of error messages from failed items
    """
    session_id: str
    input_data: list[str]
    processed_count: int = 0
    failed_count: int = 0
    results: list[dict] = None
    errors: list[str] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.errors is None:
            self.errors = []
```

### State Helper Methods

```python
@dataclass
class ProcessingState:
    total: int
    completed: int = 0
    failed: int = 0

    @property
    def remaining(self) -> int:
        """Items remaining to process."""
        return self.total - self.completed - self.failed

    @property
    def success_rate(self) -> float:
        """Percentage of successful items."""
        if self.completed == 0:
            return 0.0
        return (self.completed / (self.completed + self.failed)) * 100

    def mark_success(self):
        """Helper to mark item as completed."""
        self.completed += 1

    def mark_failure(self):
        """Helper to mark item as failed."""
        self.failed += 1
```

## Testing

### Testing Stateful Nodes

```python
import pytest
from pydantic_graph import GraphRunContext
from src.graphs.my_graph.nodes import ProcessNode
from src.graphs.my_graph.models.state_models import MyState

@pytest.mark.asyncio
async def test_node_updates_state():
    # Create state
    state = MyState(session_id="test", data="input")

    # Create context with state
    ctx = GraphRunContext(state=state)

    # Run node
    node = ProcessNode()
    result = await node.run(ctx)

    # Assert state was updated
    assert state.processed_count == 1
    assert state.results
```

### Testing Full Graph with State

```python
import pytest
from src.graphs.my_graph.graph import MyGraph

@pytest.mark.asyncio
async def test_graph_maintains_state():
    graph = MyGraph(session_id="test_session")

    result = await graph.run(user_input="test data")

    # Verify final result includes state data
    assert result["session"] == "test_session"
    assert result["steps"] > 0
    assert result["results"]
```

## Troubleshooting

### State Not Persisting

**Issue:** State changes don't carry forward

**Solution:**
- Verify nodes declare state type: `BaseNode[MyState]`
- Ensure context has state type: `GraphRunContext[MyState]`
- Check state passed to `graph.run(node, state=state)`

### Mutable Default Issues

**Issue:** Lists/dicts shared across state instances

**Solution:**
```python
# Wrong
@dataclass
class MyState:
    items: list = []  # Shared!

# Correct
@dataclass
class MyState:
    items: list = None

    def __post_init__(self):
        if self.items is None:
            self.items = []
```

### Type Errors

**Issue:** Type checker complains about state access

**Solution:**
```python
# Ensure proper type hints
async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
    #                                 ^^^^^^^^ Include state type
    value = ctx.state.field  # Now type-safe
```

## File Checklist

When creating a stateful graph:

- [ ] `__init__.py` - Export graph class
- [ ] `graph.py` - Graph with state initialization
- [ ] `nodes.py` - Stateful node implementations
- [ ] `models/state_models.py` - State dataclass definition
- [ ] Test files for nodes and graph
- [ ] Documentation

## Related Blueprints

- `graph_base.md` - Basic graph patterns
- `graph_with_agents.md` - Adding agents to stateful graphs
- `../agents/agent_orchestrator.md` - Orchestrator integration
