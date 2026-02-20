# Session-Based Graph Blueprint

This blueprint covers Pydantic Graphs with session persistence, enabling workflows that span multiple non-blocking execution calls with retry logic and progress tracking.

## Overview

Session-based graphs:
- Persist state across multiple graph execution calls
- Enable non-blocking, caller-controlled retry patterns
- Track progress and history across attempts
- Support quality-based completion logic
- Allow process restart recovery
- Separate graph state (transient) from session state (persistent)

## Use Cases

Session-based graphs are ideal for:
- Quality assessment workflows with retry logic
- Multi-attempt content generation with improvement cycles
- Long-running processes that can be paused and resumed
- Workflows requiring human-in-the-loop at certain thresholds
- Processes where caller controls timing between retries
- Scenarios needing full attempt history for diagnostics

## Graph Structure

```
src/graphs/{graph_name}/
├── __init__.py
├── graph.py                      # Graph class with session initialization
├── nodes.py                      # Session-aware nodes
├── session_manager.py            # Session CRUD operations
└── models/
    ├── state_models.py          # Graph state (transient)
    ├── session_models.py        # Session state (persistent)
    └── output_models.py         # Result models
```

## Core Concepts

### State vs Session Separation

| Graph State (Transient) | Session State (Persistent) |
|-------------------------|----------------------------|
| Lives only during one execution | Persists across calls via file storage |
| Working data (web_data, current_result) | Configuration and history |
| Never serialized | JSON file storage |
| Includes session object reference | No reference to state |
| Workflow tracking (stage, errors) | Lifecycle tracking (status, timestamps) |

**Example:**

```python
@dataclass
class ReviewState:
    """Graph state - transient per execution."""
    session_id: str                    # Identifier
    content: str                       # Input data
    session: ReviewSession = None      # Reference to persistent session

    # Working data (not persisted)
    web_data: list[dict] = field(default_factory=list)
    current_review: dict = None
    quality_score: float = 0.0

    # Workflow tracking
    workflow_stage: str = ""
    error_message: str = ""

@dataclass
class ReviewSession:
    """Session state - persisted to disk."""
    session_id: str
    max_retries: int
    quality_threshold: float

    # Progress tracking (persisted)
    retry_count: int = 0
    status: str = "in_progress"
    history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
```

### Session Lifecycle

```
1. LoadOrCreateSession   → Session loaded from disk OR created new
2. [Processing Nodes]    → Session travels through ctx.state.session
3. UpdateSession         → Record attempt in session.history
4. CheckCompletion       → Evaluate session status
5a. SaveSession          → Persist to disk (retry path)
5b. WipeSession          → Delete from disk (completion path)
6. PopulateResult        → Return result to caller
```

## Implementation Pattern

### Graph Class with Sessions

**File:** `graph.py`

```python
from pydantic_graph import Graph

from src.graphs.{graph_name}.models.state_models import {GraphName}State
from src.graphs.{graph_name}.models.output_models import {GraphName}Result
from src.graphs.{graph_name}.nodes import (
    LoadOrCreateSession,
    ProcessData,
    UpdateSession,
    CheckCompletion,
    SaveSession,
    WipeSession,
    PopulateResult
)

class {GraphName}Graph:
    def __init__(self):
        self.graph = Graph(nodes=[
            LoadOrCreateSession,
            ProcessData,
            UpdateSession,
            CheckCompletion,
            SaveSession,
            WipeSession,
            PopulateResult
        ])

    async def run(
        self,
        content: str,
        session_id: str,
        max_retries: int = 3,
        quality_threshold: float = 0.8
    ) -> {GraphName}Result:
        """Runs one execution pass of the workflow.

        Non-blocking: Each call is start-to-end, no internal loops.
        Caller controls when to retry by calling again with same session_id.

        Args:
            content: Content to process
            session_id: Unique session identifier (same for retries)
            max_retries: Maximum retry attempts
            quality_threshold: Required score to pass

        Returns:
            Result with session status and completion flags
        """
        state = {GraphName}State(
            session_id=session_id,
            content=content,
            max_retries=max_retries,
            quality_threshold=quality_threshold
        )

        result = await self.graph.run(LoadOrCreateSession(), state=state)

        return result.output
```

### Session Management Nodes

#### LoadOrCreateSession Node

**Purpose:** Initialize session at workflow start

```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from src.graphs.{graph_name}.models.state_models import {GraphName}State
from src.graphs.{graph_name}.session_manager import load_session, create_session


@dataclass
class LoadOrCreateSession(BaseNode[{GraphName}State]):
    """Loads existing session or creates new one.

    Always increments retry_count to track current attempt.
    """

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> ProcessData:
        print(f"[*] LoadOrCreateSession for {ctx.state.session_id}")

        session = load_session(ctx.state.session_id)

        if session is None:
            print(f"[+] Creating new session {ctx.state.session_id}")

            max_retries = getattr(ctx.state, 'max_retries', 3)
            quality_threshold = getattr(ctx.state, 'quality_threshold', 0.8)

            session = create_session(
                session_id=ctx.state.session_id,
                content=ctx.state.content,
                max_retries=max_retries,
                quality_threshold=quality_threshold
            )
        else:
            print(f"[+] Loaded existing session (retry {session.retry_count})")

        # Always increment on load
        session.increment_retry()

        ctx.state.session = session
        ctx.state.workflow_stage = "session_loaded"

        return ProcessData()
```

#### UpdateSession Node

**Purpose:** Record attempt results in session history and track best attempt

```python
@dataclass
class UpdateSession(BaseNode[{GraphName}State]):
    """Records current attempt in session history and tracks best."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> CheckCompletion:
        print(f"[*] UpdateSession")
        ctx.state.workflow_stage = "updating_session"

        if ctx.state.session and ctx.state.current_result:
            is_best_so_far = ctx.state.session.add_attempt(
                score=ctx.state.quality_score,
                review_details=ctx.state.current_result
            )

            # Signal to caller if this is the best attempt
            ctx.state.is_best_attempt = is_best_so_far

            print(f"[+] Recorded attempt {ctx.state.session.retry_count}")
            if is_best_so_far:
                print(f"[*] New best score: {ctx.state.quality_score:.2f}")

        return CheckCompletion()
```

#### CheckCompletion Node

**Purpose:** Decision logic for retry vs completion

```python
@dataclass
class CheckCompletion(BaseNode[{GraphName}State]):
    """Evaluates completion conditions and routes accordingly."""

    async def run(
        self, ctx: GraphRunContext[{GraphName}State]
    ) -> WipeSession | SaveSession:
        print(f"[*] CheckCompletion")
        ctx.state.workflow_stage = "checking_completion"

        session = ctx.state.session
        score = ctx.state.quality_score
        threshold = session.quality_threshold
        retry_count = session.retry_count
        max_retries = session.max_retries

        print(f"[*] Score: {score:.2f}, Threshold: {threshold:.2f}")
        print(f"[*] Retry: {retry_count}/{max_retries}")

        # Success: Quality threshold met
        if score >= threshold:
            print(f"[+] Quality threshold met! ({score:.2f} >= {threshold:.2f})")
            session.status = "completed"
            return WipeSession()

        # Exhausted: Max retries reached
        if retry_count >= max_retries:
            print(f"[!] Max retries reached. Completing with current score.")
            session.status = "completed"
            return WipeSession()

        # Continue: More retries available
        if retry_count < max_retries:
            print(f"[*] Can retry. Saving session for next attempt...")
            session.status = "in_progress"
            return SaveSession()
```

#### SaveSession Node

**Purpose:** Persist session for retry

```python
@dataclass
class SaveSession(BaseNode[{GraphName}State]):
    """Saves session to disk for future retry."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> PopulateResult:
        print(f"[*] SaveSession")
        ctx.state.workflow_stage = "saving_session"

        if ctx.state.session:
            save_session(ctx.state.session)
            print(f"[+] Session saved for retry")

        return PopulateResult()
```

#### WipeSession Node

**Purpose:** Delete session on completion

```python
@dataclass
class WipeSession(BaseNode[{GraphName}State]):
    """Deletes session from disk on completion."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> PopulateResult:
        print(f"[*] WipeSession")
        ctx.state.workflow_stage = "wiping_session"

        wipe_session(ctx.state.session_id)
        print(f"[+] Session wiped")

        return PopulateResult()
```

#### PopulateResult Node

**Purpose:** Build final result for caller

```python
@dataclass
class PopulateResult(BaseNode[{GraphName}State]):
    """Builds result with session status flags and best attempt tracking."""

    async def run(self, ctx: GraphRunContext[{GraphName}State]) -> End[{GraphName}Result]:
        print(f"[*] PopulateResult")
        ctx.state.workflow_stage = "populating_result"

        session = ctx.state.session

        passed = ctx.state.quality_score >= session.quality_threshold
        max_retries_reached = session.retry_count >= session.max_retries
        session_completed = session.status in ["completed", "needs_human"]

        result = {GraphName}Result(
            session_id=session.session_id,
            retry_count=session.retry_count,
            max_retries=session.max_retries,
            quality_score=ctx.state.quality_score,
            quality_threshold=session.quality_threshold,
            passed=passed,
            max_retries_reached=max_retries_reached,
            session_completed=session_completed,
            is_best_so_far=ctx.state.is_best_attempt,
            best_attempt_number=session.best_attempt_number,
            best_quality_score=session.best_quality_score,
            result_details=ctx.state.current_result or {},
            timestamp=datetime.now().isoformat(),
            attempt_history=session.history
        )

        return End(result)
```

## Non-Blocking Retry Pattern

### Caller-Controlled Flow

```python
async def caller_retry_loop():
    """Example of caller controlling retry timing."""
    graph = MyGraph()
    session_id = "process_001"

    # Attempt 1
    result = await graph.run(
        content=original_content,
        session_id=session_id,
        max_retries=3,
        quality_threshold=0.8
    )

    print(f"Attempt 1: Score {result.quality_score:.2f}")

    # Check if can retry
    if not result.passed and not result.session_completed:
        # Caller decides when to retry (maybe improve content first)
        await asyncio.sleep(5)  # Wait 5 seconds

        # Attempt 2: Same session_id resumes from where it left off
        result = await graph.run(
            content=improved_content,
            session_id=session_id  # Same session_id = retry
        )

        print(f"Attempt 2: Score {result.quality_score:.2f}")

    # Check final result
    if result.passed:
        print("✓ Quality threshold met")
    elif result.max_retries_reached:
        print("✗ Max retries exhausted")
```

### Result Model for Caller

```python
from pydantic import BaseModel, Field

class WorkflowResult(BaseModel):
    """Result model with caller decision support and best attempt tracking."""
    session_id: str
    retry_count: int
    max_retries: int

    quality_score: float
    quality_threshold: float

    # Decision flags for caller
    passed: bool = Field(description="True if quality threshold met")
    max_retries_reached: bool = Field(description="True if retry limit hit")
    session_completed: bool = Field(description="True if session was wiped")

    # Best attempt tracking
    is_best_so_far: bool = Field(description="True if this attempt has highest score")
    best_attempt_number: int = Field(description="Attempt number with highest score")
    best_quality_score: float = Field(description="Highest score achieved")

    # Data
    result_details: dict = Field(description="Full result data")
    attempt_history: list[dict] = Field(description="All attempts")
    timestamp: str

    def can_retry(self) -> bool:
        """Helper for caller to check if retry is possible."""
        return not self.session_completed and not self.max_retries_reached

    def should_store_content(self) -> bool:
        """Helper for caller to check if content should be stored."""
        return self.is_best_so_far
```

**Usage with Best Attempt Tracking:**

```python
# Caller stores content versions when signaled
content_versions = {}

result = await graph.run(content, session_id)

# Store content when this is the best attempt
if result.should_store_content():
    content_versions[result.retry_count] = content
    print(f"[+] Stored content for attempt #{result.retry_count}")

# At the end, retrieve best version if needed
if result.max_retries_reached and not result.passed:
    best_content = content_versions.get(result.best_attempt_number)
    if best_content:
        print(f"[*] Using best attempt #{result.best_attempt_number}")
        print(f"[*] Best score: {result.best_quality_score:.2f} vs last: {result.quality_score:.2f}")
```

## Quality-Based Completion Logic

### Dual Condition Pattern

```python
async def run(self, ctx: GraphRunContext[State]) -> WipeSession | SaveSession:
    """Completion logic with two exit conditions."""
    session = ctx.state.session
    score = ctx.state.quality_score

    # Primary success condition
    if score >= session.quality_threshold:
        session.status = "completed"
        return WipeSession()

    # Exhaustion condition
    if session.retry_count >= session.max_retries:
        session.status = "completed"
        return WipeSession()

    # Continue condition
    return SaveSession()
```

### Human Escalation Pattern

```python
async def run(self, ctx: GraphRunContext[State]) -> WipeSession | SaveSession | InvokeHuman:
    """Completion logic with human escalation."""
    session = ctx.state.session
    score = ctx.state.quality_score

    # Success
    if score >= session.quality_threshold:
        session.status = "completed"
        return WipeSession()

    # Exhaustion with low quality → escalate
    if session.retry_count >= session.max_retries and score < 0.5:
        print(f"[!] Low quality after max retries. Invoking human review.")
        session.status = "needs_human"
        return InvokeHuman()  # Blocking or async human review

    # Exhaustion with acceptable quality
    if session.retry_count >= session.max_retries:
        session.status = "completed"
        return WipeSession()

    # Continue
    return SaveSession()
```

### Adaptive Thresholds

```python
async def run(self, ctx: GraphRunContext[State]) -> WipeSession | SaveSession:
    """Adaptive threshold based on retry count."""
    session = ctx.state.session
    score = ctx.state.quality_score

    # Lower threshold with each retry
    adaptive_threshold = session.quality_threshold - (0.05 * session.retry_count)
    adaptive_threshold = max(0.5, adaptive_threshold)  # Floor at 0.5

    print(f"[*] Adaptive threshold: {adaptive_threshold:.2f}")

    if score >= adaptive_threshold:
        session.status = "completed"
        return WipeSession()

    if session.retry_count >= session.max_retries:
        session.status = "completed"
        return WipeSession()

    return SaveSession()
```

## Advanced Patterns

### Content Change Detection

```python
@dataclass
class LoadOrCreateSession(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> NextNode:
        session = load_session(ctx.state.session_id)

        if session:
            # Check if content changed
            current_hash = compute_content_hash(ctx.state.content)

            if session.content_hash != current_hash:
                print(f"[*] Content changed, resetting retry count")
                session.retry_count = 0
                session.content_hash = current_hash
                session.history = []

        else:
            session = create_session(...)

        session.increment_retry()
        ctx.state.session = session

        return NextNode()
```

### Improvement Tracking

```python
@dataclass
class CheckCompletion(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> WipeSession | SaveSession:
        session = ctx.state.session
        score = ctx.state.quality_score

        # Check improvement trend
        if len(session.history) >= 2:
            previous_score = session.history[-2]["quality_score"]
            improvement = score - previous_score

            if improvement < 0.02:  # Less than 2% improvement
                print(f"[*] Minimal improvement ({improvement:.2%})")

                if session.retry_count >= session.max_retries:
                    print(f"[!] Plateaued. Stopping retries.")
                    session.status = "completed"
                    return WipeSession()

        # Standard logic
        if score >= session.quality_threshold:
            session.status = "completed"
            return WipeSession()

        if session.retry_count >= session.max_retries:
            session.status = "completed"
            return WipeSession()

        return SaveSession()
```

### Session Recovery

```python
@dataclass
class LoadOrCreateSession(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> NextNode:
        session = load_session(ctx.state.session_id)

        if session:
            # Check for stale session
            updated_time = datetime.fromisoformat(session.updated_at)
            age = datetime.now() - updated_time

            if age.total_seconds() > 3600:  # 1 hour
                print(f"[!] Stale session detected (age: {age})")
                print(f"[*] Resetting session")

                wipe_session(ctx.state.session_id)
                session = None

        if session is None:
            session = create_session(...)

        session.increment_retry()
        ctx.state.session = session

        return NextNode()
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class/node
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Best Practices

### Always Increment on Load

```python
# GOOD: Increment immediately after load/create
session = load_session(session_id) or create_session(...)
session.increment_retry()  # Always increment
ctx.state.session = session

# BAD: Forgetting to increment
session = load_session(session_id) or create_session(...)
ctx.state.session = session  # retry_count not updated
```

### Separate Concerns

```python
# GOOD: Session management in dedicated nodes
LoadOrCreateSession → [Processing] → UpdateSession → CheckCompletion → Save/Wipe

# BAD: Session logic mixed with processing
ProcessDataAndManageSession  # Does too much
```

### Status Consistency

```python
# GOOD: Set status before routing
if score >= threshold:
    session.status = "completed"  # Set first
    return WipeSession()          # Then route

# BAD: Routing without status update
if score >= threshold:
    return WipeSession()  # Status still "in_progress"
```

### Comprehensive Results

```python
# GOOD: Include all decision support flags
result = Result(
    passed=score >= threshold,
    max_retries_reached=retry_count >= max_retries,
    session_completed=session.status in ["completed", "needs_human"],
    can_retry=retry_count < max_retries and session.status == "in_progress",
    attempt_history=session.history
)

# BAD: Minimal result, caller can't make decisions
result = Result(score=score)
```

## Testing

### Testing Session Nodes

```python
import pytest
from pydantic_graph import GraphRunContext
from src.graphs.my_graph.nodes import LoadOrCreateSession, CheckCompletion
from src.graphs.my_graph.models.state_models import MyState
from src.graphs.my_graph.models.session_models import MySession

@pytest.mark.asyncio
async def test_load_or_create_new_session():
    state = MyState(session_id="test_001", content="test")
    ctx = GraphRunContext(state=state)

    node = LoadOrCreateSession()
    result = await node.run(ctx)

    assert ctx.state.session is not None
    assert ctx.state.session.session_id == "test_001"
    assert ctx.state.session.retry_count == 1  # Incremented

@pytest.mark.asyncio
async def test_check_completion_pass():
    session = MySession("test", "hash", 3, 0.8)
    session.retry_count = 1

    state = MyState(session_id="test", content="test")
    state.session = session
    state.quality_score = 0.85  # Above threshold

    ctx = GraphRunContext(state=state)

    node = CheckCompletion()
    result = await node.run(ctx)

    assert isinstance(result, WipeSession)
    assert session.status == "completed"

@pytest.mark.asyncio
async def test_check_completion_retry():
    session = MySession("test", "hash", 3, 0.8)
    session.retry_count = 1

    state = MyState(session_id="test", content="test")
    state.session = session
    state.quality_score = 0.70  # Below threshold

    ctx = GraphRunContext(state=state)

    node = CheckCompletion()
    result = await node.run(ctx)

    assert isinstance(result, SaveSession)
    assert session.status == "in_progress"
```

### Testing Full Workflow

```python
@pytest.mark.asyncio
async def test_full_retry_workflow():
    graph = MyGraph()

    # Attempt 1: Fail
    result1 = await graph.run(
        content="test content",
        session_id="workflow_test",
        max_retries=3,
        quality_threshold=0.8
    )

    assert result1.retry_count == 1
    assert not result1.session_completed

    # Attempt 2: Pass
    result2 = await graph.run(
        content="improved content",
        session_id="workflow_test"
    )

    assert result2.retry_count == 2
    assert result2.passed
    assert result2.session_completed
```

## Advanced Patterns

### Passing Additional Context to Assessment Nodes

When performing quality assessment or validation, passing additional context helps the assessment be more accurate and requirement-aligned. This pattern shows how to include original requirements or specifications in the assessment process.

**State Definition:**

```python
@dataclass
class ReviewState:
    session_id: str
    content: str
    original_context: str = ""  # Original requirements or specifications
    max_retries: int = 3
    quality_threshold: float = 0.8

    session: ReviewSession = None
    current_review: dict = None
    quality_score: float = 0.0
```

**Graph Entry Point:**

```python
async def review(
    self,
    content: str,
    session_id: str,
    original_context: str = "",  # Accept context parameter
    max_retries: int = 3,
    quality_threshold: float = 0.8
) -> ReviewResult:
    state = ReviewState(
        session_id=session_id,
        content=content,
        original_context=original_context,  # Include in state
        max_retries=max_retries,
        quality_threshold=quality_threshold
    )

    return await self.graph.run(state, self.initial_node)
```

**Assessment Node Using Context:**

```python
@dataclass
class PerformAssessment(BaseNode[ReviewState]):
    """Performs quality assessment with original context."""

    async def run(self, ctx: GraphRunContext[ReviewState]) -> UpdateSession:
        prompt_parts = [f"# Content to Review\n\n{ctx.state.content}"]

        # Include original context if provided
        if ctx.state.original_context:
            prompt_parts.append(
                f"\n# Review Against These Requirements:\n\n{ctx.state.original_context}"
            )

        prompt = "\n".join(prompt_parts)

        # Call assessment agent
        result = await self.assessor_agent.run(prompt)

        ctx.state.current_review = result.data
        ctx.state.quality_score = result.data.get("quality_score", 0.0)

        return UpdateSession()
```

**Usage Example:**

```python
# Original creation specification
creation_spec = """
Write a 500-word technical blog post about JWT authentication.
Must include:
- Definition of JWT
- How JWTs work (3-step process)
- One practical use case
Tone: Educational but accessible to beginners
"""

# Generated content (from separate generation step)
generated_content = "..."

# Review with context
result = await graph.review(
    content=generated_content,
    original_context=creation_spec,  # Pass original requirements
    session_id="review_001",
    quality_threshold=0.85
)

# Assessment will validate against original requirements
if result.passed:
    print("Content meets original requirements")
else:
    print(f"Issues: {result.review_details['issues']}")
```

**Benefits:**
- Enables requirement validation (not just generic quality assessment)
- Complete traceability: specification → generation → review
- More actionable feedback tied to specific requirements
- Assessment can check for missing required elements

**When to Use:**
- Content was generated from a prompt or specification
- Requirements are explicit and verifiable
- Assessment should validate completeness (not just quality)
- Multiple stakeholders need to verify against original intent

## Troubleshooting

### Session Not Persisting

**Issue:** Session resets on each call

**Solutions:**
- Verify `session.increment_retry()` is called
- Check `save_session()` is executed
- Confirm session_id is consistent across calls
- Check file permissions on session directory

### Infinite Retry Loop

**Issue:** Graph retries forever

**Solutions:**
- Ensure `retry_count` increments on each call
- Verify `CheckCompletion` routing logic
- Check that `max_retries` is set correctly
- Add logging to track retry_count

### Session Not Wiped

**Issue:** Completed sessions remain on disk

**Solutions:**
- Verify `WipeSession` node is reached
- Check `CheckCompletion` returns `WipeSession` correctly
- Confirm `session.status` is set to "completed"
- Check file permissions for deletion

## File Checklist

When implementing session-based graph:

- [ ] `graph.py` - Graph class with session parameters
- [ ] `nodes.py` - Session management nodes (Load, Update, Check, Save, Wipe, Result)
- [ ] `session_manager.py` - CRUD operations
- [ ] `models/state_models.py` - Graph state with session reference
- [ ] `models/session_models.py` - Session dataclass
- [ ] `models/output_models.py` - Result model with decision flags
- [ ] Session increment in LoadOrCreateSession
- [ ] Dual routing in CheckCompletion
- [ ] Test coverage for session lifecycle
- [ ] Documentation

## Related Blueprints

- `../../libs/session/session_manager.md` - Session CRUD operations
- `../../libs/session/session_models.md` - Session dataclass patterns
- `graph_stateful.md` - Stateful graph foundation
- `graph_with_agents.md` - Integrating agents with session-based graphs
- `../../../patterns/content_reviewer/content_reviewer_pattern.md` - Full example usage
