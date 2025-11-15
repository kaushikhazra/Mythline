# Backend: Session Management

Managing user sessions and session-based data in FastAPI.

---

## Overview

**Use when:** Multi-session support, session persistence, session switching, session cleanup.

**Pattern:**
```
List Sessions → Load Session → Create Session → Delete Session
```

---

## Session Storage

### Session Directory Structure

```
.mythline/
└── {agent_id}/
    └── context_memory/
        ├── session_20240113_143022.json
        ├── session_20240113_150033.json
        └── session_20240114_091544.json
```

---

## List Sessions

### Basic Session Listing

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from pathlib import Path
from datetime import datetime

router = APIRouter()

class SessionInfo(BaseModel):
    session_id: str
    last_modified: str

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    agent_id = "story_researcher"
    context_dir = Path(".mythline") / agent_id / "context_memory"

    if not context_dir.exists():
        return []

    sessions = []
    for session_file in context_dir.glob("*.json"):
        sessions.append(SessionInfo(
            session_id=session_file.stem,
            last_modified=datetime.fromtimestamp(
                session_file.stat().st_mtime
            ).isoformat()
        ))

    # Sort by most recent first
    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    return sessions
```

### With Message Count

```python
from src.libs.agent_memory.context_memory import load_context

class SessionInfo(BaseModel):
    session_id: str
    last_modified: str
    message_count: int

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    agent_id = "story_researcher"
    context_dir = Path(".mythline") / agent_id / "context_memory"

    if not context_dir.exists():
        return []

    sessions = []
    for session_file in context_dir.glob("*.json"):
        session_id = session_file.stem
        messages = load_context(agent_id, session_id)

        sessions.append(SessionInfo(
            session_id=session_id,
            last_modified=datetime.fromtimestamp(
                session_file.stat().st_mtime
            ).isoformat(),
            message_count=len(messages)
        ))

    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    return sessions
```

---

## Load Session

### Get Session History

```python
from typing import List

class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]

@router.get("/sessions/{session_id}", response_model=SessionHistory)
async def get_session(session_id: str):
    agent_id = "story_researcher"
    messages = load_context(agent_id, session_id)

    # Format messages
    formatted_messages = []
    for msg in messages:
        if not hasattr(msg, 'parts') or not msg.parts:
            continue

        for part in msg.parts:
            part_kind = getattr(part, 'part_kind', None)

            if part_kind == 'user-prompt':
                formatted_messages.append({
                    "role": "user",
                    "content": getattr(part, 'content', str(part))
                })
            elif part_kind == 'text':
                formatted_messages.append({
                    "role": "assistant",
                    "content": getattr(part, 'content', str(part))
                })

    return SessionHistory(
        session_id=session_id,
        messages=formatted_messages
    )
```

### Check Session Exists

```python
from fastapi import HTTPException

@router.get("/sessions/{session_id}/exists")
async def check_session_exists(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    return {"exists": session_file.exists()}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    messages = load_context(agent_id, session_id)
    return {"session_id": session_id, "messages": messages}
```

---

## Create Session

### Auto-Generate Session ID

```python
from datetime import datetime

@router.post("/sessions/create")
async def create_session():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Session will be created when first message is saved
    return {
        "session_id": session_id,
        "status": "created"
    }
```

### Create with Custom ID

```python
class CreateSessionRequest(BaseModel):
    session_id: str

@router.post("/sessions/create")
async def create_session(request: CreateSessionRequest):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{request.session_id}.json"

    if session_file.exists():
        raise HTTPException(
            status_code=409,
            detail="Session already exists"
        )

    # Initialize empty session
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text("[]")

    return {
        "session_id": request.session_id,
        "status": "created"
    }
```

---

## Delete Session

### Delete Single Session

```python
@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    session_file.unlink()

    return {
        "session_id": session_id,
        "status": "deleted"
    }
```

### Delete All Sessions

```python
@router.delete("/sessions")
async def delete_all_sessions():
    agent_id = "story_researcher"
    context_dir = Path(".mythline") / agent_id / "context_memory"

    if not context_dir.exists():
        return {"deleted": 0}

    count = 0
    for session_file in context_dir.glob("*.json"):
        session_file.unlink()
        count += 1

    return {"deleted": count}
```

---

## Session Metadata

### Get Session Info

```python
class SessionMetadata(BaseModel):
    session_id: str
    created: str
    last_modified: str
    message_count: int
    file_size: int

@router.get("/sessions/{session_id}/info", response_model=SessionMetadata)
async def get_session_info(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    stat = session_file.stat()
    messages = load_context(agent_id, session_id)

    return SessionMetadata(
        session_id=session_id,
        created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        message_count=len(messages),
        file_size=stat.st_size
    )
```

---

## Get Latest Session

### Most Recent Session

```python
from src.libs.agent_memory.context_memory import get_latest_session

@router.get("/sessions/latest")
async def get_latest():
    agent_id = "story_researcher"
    latest_session = get_latest_session(agent_id)

    if not latest_session:
        raise HTTPException(
            status_code=404,
            detail="No sessions found"
        )

    return {"session_id": latest_session}
```

---

## Complete Example

### Research Session Management

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from src.libs.agent_memory.context_memory import load_context, get_latest_session

router = APIRouter()

class SessionInfo(BaseModel):
    session_id: str
    last_modified: str
    message_count: int

class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]

@router.get("/research/sessions", response_model=List[SessionInfo])
async def list_sessions():
    agent_id = "story_researcher"
    context_dir = Path(".mythline") / agent_id / "context_memory"

    if not context_dir.exists():
        return []

    sessions = []
    for session_file in context_dir.glob("*.json"):
        session_id = session_file.stem
        messages = load_context(agent_id, session_id)

        sessions.append(SessionInfo(
            session_id=session_id,
            last_modified=datetime.fromtimestamp(
                session_file.stat().st_mtime
            ).isoformat(),
            message_count=len(messages)
        ))

    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    return sessions

@router.get("/research/sessions/{session_id}", response_model=SessionHistory)
async def get_session(session_id: str):
    agent_id = "story_researcher"
    messages = load_context(agent_id, session_id)

    formatted_messages = []
    for msg in messages:
        if not hasattr(msg, 'parts') or not msg.parts:
            continue

        for part in msg.parts:
            part_kind = getattr(part, 'part_kind', None)

            if part_kind == 'user-prompt':
                formatted_messages.append({
                    "role": "user",
                    "content": getattr(part, 'content', str(part))
                })
            elif part_kind == 'text':
                formatted_messages.append({
                    "role": "assistant",
                    "content": getattr(part, 'content', str(part))
                })

    return SessionHistory(
        session_id=session_id,
        messages=formatted_messages
    )

@router.get("/research/sessions/latest")
async def get_latest_session_id():
    agent_id = "story_researcher"
    latest = get_latest_session(agent_id)

    if not latest:
        raise HTTPException(status_code=404, detail="No sessions found")

    return {"session_id": latest}

@router.delete("/research/sessions/{session_id}")
async def delete_session(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    session_file.unlink()

    return {"session_id": session_id, "status": "deleted"}
```

---

## Session Export/Import

### Export Session

```python
@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str):
    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=session_file,
        filename=f"{session_id}.json",
        media_type='application/json'
    )
```

### Import Session

```python
from fastapi import UploadFile, File

@router.post("/sessions/import")
async def import_session(file: UploadFile = File(...)):
    content = await file.read()

    # Validate JSON
    import json
    try:
        messages = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Generate session ID from filename
    session_id = Path(file.filename).stem

    agent_id = "story_researcher"
    session_file = Path(".mythline") / agent_id / "context_memory" / f"{session_id}.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_bytes(content)

    return {"session_id": session_id, "status": "imported"}
```

---

## Best Practices

**DO:**
- Sort sessions by most recent
- Validate session IDs
- Handle missing sessions gracefully
- Use consistent session ID format
- Clean up old sessions periodically
- Provide session metadata
- Use Path for file operations

**DON'T:**
- Trust user-provided session IDs without validation
- Expose internal file paths
- Delete sessions without confirmation
- Forget to check session existence
- Hardcode agent IDs
- Store sensitive data in session IDs

---

## Related Documentation

- `router_module.md` - Endpoint organization
- `agent_integration.md` - Agent session management
- `file_operations.md` - File handling
- `../COMMON.md` - Common backend patterns
- `../../libs/agent_memory/context_memory.md` - Context memory library
