# Base Graph Blueprint

This blueprint covers the fundamental Pydantic Graph pattern for creating finite state machine workflows without state management or agent integration.

## Overview

Base graphs:
- Finite State Machine (FSM) pattern
- Node-based workflow execution
- Conditional branching between nodes
- Sequential and parallel execution
- No state management (stateless)
- Simple linear or branching flows

## Conceptual Model

### Linear Flow
```
Node1 --> Node2 --> Node3 --> End
```

### Conditional Branching
```
Node1 --<condition A>--> Node2 --> End
  |
  +--<condition B>--> Node3 --> End
```

### Loops
```
Node1 --> Node2
  ^         |
  |         v
  +------- Node3
```

## Graph Structure

```
src/graphs/{graph_name}/
├── __init__.py
├── graph.py
└── nodes.py
```

## Implementation Pattern

### Simple Linear Graph

**File:** `nodes.py`

```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

@dataclass
class Step1(BaseNode):
    input_data: str

    async def run(self, ctx: GraphRunContext) -> Step2 | End[str]:
        """First step of processing."""
        print(f"Step 1: Processing {self.input_data}")

        processed = self.input_data.upper()

        if not processed:
            return End("Error: No data to process")

        return Step2(data=processed)


@dataclass
class Step2(BaseNode):
    data: str

    async def run(self, ctx: GraphRunContext) -> Step3:
        """Second step of processing."""
        print(f"Step 2: Transforming {self.data}")

        transformed = f"[{self.data}]"

        return Step3(final_data=transformed)


@dataclass
class Step3(BaseNode):
    final_data: str

    async def run(self, ctx: GraphRunContext) -> End[str]:
        """Final step - return result."""
        print(f"Step 3: Finalizing {self.final_data}")

        return End(self.final_data)
```

**File:** `graph.py`

```python
from pydantic_graph import Graph

from src.graphs.{graph_name}.nodes import Step1, Step2, Step3


class {GraphName}:
    def __init__(self):
        self.graph = Graph(nodes=[Step1, Step2, Step3])

    async def run(self, input_data: str) -> str:
        """Runs the graph workflow."""
        result = await self.graph.run(Step1(input_data=input_data))
        return result.output
```

**File:** `__init__.py`

```python
from .graph import {GraphName}

__all__ = ['{GraphName}']
```

## Key Concepts

### Node Definition

```python
from __future__ import annotations  # REQUIRED for forward references
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

@dataclass
class MyNode(BaseNode):
    # Input parameters as dataclass fields
    input_param: str
    optional_param: int = 0

    async def run(self, ctx: GraphRunContext) -> NextNode | End[str]:
        """Node logic goes here."""
        # Process data
        result = self.process(self.input_param)

        # Return next node or End
        if result:
            return NextNode(data=result)
        else:
            return End("Workflow complete")
```

### Node Return Types

**Single Next Node:**
```python
async def run(self, ctx: GraphRunContext) -> NextNode:
    return NextNode(data="value")
```

**Conditional Branching:**
```python
async def run(self, ctx: GraphRunContext) -> NodeA | NodeB | End[str]:
    if condition1:
        return NodeA(param=value)
    elif condition2:
        return NodeB(param=value)
    else:
        return End("Complete")
```

**End with Result:**
```python
async def run(self, ctx: GraphRunContext) -> End[str]:
    return End("Final result")

async def run(self, ctx: GraphRunContext) -> End[dict]:
    return End({"status": "complete", "data": result})
```

### The End Node

```python
from pydantic_graph import End

# Return with string
return End("Success")

# Return with dict
return End({"status": "complete", "count": 42})

# Return with custom object
return End(result_object)

# Return None
return End(None)
```

**Accessing End result:**
```python
result = await graph.run(StartNode())
output = result.output  # Access the End() value
```

## Conditional Branching Patterns

### Simple If/Else

```python
@dataclass
class DecisionNode(BaseNode):
    value: int

    async def run(self, ctx: GraphRunContext) -> PathA | PathB:
        if self.value > 10:
            return PathA(data=self.value)
        else:
            return PathB(data=self.value)
```

### Multiple Conditions

```python
@dataclass
class MultiDecision(BaseNode):
    category: str

    async def run(self, ctx: GraphRunContext) -> ProcessA | ProcessB | ProcessC | End[str]:
        if self.category == "type1":
            return ProcessA()
        elif self.category == "type2":
            return ProcessB()
        elif self.category == "type3":
            return ProcessC()
        else:
            return End(f"Unknown category: {self.category}")
```

### Validation Node

```python
@dataclass
class ValidateInput(BaseNode):
    user_input: str

    async def run(self, ctx: GraphRunContext) -> ProcessInput | End[str]:
        """Validates input before processing."""
        if not self.user_input or len(self.user_input) < 3:
            return End("Error: Input too short")

        if self.user_input.isnumeric():
            return End("Error: Input must contain text")

        return ProcessInput(validated_input=self.user_input)
```

## Loop Patterns

### Retry Loop

```python
@dataclass
class AttemptOperation(BaseNode):
    data: str
    attempt: int = 1
    max_attempts: int = 3

    async def run(self, ctx: GraphRunContext) -> ProcessData | AttemptOperation | End[str]:
        """Retries operation up to max attempts."""
        success = self.try_operation(self.data)

        if success:
            return ProcessData(data=self.data)

        if self.attempt >= self.max_attempts:
            return End(f"Failed after {self.max_attempts} attempts")

        # Loop back to self with incremented attempt
        return AttemptOperation(
            data=self.data,
            attempt=self.attempt + 1,
            max_attempts=self.max_attempts
        )

    def try_operation(self, data: str) -> bool:
        # Actual operation logic
        return True
```

### Iteration Loop

```python
@dataclass
class ProcessList(BaseNode):
    items: list[str]
    current_index: int = 0
    results: list[str] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    async def run(self, ctx: GraphRunContext) -> ProcessList | End[list]:
        """Processes list items one by one."""
        if self.current_index >= len(self.items):
            return End(self.results)

        # Process current item
        item = self.items[self.current_index]
        processed = f"Processed: {item}"
        self.results.append(processed)

        # Loop to next item
        return ProcessList(
            items=self.items,
            current_index=self.current_index + 1,
            results=self.results
        )
```

## Data Flow Between Nodes

### Passing Data Forward

```python
@dataclass
class ExtractData(BaseNode):
    source: str

    async def run(self, ctx: GraphRunContext) -> TransformData:
        extracted = self.extract(self.source)
        return TransformData(data=extracted)


@dataclass
class TransformData(BaseNode):
    data: str

    async def run(self, ctx: GraphRunContext) -> SaveData:
        transformed = self.transform(self.data)
        return SaveData(final_data=transformed)


@dataclass
class SaveData(BaseNode):
    final_data: str

    async def run(self, ctx: GraphRunContext) -> End[bool]:
        success = self.save(self.final_data)
        return End(success)
```

### Multiple Parameters

```python
@dataclass
class ProcessNode(BaseNode):
    param1: str
    param2: int
    param3: list[str]

    async def run(self, ctx: GraphRunContext) -> NextNode:
        result = self.process(self.param1, self.param2, self.param3)
        return NextNode(processed=result)
```

## Node Initialization

### Post-Init Processing

```python
@dataclass
class NodeWithDefaults(BaseNode):
    data: str
    processed_data: str = None
    timestamp: float = None

    def __post_init__(self):
        """Initialize computed fields."""
        if self.processed_data is None:
            self.processed_data = self.data.strip().lower()

        if self.timestamp is None:
            import time
            self.timestamp = time.time()

    async def run(self, ctx: GraphRunContext) -> End[str]:
        return End(self.processed_data)
```

### Complex Initialization

```python
@dataclass
class NodeWithSetup(BaseNode):
    config: dict
    processor: object = None

    def __post_init__(self):
        """Setup complex objects."""
        from src.libs.processor import Processor
        self.processor = Processor(self.config)

    async def run(self, ctx: GraphRunContext) -> End[str]:
        result = self.processor.process()
        return End(result)
```

## Graph Invocation

### Async Run

```python
class MyGraph:
    def __init__(self):
        self.graph = Graph(nodes=[Node1, Node2, Node3])

    async def run(self, input_data: str) -> str:
        result = await self.graph.run(Node1(input_data=input_data))
        return result.output
```

### Sync Run

```python
class MyGraph:
    def __init__(self):
        self.graph = Graph(nodes=[Node1, Node2, Node3])

    def run(self, input_data: str) -> str:
        result = self.graph.run_sync(Node1(input_data=input_data))
        return result.output
```

### Error Handling

```python
class MyGraph:
    def __init__(self):
        self.graph = Graph(nodes=[Node1, Node2, Node3])

    async def run(self, input_data: str) -> str:
        try:
            result = await self.graph.run(Node1(input_data=input_data))
            return result.output
        except Exception as e:
            print(f"Graph execution failed: {e}")
            return f"Error: {str(e)}"
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class/node
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Best Practices

### Node Naming

```python
# GOOD: Action-based names
class FetchData(BaseNode): ...
class ValidateInput(BaseNode): ...
class ProcessResults(BaseNode): ...
class SaveOutput(BaseNode): ...

# BAD: Generic names
class Node1(BaseNode): ...
class Handler(BaseNode): ...
class Step(BaseNode): ...
```

### Single Responsibility

```python
# GOOD: Each node does one thing
class FetchData(BaseNode):
    async def run(self, ctx) -> ValidateData:
        data = fetch_from_source()
        return ValidateData(data=data)

class ValidateData(BaseNode):
    async def run(self, ctx) -> ProcessData | End[str]:
        if not self.is_valid():
            return End("Validation failed")
        return ProcessData(data=self.data)

# BAD: Node doing too much
class FetchValidateProcess(BaseNode):
    async def run(self, ctx) -> End[str]:
        data = fetch_from_source()
        if not validate(data):
            return End("Failed")
        result = process(data)
        return End(result)
```

### Clear Return Types

```python
# GOOD: Explicit return types
async def run(self, ctx: GraphRunContext) -> ProcessNode | ValidateNode | End[str]:
    if condition1:
        return ProcessNode(data=x)
    elif condition2:
        return ValidateNode(data=y)
    else:
        return End("complete")

# BAD: Unclear returns
async def run(self, ctx: GraphRunContext):  # Missing return type
    return something  # What type is this?
```

### Logging

```python
from termcolor import colored

@dataclass
class ProcessNode(BaseNode):
    data: str

    async def run(self, ctx: GraphRunContext) -> NextNode | End[str]:
        print(colored(f"[*] Processing: {self.data}", "cyan"))

        result = self.process(self.data)

        if result:
            print(colored(f"[+] Processing complete", "green"))
            return NextNode(result=result)
        else:
            print(colored(f"[!] Processing failed", "red"))
            return End("Error: Processing failed")
```

## Testing

### Unit Testing Nodes

```python
import pytest
from src.graphs.my_graph.nodes import ProcessNode

@pytest.mark.asyncio
async def test_process_node():
    from pydantic_graph import GraphRunContext

    node = ProcessNode(data="test")
    ctx = GraphRunContext()

    result = await node.run(ctx)

    assert isinstance(result, NextNode)
    assert result.processed_data == "expected"
```

### Integration Testing Graph

```python
import pytest
from src.graphs.my_graph.graph import MyGraph

@pytest.mark.asyncio
async def test_full_graph():
    graph = MyGraph()

    result = await graph.run(input_data="test")

    assert result == "expected output"

@pytest.mark.asyncio
async def test_graph_error_path():
    graph = MyGraph()

    result = await graph.run(input_data="invalid")

    assert "Error" in result
```

## Common Patterns

### Entry Point Node

```python
@dataclass
class StartWorkflow(BaseNode):
    """Entry point that validates and routes."""
    config: dict

    async def run(self, ctx: GraphRunContext) -> ProcessA | ProcessB | End[str]:
        if not self.config:
            return End("Error: No configuration provided")

        workflow_type = self.config.get("type")

        if workflow_type == "A":
            return ProcessA(config=self.config)
        elif workflow_type == "B":
            return ProcessB(config=self.config)
        else:
            return End(f"Error: Unknown workflow type: {workflow_type}")
```

### Cleanup Node

```python
@dataclass
class CleanupResources(BaseNode):
    resource_ids: list[str]

    async def run(self, ctx: GraphRunContext) -> End[bool]:
        """Cleanup resources before ending."""
        for resource_id in self.resource_ids:
            self.cleanup(resource_id)

        return End(True)
```

### Aggregation Node

```python
@dataclass
class AggregateResults(BaseNode):
    results: list[str]

    async def run(self, ctx: GraphRunContext) -> End[dict]:
        """Aggregates results from multiple paths."""
        summary = {
            "count": len(self.results),
            "total": sum(int(r) for r in self.results if r.isnumeric()),
            "items": self.results
        }

        return End(summary)
```

## Troubleshooting

### Missing Forward References

**Issue:** `NameError: name 'NextNode' is not defined`

**Solution:**
```python
from __future__ import annotations  # Add this at the top!
```

### Type Hints Not Working

**Issue:** Return type errors

**Solution:**
```python
# Use Union with | operator
async def run(self, ctx: GraphRunContext) -> NodeA | NodeB | End[str]:
    ...
```

### Node Not Found

**Issue:** `Node not registered in graph`

**Solution:**
```python
# Ensure all nodes are in the nodes list
self.graph = Graph(nodes=[Node1, Node2, Node3])  # Include ALL nodes
```

## File Checklist

When creating a new base graph:

- [ ] `__init__.py` - Export graph class
- [ ] `graph.py` - Graph class with node registration
- [ ] `nodes.py` - All node implementations
- [ ] Test file in `tests/graphs/`
- [ ] Documentation in graph docstring

## Related Blueprints

- `graph_stateful.md` - Graphs with state management
- `graph_with_agents.md` - Integrating agents in graphs
- `../agents/agent_orchestrator.md` - Using graphs with orchestrators
