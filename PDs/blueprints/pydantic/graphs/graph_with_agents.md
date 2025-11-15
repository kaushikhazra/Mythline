# Graph with Agents Blueprint

This blueprint covers integrating Pydantic AI agents into Pydantic Graph workflows, combining stateful graph orchestration with intelligent AI agents for complex, multi-step AI workflows.

## Overview

Graphs with agents:
- Combine graph FSM orchestration with AI agents
- Stateful workflow with intelligent processing
- Agents initialized within nodes
- Structured output from agents to graph
- Review loops and quality control
- Progress tracking and error handling
- Complex multi-agent coordination

## Graph Structure

```
src/graphs/{graph_name}/
├── __init__.py
├── graph.py
├── nodes.py
└── models/              # May be shared with agent
    ├── state_models.py  # Graph state
    └── output_models.py # Agent output models (optional)
```

## Agent Integration Patterns

### Pattern 1: Agent Initialized in Node

**Most Common Pattern - Agent created when node is created**

```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from src.agents.my_agent.agent import MyAgent

@dataclass
class ProcessWithAgent(BaseNode[MyState]):
    input_data: str

    def __post_init__(self):
        """Initialize agent when node is created."""
        self.agent = None

    async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
        # Lazy initialization - create agent on first use
        if self.agent is None:
            self.agent = MyAgent(session_id=ctx.state.session_id)

        print("[*] Calling agent...")

        # Run agent
        result = await self.agent.run(self.input_data)

        # Store result in state
        ctx.state.agent_output = result.output

        print("[+] Agent completed")

        return NextNode()
```

**Why `__post_init__`?**
- Sets `self.agent = None` initially
- Allows lazy initialization in `run()`
- Agent gets session_id from context state
- Agent shared across retries (if node loops)

### Pattern 2: Multiple Agents in One Node

```python
@dataclass
class CoordinateAgents(BaseNode[MyState]):
    task_type: str

    def __post_init__(self):
        self.narrator_agent = None
        self.dialog_agent = None

    async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
        if self.task_type == "narration":
            if self.narrator_agent is None:
                self.narrator_agent = NarratorAgent(session_id=ctx.state.session_id)

            result = await self.narrator_agent.run(ctx.state.reference_text)
            ctx.state.output = result.output.text

        elif self.task_type == "dialogue":
            if self.dialog_agent is None:
                self.dialog_agent = DialogCreatorAgent(session_id=ctx.state.session_id)

            result = await self.dialog_agent.run(ctx.state.reference_text)
            ctx.state.output = result.output

        return NextNode()
```

### Pattern 3: Agent with Structured Output

```python
from src.agents.planner_agent.agent import PlannerAgent
from src.agents.planner_agent.models.output_models import TodoList

@dataclass
class CreatePlan(BaseNode[WorkflowState]):
    requirements: str

    def __post_init__(self):
        self.planner = None

    async def run(self, ctx: GraphRunContext[WorkflowState]) -> ExecutePlan:
        if self.planner is None:
            self.planner = PlannerAgent(session_id=ctx.state.session_id)

        print("[*] Generating plan...")

        # Agent returns structured output
        result = await self.planner.run(self.requirements)

        # result.output is TodoList model
        todo_list = result.output

        # Store in state
        ctx.state.todo_list = todo_list.items
        ctx.state.total_todos = len(todo_list.items)

        print(f"[+] Plan created with {len(todo_list.items)} items")

        return ExecutePlan()
```

## Real-World Example: Story Creator Graph

### State Model

**File:** `models/state_models.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Todo:
    """Todo item for story creation."""
    id: str
    type: str
    description: str
    prompt: str
    status: str = "pending"
    retry_count: int = 0
    review_comments: Optional[str] = None

@dataclass
class StorySession:
    """Graph state for story creation workflow."""
    # Session info
    session_id: str
    subject: str
    player: str

    # Workflow data
    todo_list: list[Todo]
    current_todo_index: int = 0

    # Accumulated output
    story_segments: list[str] = None

    def __post_init__(self):
        if self.story_segments is None:
            self.story_segments = []
```

### Node 1: Create Plan with Agent

```python
@dataclass
class CreateTODO(BaseNode[StorySession]):
    research_content: str

    def __post_init__(self):
        self.planner_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO:
        if self.planner_agent is None:
            self.planner_agent = StoryPlannerAgent(session_id=ctx.state.session_id)

        print(colored("[*] Generating story plan...", "cyan"))

        # Agent creates structured todo list
        todo_list = await self.planner_agent.run(
            self.research_content,
            ctx.state.player
        )

        # Update state
        ctx.state.todo_list = todo_list
        ctx.state.current_todo_index = 0

        print(colored(f"[+] Plan created with {len(todo_list)} todos", "green"))

        return GetNextTODO()
```

### Node 2: Get Next Todo (No Agent)

```python
@dataclass
class GetNextTODO(BaseNode[StorySession]):
    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | End[None]:
        # Check if more todos
        if ctx.state.current_todo_index < len(ctx.state.todo_list):
            current_todo = ctx.state.todo_list[ctx.state.current_todo_index]

            print(colored(f"[*] Processing todo {ctx.state.current_todo_index + 1}", "cyan"))

            return CreateStorySegment()
        else:
            print(colored("[+] All todos complete!", "green"))
            return End(None)
```

### Node 3: Create Content with Multiple Agents

```python
@dataclass
class CreateStorySegment(BaseNode[StorySession]):
    def __post_init__(self):
        self.narrator_agent = None
        self.dialog_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> ReviewOutput:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]

        # Build prompt
        prompt = self._build_prompt(current_todo, ctx.state)

        # Route to appropriate agent based on todo type
        if current_todo.type in ["dialogue", "conversation"]:
            if self.dialog_agent is None:
                self.dialog_agent = DialogCreatorAgent(session_id=ctx.state.session_id)

            print(colored("[*] Generating dialogue...", "cyan"))

            # Clear agent memory for fresh generation
            self.dialog_agent.messages = []

            result = await self.dialog_agent.run(prompt)
            current_todo.output = result.output

        else:  # Narration
            if self.narrator_agent is None:
                self.narrator_agent = NarratorAgent(session_id=ctx.state.session_id)

            print(colored("[*] Generating narration...", "cyan"))

            # Clear agent memory for fresh generation
            self.narrator_agent.messages = []

            result = await self.narrator_agent.run(prompt)
            current_todo.output = result.output.text

        print(colored("[+] Content generated", "green"))

        return ReviewOutput()

    def _build_prompt(self, todo: Todo, state: StorySession) -> str:
        """Builds prompt from todo and state."""
        prompt = todo.prompt.replace("{player}", state.player)

        if todo.review_comments:
            prompt += f"\n\nReview feedback:\n{todo.review_comments}"

        return prompt
```

### Node 4: Review with Agent (Loop Pattern)

```python
@dataclass
class ReviewOutput(BaseNode[StorySession]):
    def __post_init__(self):
        self.reviewer_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | WriteToFile:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]

        if self.reviewer_agent is None:
            self.reviewer_agent = ReviewerAgent(session_id=ctx.state.session_id)

        print(colored("[*] Reviewing content...", "cyan"))

        # Fresh review each time
        self.reviewer_agent.messages = []

        # Agent returns structured review
        review = await self.reviewer_agent.run(current_todo.output)

        # Check if improvement needed
        if review.need_improvement and review.score < 0.8:
            current_todo.retry_count += 1

            if current_todo.retry_count >= 10:
                print(colored(f"[!] Max retries reached (score: {review.score})", "yellow"))
                current_todo.status = "done"
                return WriteToFile()

            # Loop back to regenerate
            print(colored(f"[*] Needs improvement (score: {review.score}), retry {current_todo.retry_count}", "yellow"))
            current_todo.review_comments = review.comments
            return CreateStorySegment()

        # Quality acceptable
        print(colored(f"[+] Quality approved (score: {review.score})", "green"))
        current_todo.status = "done"
        return WriteToFile()
```

### Node 5: Write Output (No Agent)

```python
@dataclass
class WriteToFile(BaseNode[StorySession]):
    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]

        # Save segment
        ctx.state.story_segments.append(current_todo.output)

        # Move to next todo
        ctx.state.current_todo_index += 1

        print(colored("[+] Segment saved", "green"))

        # Loop back to get next todo
        return GetNextTODO()
```

### Graph Class

```python
from pydantic_graph import Graph

from src.graphs.story_creator_graph.models.state_models import StorySession
from src.graphs.story_creator_graph.nodes import (
    CreateTODO,
    GetNextTODO,
    CreateStorySegment,
    ReviewOutput,
    WriteToFile
)

class StoryCreatorGraph:
    def __init__(self, session_id: str, player_name: str):
        self.session_id = session_id
        self.player_name = player_name

        self.graph = Graph(
            nodes=[
                CreateTODO,
                GetNextTODO,
                CreateStorySegment,
                ReviewOutput,
                WriteToFile
            ]
        )

    async def run(self, subject: str, research_content: str) -> None:
        """Runs the story creation workflow."""
        # Initialize state
        state = StorySession(
            session_id=self.session_id,
            subject=subject,
            player=self.player_name,
            todo_list=[]
        )

        # Run graph
        await self.graph.run(
            CreateTODO(research_content=research_content),
            state=state
        )
```

## Key Patterns

### Agent Memory Management

**Clear Memory for Fresh Generation:**
```python
# Clear agent memory before each use
self.agent.messages = []
result = await self.agent.run(prompt)
```

**Maintain Memory Across Calls:**
```python
# Don't clear - agent remembers context
result = await self.agent.run(prompt)
```

### Lazy Agent Initialization

```python
def __post_init__(self):
    self.agent = None

async def run(self, ctx):
    if self.agent is None:
        self.agent = MyAgent(session_id=ctx.state.session_id)

    result = await self.agent.run(...)
```

**Benefits:**
- Agent only created if node actually runs
- Gets session_id from context
- Shared across retries if node loops

### Retry Loops with Agents

```python
@dataclass
class ProcessWithRetry(BaseNode[MyState]):
    max_retries: int = 3

    def __post_init__(self):
        self.agent = None

    async def run(self, ctx: GraphRunContext[MyState]) -> Success | ProcessWithRetry | End[str]:
        if self.agent is None:
            self.agent = MyAgent(session_id=ctx.state.session_id)

        # Track retries in state
        if ctx.state.retry_count >= self.max_retries:
            return End(f"Failed after {self.max_retries} retries")

        result = await self.agent.run(ctx.state.input)

        # Check quality
        if self.is_acceptable(result.output):
            return Success(output=result.output)

        # Retry
        ctx.state.retry_count += 1
        ctx.state.feedback = "Needs improvement: ..."

        return ProcessWithRetry(max_retries=self.max_retries)
```

### Conditional Agent Selection

```python
@dataclass
class RouteToAgent(BaseNode[MyState]):
    def __post_init__(self):
        self.agent_a = None
        self.agent_b = None
        self.agent_c = None

    async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
        task_type = ctx.state.task_type

        if task_type == "type_a":
            if self.agent_a is None:
                self.agent_a = AgentA(session_id=ctx.state.session_id)
            result = await self.agent_a.run(ctx.state.input)

        elif task_type == "type_b":
            if self.agent_b is None:
                self.agent_b = AgentB(session_id=ctx.state.session_id)
            result = await self.agent_b.run(ctx.state.input)

        else:
            if self.agent_c is None:
                self.agent_c = AgentC(session_id=ctx.state.session_id)
            result = await self.agent_c.run(ctx.state.input)

        ctx.state.output = result.output
        return NextNode()
```

### Progress Tracking

```python
def save_progress(session_id: str, status: str, current: int, total: int):
    """Saves progress for external polling."""
    from pathlib import Path
    import json

    progress_dir = Path(f".mythline/jobs/{session_id}")
    progress_dir.mkdir(parents=True, exist_ok=True)

    progress_file = progress_dir / "progress.json"
    progress_file.write_text(json.dumps({
        "status": status,
        "current": current,
        "total": total,
        "percent": (current / total * 100) if total > 0 else 0
    }))

@dataclass
class ProcessWithProgress(BaseNode[MyState]):
    def __post_init__(self):
        self.agent = None

    async def run(self, ctx: GraphRunContext[MyState]) -> NextNode:
        if self.agent is None:
            self.agent = MyAgent(session_id=ctx.state.session_id)

        # Update progress before processing
        save_progress(
            ctx.state.session_id,
            "processing",
            ctx.state.current_item,
            ctx.state.total_items
        )

        result = await self.agent.run(ctx.state.input)

        ctx.state.current_item += 1

        return NextNode()
```

## Best Practices

### Agent Lifecycle

```python
# GOOD: Lazy initialization in __post_init__ and run()
def __post_init__(self):
    self.agent = None

async def run(self, ctx):
    if self.agent is None:
        self.agent = MyAgent(session_id=ctx.state.session_id)
    result = await self.agent.run(...)

# BAD: Creating agent in __post_init__ without session_id
def __post_init__(self):
    self.agent = MyAgent(session_id="?")  # No session_id available yet!
```

### Memory Management

```python
# Clear memory for independent generations
self.agent.messages = []
result = await self.agent.run(prompt)

# Keep memory for contextual conversation
result = await self.agent.run(prompt)  # Agent remembers previous
```

### Error Handling

```python
async def run(self, ctx: GraphRunContext[MyState]) -> NextNode | End[str]:
    try:
        if self.agent is None:
            self.agent = MyAgent(session_id=ctx.state.session_id)

        result = await self.agent.run(ctx.state.input)

        ctx.state.output = result.output
        return NextNode()

    except Exception as e:
        error_msg = f"Agent failed: {str(e)}"
        print(colored(f"[!] {error_msg}", "red"))
        ctx.state.error = error_msg
        return End(error_msg)
```

### Structured Output Validation

```python
async def run(self, ctx: GraphRunContext[MyState]) -> NextNode | End[str]:
    if self.agent is None:
        self.agent = MyAgent(session_id=ctx.state.session_id)

    result = await self.agent.run(ctx.state.input)

    # Validate structured output
    if not result.output.required_field:
        return End("Error: Missing required field in agent output")

    if len(result.output.items) == 0:
        return End("Error: Agent returned empty list")

    # Store validated output
    ctx.state.validated_output = result.output

    return NextNode()
```

## Testing

### Testing Nodes with Agents

```python
import pytest
from unittest.mock import AsyncMock, patch
from pydantic_graph import GraphRunContext

from src.graphs.my_graph.nodes import ProcessNode
from src.graphs.my_graph.models.state_models import MyState

@pytest.mark.asyncio
@patch('src.agents.my_agent.agent.MyAgent')
async def test_node_calls_agent(mock_agent_class):
    # Setup mock
    mock_agent = AsyncMock()
    mock_agent.run.return_value = AsyncMock(output="test output")
    mock_agent_class.return_value = mock_agent

    # Create state and context
    state = MyState(session_id="test", input="test input")
    ctx = GraphRunContext(state=state)

    # Run node
    node = ProcessNode()
    result = await node.run(ctx)

    # Verify agent was called
    mock_agent.run.assert_called_once()
    assert state.output == "test output"
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_graph_with_agents():
    from src.graphs.my_graph.graph import MyGraph

    graph = MyGraph(session_id="test_session", config={})

    result = await graph.run(input_data="test")

    # Verify workflow completed
    assert result is not None
```

## Troubleshooting

### Agent Not Getting Session ID

**Issue:** `TypeError: __init__() missing 1 required positional argument: 'session_id'`

**Solution:**
```python
# Wrong - no session_id available
def __post_init__(self):
    self.agent = MyAgent(session_id=???)

# Correct - lazy init with session from context
def __post_init__(self):
    self.agent = None

async def run(self, ctx):
    if self.agent is None:
        self.agent = MyAgent(session_id=ctx.state.session_id)
```

### Agent Memory Not Clearing

**Issue:** Agent remembers previous generations when it shouldn't

**Solution:**
```python
# Clear memory before each independent generation
self.agent.messages = []
result = await self.agent.run(prompt)
```

### Retry Loop Not Working

**Issue:** Node loops infinitely

**Solution:**
```python
# Track retries in state
ctx.state.retry_count += 1

if ctx.state.retry_count >= max_retries:
    return End("Max retries exceeded")

return RetryNode()  # Loop back
```

## File Checklist

When creating graph with agents:

- [ ] `__init__.py` - Export graph class
- [ ] `graph.py` - Graph with state initialization
- [ ] `nodes.py` - Nodes with agent integration
- [ ] `models/state_models.py` - State dataclass
- [ ] Import agent classes correctly
- [ ] Test files for nodes and full graph
- [ ] Documentation

## Related Blueprints

- `graph_base.md` - Basic graph patterns
- `graph_stateful.md` - State management
- `../agents/agent_stateful_subagent.md` - Sub-agent patterns
- `../agents/agent_orchestrator.md` - Orchestrator agents
