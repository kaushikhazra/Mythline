# Session Manager Blueprint

This blueprint covers session file persistence for graph workflows that require state to persist across multiple execution calls.

## Overview

Session manager provides:
- File-based session persistence (JSON format)
- CRUD operations for session lifecycle
- Session directory management
- Content hash computation for change detection
- Graceful error handling

## Purpose

Enable graphs to maintain state across multiple non-blocking execution calls, allowing:
- Retry logic with caller-controlled timing
- Recovery from process crashes
- Progress tracking across calls
- Configuration persistence

## Storage Structure

```
.mythline/{component_name}/sessions/
└── {session_id}.json
```

**Example:**
```
.mythline/content_reviewer/sessions/
├── review_001.json
├── review_002.json
└── batch_2024_01.json
```

## Implementation Pattern

### Module Structure

**File:** `src/libs/session/session_manager.py`

```python
from pathlib import Path
import json
import hashlib
from dataclasses import asdict

SESSION_DIR = Path(".mythline/{component_name}/sessions")

def create_session(session_id: str, **config) -> Session:
    pass

def load_session(session_id: str) -> Session | None:
    pass

def save_session(session: Session):
    pass

def wipe_session(session_id: str):
    pass

def compute_content_hash(content: str) -> str:
    pass
```

### CRUD Operations

#### Create Session

```python
def create_session(
    session_id: str,
    content: str,
    max_retries: int,
    quality_threshold: float
) -> ReviewSession:
    """Creates a new session with initial configuration.

    Args:
        session_id: Unique identifier for this session
        content: Content to track (used for hash computation)
        max_retries: Maximum retry attempts allowed
        quality_threshold: Required quality score threshold

    Returns:
        New ReviewSession instance
    """
    content_hash = compute_content_hash(content)

    return ReviewSession(
        session_id=session_id,
        content_hash=content_hash,
        max_retries=max_retries,
        quality_threshold=quality_threshold,
        retry_count=0,
        status="in_progress",
        history=[],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
```

#### Load Session

```python
def load_session(session_id: str) -> ReviewSession | None:
    """Loads session from disk.

    Args:
        session_id: Session identifier

    Returns:
        ReviewSession if exists, None otherwise
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    if not session_file.exists():
        return None

    try:
        data = json.loads(session_file.read_text())
        return ReviewSession(**data)
    except Exception as e:
        print(f"[!] Error loading session {session_id}: {e}")
        return None
```

#### Save Session

```python
def save_session(session: ReviewSession):
    """Persists session to disk.

    Args:
        session: Session instance to save
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session.session_id}.json"

    try:
        session_data = asdict(session)
        session_file.write_text(json.dumps(session_data, indent=2))
        print(f"[+] Session {session.session_id} saved")
    except Exception as e:
        print(f"[!] Error saving session {session.session_id}: {e}")
```

#### Wipe Session

```python
def wipe_session(session_id: str):
    """Deletes session file from disk.

    Args:
        session_id: Session identifier to delete
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    try:
        if session_file.exists():
            session_file.unlink()
            print(f"[+] Session {session_id} wiped")
        else:
            print(f"[*] Session {session_id} does not exist")
    except Exception as e:
        print(f"[!] Error wiping session {session_id}: {e}")
```

### Helper Functions

#### Content Hash Computation

```python
def compute_content_hash(content: str) -> str:
    """Computes SHA256 hash of content for change detection.

    Args:
        content: Content to hash

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode()).hexdigest()
```

**Usage:**
- Store hash on session creation
- Compare hash on subsequent loads to detect content changes
- Enables caller to modify content between retries

## JSON File Format

**File:** `.mythline/{component}/sessions/{session_id}.json`

```json
{
  "session_id": "review_123",
  "content_hash": "a8f3c2e1d5b9...",
  "max_retries": 3,
  "quality_threshold": 0.8,
  "retry_count": 2,
  "status": "in_progress",
  "last_review": {
    "quality_score": 0.72,
    "summary": "Good structure, needs accuracy improvements"
  },
  "history": [
    {
      "attempt": 1,
      "quality_score": 0.65,
      "timestamp": "2025-01-15T10:00:00",
      "review_summary": "Initial assessment"
    },
    {
      "attempt": 2,
      "quality_score": 0.72,
      "timestamp": "2025-01-15T10:05:00",
      "review_summary": "Improved from first attempt"
    }
  ],
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T10:05:00"
}
```

**Format Guidelines:**
- Use `indent=2` for human readability
- Store ISO 8601 timestamps
- Include configuration fields (max_retries, thresholds)
- Track full history for diagnostics

## Usage Pattern

### In Graph Workflow

```python
from src.libs.session.session_manager import (
    create_session, load_session, save_session, wipe_session
)

@dataclass
class LoadOrCreateSession(BaseNode[GraphState]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> NextNode:
        session = load_session(ctx.state.session_id)

        if session is None:
            session = create_session(
                session_id=ctx.state.session_id,
                content=ctx.state.content,
                max_retries=ctx.state.max_retries,
                quality_threshold=ctx.state.quality_threshold
            )

        session.increment_retry()
        ctx.state.session = session

        return NextNode()

@dataclass
class SaveSession(BaseNode[GraphState]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> NextNode:
        save_session(ctx.state.session)
        return NextNode()

@dataclass
class WipeSession(BaseNode[GraphState]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> NextNode:
        wipe_session(ctx.state.session_id)
        return NextNode()
```

## Error Handling

### Graceful Degradation

```python
def load_session(session_id: str) -> ReviewSession | None:
    try:
        # Load and deserialize
        data = json.loads(session_file.read_text())
        return ReviewSession(**data)
    except json.JSONDecodeError as e:
        print(f"[!] Corrupt session file {session_id}: {e}")
        return None
    except Exception as e:
        print(f"[!] Error loading session {session_id}: {e}")
        return None
```

### Directory Existence

```python
def save_session(session: ReviewSession):
    # Always ensure directory exists before operations
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    session_file = SESSION_DIR / f"{session.session_id}.json"
    session_file.write_text(json.dumps(asdict(session), indent=2))
```

## Best Practices

### Session ID Naming

```python
# GOOD: Descriptive, unique identifiers
session_id = f"review_{content_type}_{timestamp}"
session_id = f"batch_{batch_id}_{item_number}"
session_id = f"{user_id}_draft_{version}"

# BAD: Generic, collision-prone
session_id = "session1"
session_id = "temp"
```

### Content Hash Usage

```python
# Check if content changed between retries
def load_session_with_validation(session_id: str, current_content: str) -> Session | None:
    session = load_session(session_id)

    if session is None:
        return None

    current_hash = compute_content_hash(current_content)

    if session.content_hash != current_hash:
        print(f"[*] Content changed, resetting retry count")
        session.retry_count = 0
        session.content_hash = current_hash

    return session
```

### Session Cleanup

```python
# Clean up old sessions periodically
def cleanup_old_sessions(max_age_days: int = 7):
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=max_age_days)

    for session_file in SESSION_DIR.glob("*.json"):
        if session_file.stat().st_mtime < cutoff.timestamp():
            session_file.unlink()
            print(f"[+] Cleaned up old session: {session_file.stem}")
```

### Atomic Writes

```python
def save_session(session: ReviewSession):
    """Save with atomic write to prevent corruption."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    session_file = SESSION_DIR / f"{session.session_id}.json"
    temp_file = SESSION_DIR / f"{session.session_id}.tmp"

    try:
        # Write to temp file first
        temp_file.write_text(json.dumps(asdict(session), indent=2))

        # Atomic rename
        temp_file.replace(session_file)

    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise e
```

## Testing

### Testing CRUD Operations

```python
import pytest
from pathlib import Path
from src.libs.session.session_manager import (
    create_session, load_session, save_session, wipe_session
)

@pytest.fixture
def test_session_dir(tmp_path):
    global SESSION_DIR
    SESSION_DIR = tmp_path / "sessions"
    return SESSION_DIR

def test_create_and_load_session(test_session_dir):
    session = create_session(
        session_id="test_001",
        content="Test content",
        max_retries=3,
        quality_threshold=0.8
    )

    save_session(session)

    loaded = load_session("test_001")

    assert loaded.session_id == "test_001"
    assert loaded.max_retries == 3
    assert loaded.retry_count == 0

def test_wipe_session(test_session_dir):
    session = create_session("test_002", "content", 3, 0.8)
    save_session(session)

    assert (test_session_dir / "test_002.json").exists()

    wipe_session("test_002")

    assert not (test_session_dir / "test_002.json").exists()

def test_load_nonexistent_session(test_session_dir):
    result = load_session("nonexistent")
    assert result is None
```

## Troubleshooting

### Session Not Found

**Issue:** `load_session()` returns None

**Solutions:**
- Verify session_id matches exactly
- Check SESSION_DIR path is correct
- Ensure session wasn't wiped by another process
- Check file permissions

### Corrupt Session File

**Issue:** JSON decode error

**Solutions:**
- Implement atomic writes (see best practices)
- Add validation on load
- Keep backup copies before updates
- Log corruption events for debugging

### Permission Errors

**Issue:** Cannot write to session directory

**Solutions:**
- Ensure directory has write permissions
- Check disk space
- Use `mkdir(parents=True, exist_ok=True)` before all operations

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## File Checklist

When implementing session manager:

- [ ] `session_manager.py` - CRUD functions
- [ ] `session_models.py` - Session dataclass definition
- [ ] Directory constant (SESSION_DIR)
- [ ] Create, load, save, wipe functions
- [ ] Content hash helper function
- [ ] Error handling for all operations
- [ ] Test coverage for CRUD operations
- [ ] Documentation

## Related Blueprints

- `session_models.md` - Session dataclass definition
- `../graphs/graph_session_based.md` - Using sessions in graphs
- `../../pydantic/graphs/graph_stateful.md` - Stateful graph foundation
