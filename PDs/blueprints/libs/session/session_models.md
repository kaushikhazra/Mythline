# Session Models Blueprint

This blueprint covers session dataclass definitions for graph workflows that require persistent state across multiple execution calls.

## Overview

Session models provide:
- Structured session state representation
- Lifecycle tracking (status, timestamps)
- Progress tracking (retry count, attempt history)
- Configuration storage (thresholds, limits)
- Helper methods for session management

## Purpose

Define the data structure for sessions that persist across graph execution calls, enabling:
- Retry logic tracking
- Progress monitoring
- Configuration persistence
- Attempt history for diagnostics
- Status-based workflow routing

## Session Model Structure

### Basic Session Model

**File:** `src/graphs/{graph_name}/models/session_models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ReviewSession:
    """Session state for multi-attempt workflows.

    Tracks retry attempts, configuration, and history across
    multiple graph execution calls. Includes best attempt tracking
    to handle non-deterministic quality variations.

    Attributes:
        session_id: Unique identifier for this session
        content_hash: SHA256 hash of content for change detection
        max_retries: Maximum retry attempts allowed
        quality_threshold: Required quality score to pass
        retry_count: Current attempt number (incremented on each call)
        status: Lifecycle status (in_progress, completed, needs_human)
        last_review: Most recent assessment result
        history: List of all attempt results
        best_attempt_number: Attempt number with highest score
        best_quality_score: Highest score achieved across all attempts
        created_at: Session creation timestamp (ISO 8601)
        updated_at: Last modification timestamp (ISO 8601)
    """
    session_id: str
    content_hash: str
    max_retries: int
    quality_threshold: float

    retry_count: int = 0
    status: str = "in_progress"
    last_review: dict | None = None
    history: list[dict] = field(default_factory=list)
    best_attempt_number: int = 0
    best_quality_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def increment_retry(self):
        """Increments retry count and updates timestamp."""
        self.retry_count += 1
        self.updated_at = datetime.now().isoformat()

    def add_attempt(self, score: float, review_details: dict) -> bool:
        """Records attempt in history and tracks if it's the best.

        Args:
            score: Quality score for this attempt
            review_details: Full review/assessment details

        Returns:
            True if this attempt has the highest score so far
        """
        attempt_record = {
            "attempt": self.retry_count,
            "quality_score": score,
            "timestamp": datetime.now().isoformat(),
            "review_summary": review_details.get("summary", ""),
            "details": review_details
        }

        self.history.append(attempt_record)
        self.last_review = review_details
        self.updated_at = datetime.now().isoformat()

        # Track best attempt
        is_best = score > self.best_quality_score
        if is_best:
            self.best_quality_score = score
            self.best_attempt_number = self.retry_count

        return is_best

    def should_wipe(self) -> bool:
        """Determines if session should be wiped.

        Returns:
            True if status indicates completion
        """
        return self.status in ["completed", "needs_human"]

    def needs_human_review(self) -> bool:
        """Checks if human review is needed.

        Returns:
            True if status is needs_human
        """
        return self.status == "needs_human"

    def is_complete(self) -> bool:
        """Checks if session is complete.

        Returns:
            True if status is completed
        """
        return self.status == "completed"

    def can_retry(self) -> bool:
        """Checks if more retries are allowed.

        Returns:
            True if retry_count < max_retries and not complete
        """
        return self.retry_count < self.max_retries and not self.is_complete()
```

## Session Lifecycle States

### Status Values

```python
# Standard status values
STATUS_IN_PROGRESS = "in_progress"   # Active, can retry
STATUS_COMPLETED = "completed"       # Success or gave up
STATUS_NEEDS_HUMAN = "needs_human"   # Escalated to human review
STATUS_FAILED = "failed"            # Unrecoverable error
STATUS_CANCELLED = "cancelled"       # User cancelled
```

### Status Transitions

```
in_progress → completed      (quality threshold met OR max retries reached)
in_progress → needs_human    (quality consistently poor, needs escalation)
in_progress → failed         (unrecoverable error occurred)
in_progress → cancelled      (user requested cancellation)

completed → [terminal]       (session wiped)
needs_human → [terminal]     (session wiped after human review)
failed → [terminal]          (session wiped after cleanup)
```

## Helper Methods

### Retry Management

```python
def increment_retry(self):
    """Increments retry count and updates timestamp."""
    self.retry_count += 1
    self.updated_at = datetime.now().isoformat()

def can_retry(self) -> bool:
    """Checks if more retries are allowed."""
    return self.retry_count < self.max_retries and not self.is_complete()
```

**Usage:**
```python
# In LoadOrCreateSession node
session = load_session(session_id) or create_session(...)
session.increment_retry()  # Always increment on load
ctx.state.session = session
```

### Attempt History with Best Tracking

```python
def add_attempt(self, score: float, review_details: dict) -> bool:
    """Records attempt in history and tracks if it's the best.

    Args:
        score: Quality score for this attempt
        review_details: Full review/assessment details

    Returns:
        True if this attempt has the highest score so far
    """
    attempt_record = {
        "attempt": self.retry_count,
        "quality_score": score,
        "timestamp": datetime.now().isoformat(),
        "review_summary": review_details.get("summary", ""),
        "details": review_details
    }

    self.history.append(attempt_record)
    self.last_review = review_details
    self.updated_at = datetime.now().isoformat()

    # Track best attempt
    is_best = score > self.best_quality_score
    if is_best:
        self.best_quality_score = score
        self.best_attempt_number = self.retry_count

    return is_best
```

**Usage:**
```python
# In UpdateSession node
is_best_so_far = ctx.state.session.add_attempt(
    score=ctx.state.quality_score,
    review_details=ctx.state.current_review
)

# Signal to caller if this is the best attempt
ctx.state.is_best_attempt = is_best_so_far

print(f"[+] Recorded attempt {ctx.state.session.retry_count}")
if is_best_so_far:
    print(f"[*] New best score: {ctx.state.quality_score:.2f}")
```

**Why Track Best Attempt:**

Due to the non-deterministic nature of content generation and AI assessment, quality scores may not improve monotonically:

```
Attempt 1: Score 0.65
Attempt 2: Score 0.78  ← Best (global maximum)
Attempt 3: Score 0.72  ← Degradation
Attempt 4: Score 0.69  ← Further degradation
```

By tracking the best attempt, the system can:
- Signal to caller when to store content versions
- Return metadata about the best attempt when max retries reached
- Allow caller to retrieve the highest-quality version

**Caller Responsibility:**
The session tracks only metadata (scores, attempt numbers). The caller is responsible for:
- Storing content when `is_best_so_far=True`
- Retrieving the best content using `best_attempt_number`
- Managing structured data that the reviewer doesn't need to understand

### Status Checks

```python
def should_wipe(self) -> bool:
    """Determines if session should be wiped."""
    return self.status in ["completed", "needs_human"]

def is_complete(self) -> bool:
    """Checks if session is complete."""
    return self.status == "completed"

def needs_human_review(self) -> bool:
    """Checks if human review is needed."""
    return self.status == "needs_human"
```

**Usage:**
```python
# In CheckCompletion node
if ctx.state.session.should_wipe():
    return WipeSession()
else:
    return SaveSession()
```

## Timestamp Management

### Auto-Update Pattern

```python
from datetime import datetime

@dataclass
class Session:
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def _update_timestamp(self):
        """Updates the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()

    def increment_retry(self):
        self.retry_count += 1
        self._update_timestamp()

    def add_attempt(self, score: float, review_details: dict):
        # Add attempt logic
        self._update_timestamp()
```

### Timestamp Format

```python
# Use ISO 8601 format
timestamp = datetime.now().isoformat()
# Example: "2025-01-15T10:30:45.123456"

# For consistency across timezones
from datetime import timezone
timestamp = datetime.now(timezone.utc).isoformat()
# Example: "2025-01-15T10:30:45.123456+00:00"
```

## History Tracking

### Attempt Record Structure

```python
attempt_record = {
    "attempt": 1,                        # Attempt number
    "quality_score": 0.72,               # Overall score
    "timestamp": "2025-01-15T10:00:00",  # When assessed
    "review_summary": "Good structure",  # Brief summary
    "details": {                         # Full assessment
        "strengths": ["Clear", "Well-organized"],
        "weaknesses": ["Missing citations"],
        "issues": [...]
    }
}
```

### History Usage

```python
# Get all attempt scores
scores = [attempt["quality_score"] for attempt in session.history]

# Check improvement trend
if len(session.history) >= 2:
    current_score = session.history[-1]["quality_score"]
    previous_score = session.history[-2]["quality_score"]
    improvement = current_score - previous_score

# Get best attempt
best_attempt = max(session.history, key=lambda x: x["quality_score"])
```

## Configuration Fields

### Threshold Configuration

```python
@dataclass
class Session:
    # Configuration fields
    max_retries: int                # Maximum attempts allowed
    quality_threshold: float        # Required score to pass (0.0-1.0)

    # Optional configurations
    timeout_seconds: int = 300      # Max time per attempt
    min_improvement: float = 0.05   # Required score improvement between attempts
    enable_caching: bool = True     # Cache intermediate results
```

### Dynamic Configuration

```python
@dataclass
class AdaptiveSession:
    base_threshold: float
    retry_count: int = 0
    max_retries: int = 3

    @property
    def current_threshold(self) -> float:
        """Lowers threshold with each retry for adaptive behavior."""
        reduction = 0.05 * self.retry_count
        return max(0.5, self.base_threshold - reduction)
```

## Advanced Patterns

### Session with Metadata

```python
@dataclass
class EnhancedSession:
    session_id: str
    content_hash: str

    # Standard fields
    retry_count: int = 0
    status: str = "in_progress"
    history: list[dict] = field(default_factory=list)

    # Metadata tracking
    metadata: dict = field(default_factory=dict)

    def add_metadata(self, key: str, value: any):
        """Adds metadata for tracking extra information."""
        self.metadata[key] = value
        self._update_timestamp()

    def get_metadata(self, key: str, default=None):
        """Retrieves metadata value."""
        return self.metadata.get(key, default)
```

**Usage:**
```python
# Track additional information
session.add_metadata("content_type", "blog_post")
session.add_metadata("user_id", "user_123")
session.add_metadata("source", "web_upload")

# Retrieve for context
content_type = session.get_metadata("content_type", "document")
```

### Session with Computed Properties

```python
@dataclass
class AnalyticsSession:
    history: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    @property
    def average_score(self) -> float:
        """Average quality score across all attempts."""
        if not self.history:
            return 0.0
        scores = [a["quality_score"] for a in self.history]
        return sum(scores) / len(scores)

    @property
    def best_score(self) -> float:
        """Highest quality score achieved."""
        if not self.history:
            return 0.0
        return max(a["quality_score"] for a in self.history)

    @property
    def improvement_rate(self) -> float:
        """Score improvement from first to last attempt."""
        if len(self.history) < 2:
            return 0.0
        first_score = self.history[0]["quality_score"]
        last_score = self.history[-1]["quality_score"]
        return last_score - first_score

    @property
    def retry_percentage(self) -> float:
        """Percentage of retries used."""
        return (self.retry_count / self.max_retries) * 100
```

## Serialization

### To Dictionary

```python
from dataclasses import asdict

session = ReviewSession(...)
session_dict = asdict(session)

# Result:
{
    "session_id": "review_001",
    "content_hash": "a8f3...",
    "max_retries": 3,
    "history": [...]
}
```

### From Dictionary

```python
session_dict = {...}  # From JSON or other source
session = ReviewSession(**session_dict)
```

### Custom Serialization

```python
@dataclass
class Session:
    # Fields...

    def to_dict(self) -> dict:
        """Custom serialization with transformations."""
        return {
            "session_id": self.session_id,
            "config": {
                "max_retries": self.max_retries,
                "threshold": self.quality_threshold
            },
            "progress": {
                "retry_count": self.retry_count,
                "status": self.status
            },
            "history": self.history,
            "timestamps": {
                "created": self.created_at,
                "updated": self.updated_at
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Custom deserialization."""
        return cls(
            session_id=data["session_id"],
            max_retries=data["config"]["max_retries"],
            quality_threshold=data["config"]["threshold"],
            retry_count=data["progress"]["retry_count"],
            status=data["progress"]["status"],
            history=data["history"],
            created_at=data["timestamps"]["created"],
            updated_at=data["timestamps"]["updated"]
        )
```

## Best Practices

### Mutable Defaults

```python
# GOOD: Use field(default_factory=list)
@dataclass
class Session:
    history: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

# BAD: Mutable default argument (shared across instances!)
@dataclass
class Session:
    history: list[dict] = []  # DON'T DO THIS
    metadata: dict = {}       # DON'T DO THIS
```

### Field Documentation

```python
@dataclass
class Session:
    """Session state for quality review workflow.

    Tracks retry attempts and quality scores across multiple
    execution calls.

    Attributes:
        session_id: Unique identifier for this session
        max_retries: Maximum retry attempts (default: 3)
        quality_threshold: Required score 0.0-1.0 (default: 0.8)
        retry_count: Current attempt number (auto-incremented)
        status: Lifecycle status (in_progress, completed, etc.)
        history: List of all attempt results with scores
    """
    session_id: str
    max_retries: int = 3
    quality_threshold: float = 0.8
    retry_count: int = 0
    status: str = "in_progress"
    history: list[dict] = field(default_factory=list)
```

### Type Hints

```python
from typing import Literal

SessionStatus = Literal["in_progress", "completed", "needs_human", "failed"]

@dataclass
class TypedSession:
    session_id: str
    status: SessionStatus = "in_progress"
    quality_threshold: float = 0.8
    history: list[dict[str, any]] = field(default_factory=list)
```

## Testing

```python
import pytest
from datetime import datetime
from src.graphs.my_graph.models.session_models import ReviewSession

def test_session_creation():
    session = ReviewSession(
        session_id="test_001",
        content_hash="abc123",
        max_retries=3,
        quality_threshold=0.8
    )

    assert session.session_id == "test_001"
    assert session.retry_count == 0
    assert session.status == "in_progress"
    assert session.history == []

def test_increment_retry():
    session = ReviewSession("test", "hash", 3, 0.8)

    session.increment_retry()

    assert session.retry_count == 1

    session.increment_retry()

    assert session.retry_count == 2

def test_add_attempt():
    session = ReviewSession("test", "hash", 3, 0.8)
    session.retry_count = 1

    session.add_attempt(
        score=0.75,
        review_details={"summary": "Good progress"}
    )

    assert len(session.history) == 1
    assert session.history[0]["quality_score"] == 0.75
    assert session.history[0]["attempt"] == 1
    assert session.last_review["summary"] == "Good progress"

def test_status_checks():
    session = ReviewSession("test", "hash", 3, 0.8)

    assert session.can_retry()
    assert not session.is_complete()

    session.status = "completed"

    assert not session.can_retry()
    assert session.is_complete()
    assert session.should_wipe()

def test_serialization():
    from dataclasses import asdict

    session = ReviewSession("test", "hash", 3, 0.8)
    session.add_attempt(0.75, {"summary": "test"})

    session_dict = asdict(session)

    assert session_dict["session_id"] == "test"
    assert len(session_dict["history"]) == 1

    restored = ReviewSession(**session_dict)

    assert restored.session_id == session.session_id
    assert restored.retry_count == session.retry_count
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## File Checklist

When creating session models:

- [ ] `session_models.py` file
- [ ] Session dataclass with all required fields
- [ ] Default values for optional fields
- [ ] `field(default_factory=list)` for mutable defaults
- [ ] Helper methods (increment_retry, add_attempt)
- [ ] Status check methods (can_retry, is_complete)
- [ ] Timestamp fields with auto-generation
- [ ] Type hints for all fields
- [ ] Docstrings for class and methods
- [ ] Test coverage

## Related Blueprints

- `session_manager.md` - CRUD operations for sessions
- `../../pydantic/graphs/graph_session_based.md` - Using sessions in graphs
- `../../pydantic/graphs/graph_stateful.md` - Stateful graph patterns
