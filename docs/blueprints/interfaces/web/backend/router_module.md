# Backend: Router Module

FastAPI router organization and endpoint definition.

---

## Overview

**Use when:** Creating API endpoints, organizing routes, defining API structure, RESTful design.

**Pattern:**
```
Create Router → Define Endpoints → Request Models → Response Models → Error Handling
```

---

## Basic Router Setup

### Creating a Router

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello World"}
```

### Organizing Routes

```python
# routers/research.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ResearchRequest(BaseModel):
    message: str
    session_id: str

class ResearchResponse(BaseModel):
    session_id: str
    response: str

@router.post("/research/run", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    # Process request
    return ResearchResponse(
        session_id=request.session_id,
        response="Research complete"
    )
```

### Including in Main App

```python
# main.py
from fastapi import FastAPI
from routers import research, story

app = FastAPI()

app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(story.router, prefix="/api", tags=["story"])
```

---

## HTTP Methods

### GET Request

```python
@router.get("/items")
async def list_items():
    return {"items": []}

@router.get("/items/{item_id}")
async def get_item(item_id: str):
    return {"item_id": item_id}
```

### POST Request

```python
from pydantic import BaseModel

class CreateItemRequest(BaseModel):
    name: str
    description: str

@router.post("/items")
async def create_item(request: CreateItemRequest):
    return {"created": request.name}
```

### PUT Request

```python
@router.put("/items/{item_id}")
async def update_item(item_id: str, request: CreateItemRequest):
    return {"updated": item_id}
```

### DELETE Request

```python
@router.delete("/items/{item_id}")
async def delete_item(item_id: str):
    return {"deleted": item_id}
```

---

## Path Parameters

### Single Parameter

```python
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    return {"user_id": user_id}
```

### Type Hints

```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):  # Automatically validated
    return {"user_id": user_id}
```

### Multiple Parameters

```python
@router.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: str, post_id: str):
    return {"user_id": user_id, "post_id": post_id}
```

---

## Query Parameters

### Optional Parameters

```python
from typing import Optional

@router.get("/items")
async def list_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

@router.get("/search")
async def search(query: str, filter: Optional[str] = None):
    return {"query": query, "filter": filter}
```

### Required Parameters

```python
@router.get("/search")
async def search(query: str):  # Required (no default value)
    return {"query": query}
```

---

## Request Models

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional

class UserRequest(BaseModel):
    username: str
    email: str
    age: Optional[int] = None

@router.post("/users")
async def create_user(user: UserRequest):
    return {"username": user.username, "email": user.email}
```

### Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class UserRequest(BaseModel):
    username: str
    address: Address

@router.post("/users")
async def create_user(user: UserRequest):
    return {
        "username": user.username,
        "city": user.address.city
    }
```

### List Fields

```python
from typing import List

class BatchRequest(BaseModel):
    items: List[str]

@router.post("/batch")
async def process_batch(request: BatchRequest):
    return {"count": len(request.items)}
```

---

## Response Models

### Using response_model

```python
class UserResponse(BaseModel):
    user_id: str
    username: str
    # Password excluded from response

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    return UserResponse(user_id=user_id, username="john_doe")
```

### List Responses

```python
from typing import List

@router.get("/users", response_model=List[UserResponse])
async def list_users():
    return [
        UserResponse(user_id="1", username="user1"),
        UserResponse(user_id="2", username="user2")
    ]
```

---

## Error Handling

### HTTPException

```python
from fastapi import HTTPException

@router.get("/items/{item_id}")
async def get_item(item_id: str):
    if not item_exists(item_id):
        raise HTTPException(status_code=404, detail="Item not found")

    return {"item_id": item_id}
```

### Custom Error Messages

```python
@router.post("/items")
async def create_item(request: CreateItemRequest):
    if not request.name:
        raise HTTPException(
            status_code=400,
            detail="Item name is required"
        )

    return {"created": request.name}
```

### Try-Except Pattern

```python
@router.post("/process")
async def process_data(request: DataRequest):
    try:
        result = await process(request.data)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Router Prefixes and Tags

### Router with Prefix

```python
# main.py
app.include_router(
    research.router,
    prefix="/api/research",
    tags=["research"]
)

# All routes in research.router now have /api/research prefix
# /run becomes /api/research/run
```

### Multiple Tags

```python
app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["admin", "management"]
)
```

---

## Complete Router Example

### Research Router

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from src.agents.story_research_agent.agent import StoryResearcher
from src.libs.agent_memory.context_memory import load_context

router = APIRouter()
agents = {}

# Request/Response models
class ResearchRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ResearchResponse(BaseModel):
    session_id: str
    response: str

class SessionInfo(BaseModel):
    session_id: str
    last_modified: str
    message_count: int

class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]

# Helper function
def get_or_create_agent(session_id: str) -> StoryResearcher:
    if session_id not in agents:
        agents[session_id] = StoryResearcher(session_id)
    return agents[session_id]

# Endpoints
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

@router.get("/sessions/{session_id}", response_model=SessionHistory)
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

@router.post("/run", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    if request.session_id:
        session_id = request.session_id
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    agent = get_or_create_agent(session_id)
    response = await agent.run_async(request.message)

    return ResearchResponse(
        session_id=session_id,
        response=response.output
    )
```

---

## Router Organization Patterns

### Feature-Based Organization

```
routers/
├── research.py     # Research endpoints
├── story.py        # Story generation endpoints
├── users.py        # User management
└── admin.py        # Admin operations
```

### Entity-Based Organization

```
routers/
├── sessions.py     # Session CRUD
├── messages.py     # Message operations
└── files.py        # File operations
```

---

## Dependency Injection

### Shared Dependencies

```python
from fastapi import Depends

def get_current_user(token: str):
    # Validate token
    return {"user_id": "123"}

@router.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user}
```

### Database Sessions

```python
def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

@router.get("/items")
async def list_items(db = Depends(get_db)):
    return db.query_items()
```

---

## Status Codes

### Explicit Status Codes

```python
from fastapi import status

@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(request: CreateItemRequest):
    return {"created": request.name}

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    # Delete item
    return
```

### Conditional Status Codes

```python
from fastapi.responses import JSONResponse

@router.post("/items")
async def create_item(request: CreateItemRequest):
    if item_exists(request.name):
        return JSONResponse(
            status_code=409,
            content={"detail": "Item already exists"}
        )

    return {"created": request.name}
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Best Practices

**DO:**
- Use Pydantic models for request/response validation
- Use async def for endpoints
- Use response_model for documentation
- Organize routes logically
- Use appropriate HTTP methods
- Handle errors with HTTPException
- Use type hints

**DON'T:**
- Return unvalidated dictionaries
- Forget error handling
- Mix concerns in one router
- Use blocking I/O without async
- Expose internal errors to clients
- Hardcode values
- Use generic error messages

---

## Related Documentation

- `agent_integration.md` - Integrating agents with routes
- `background_tasks.md` - Long-running operations
- `file_operations.md` - File handling in routes
- `session_management.md` - Session endpoints
- `../COMMON.md` - Common backend patterns
