# Backend: Background Tasks

Running long operations in background with status tracking.

---

## Overview

**Use when:** Long-running operations, async task execution, progress tracking needed, non-blocking responses.

**Pattern:**
```
Start Task → Store Status → Update Progress → Complete → Retrieve Results
```

---

## Basic Background Task

### Using asyncio.create_task

```python
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
background_tasks = {}

class TaskRequest(BaseModel):
    input_data: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

@router.post("/start", response_model=TaskResponse)
async def start_task(request: TaskRequest):
    task_id = generate_task_id()

    async def run_task():
        # Long-running operation
        await process_data(request.input_data)

    background_tasks[task_id] = asyncio.create_task(run_task())

    return TaskResponse(
        task_id=task_id,
        status="started"
    )
```

---

## Task Status Tracking

### In-Memory Status Storage

```python
import uuid

task_status = {}

@router.post("/start")
async def start_task(request: TaskRequest):
    task_id = str(uuid.uuid4())

    # Initialize status
    task_status[task_id] = {
        "status": "running",
        "result": None,
        "error": None
    }

    async def run_task():
        try:
            result = await perform_operation(request.data)
            task_status[task_id] = {
                "status": "completed",
                "result": result,
                "error": None
            }
        except Exception as e:
            task_status[task_id] = {
                "status": "error",
                "result": None,
                "error": str(e)
            }

    asyncio.create_task(run_task())

    return {"task_id": task_id, "status": "started"}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status[task_id]
```

### File-Based Status Storage

```python
import json
from pathlib import Path

def save_progress(task_id: str, status: dict):
    progress_dir = Path(".mythline/tasks")
    progress_dir.mkdir(parents=True, exist_ok=True)

    progress_file = progress_dir / f"{task_id}.json"
    progress_file.write_text(json.dumps(status))

def load_progress(task_id: str) -> dict:
    progress_file = Path(f".mythline/tasks/{task_id}.json")

    if not progress_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    return json.loads(progress_file.read_text())

@router.post("/start")
async def start_task(request: TaskRequest):
    task_id = str(uuid.uuid4())

    # Save initial status
    save_progress(task_id, {
        "status": "running",
        "progress": 0,
        "message": "Starting task"
    })

    async def run_task():
        try:
            # Update progress
            save_progress(task_id, {
                "status": "running",
                "progress": 50,
                "message": "Processing data"
            })

            result = await process_data(request.data)

            # Mark complete
            save_progress(task_id, {
                "status": "completed",
                "progress": 100,
                "result": result
            })
        except Exception as e:
            save_progress(task_id, {
                "status": "error",
                "error": str(e)
            })

    asyncio.create_task(run_task())
    return {"task_id": task_id}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    return load_progress(task_id)
```

---

## Progress Tracking

### Percentage Progress

```python
async def run_long_task(task_id: str, items: list):
    total = len(items)

    for idx, item in enumerate(items):
        # Process item
        await process_item(item)

        # Update progress
        progress = int((idx + 1) / total * 100)
        save_progress(task_id, {
            "status": "running",
            "progress": progress,
            "current": idx + 1,
            "total": total
        })

    # Complete
    save_progress(task_id, {
        "status": "completed",
        "progress": 100
    })
```

### Step-Based Progress

```python
async def run_multi_step_task(task_id: str):
    steps = ["Step 1", "Step 2", "Step 3"]

    for idx, step in enumerate(steps):
        save_progress(task_id, {
            "status": "running",
            "current_step": step,
            "step_number": idx + 1,
            "total_steps": len(steps)
        })

        await execute_step(step)

    save_progress(task_id, {"status": "completed"})
```

---

## Agent Integration

### Long-Running Agent Task

```python
from src.agents.story_creator_agent.agent import StoryCreatorAgent

@router.post("/story/create")
async def create_story(request: StoryRequest):
    task_id = request.subject

    # Initialize progress
    save_progress(task_id, {
        "status": "starting",
        "message": "Initializing story creation"
    })

    # Create agent
    agent = StoryCreatorAgent(
        session_id=task_id,
        player_name=request.player
    )

    async def run_in_background():
        try:
            # Run agent
            await agent.run(subject=request.subject)

            save_progress(task_id, {
                "status": "completed",
                "message": "Story creation complete"
            })
        except Exception as e:
            save_progress(task_id, {
                "status": "error",
                "message": str(e)
            })

    asyncio.create_task(run_in_background())

    return {
        "task_id": task_id,
        "message": "Story creation started"
    }

@router.get("/story/progress/{task_id}")
async def get_progress(task_id: str):
    return load_progress(task_id)
```

---

## Complete Example

### Story Generation with Progress

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import json
from pathlib import Path
from src.agents.story_creator_agent.agent import StoryCreatorAgent

router = APIRouter()
background_tasks = {}

class StoryRequest(BaseModel):
    subject: str
    player: str

class StoryResponse(BaseModel):
    status: str
    message: str

def save_initial_progress(subject: str):
    progress_dir = Path(".mythline/story_jobs")
    progress_dir.mkdir(parents=True, exist_ok=True)

    progress_file = progress_dir / f"{subject}.json"
    progress_file.write_text(json.dumps({
        "status": "starting",
        "message": "Initializing story creation",
        "current": 0,
        "total": 0,
        "details": {},
        "timestamp": 0
    }))

@router.post("/story/create", response_model=StoryResponse)
async def create_story(request: StoryRequest):
    # Validate prerequisites
    research_path = f"output/{request.subject}/research.md"

    if not Path(research_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Research file not found at {research_path}. Please research {request.subject} first."
        )

    # Save initial progress
    save_initial_progress(request.subject)

    # Create agent
    session_id = request.subject
    story_creator = StoryCreatorAgent(
        session_id=session_id,
        player_name=request.player
    )

    # Background task
    async def run_in_background():
        try:
            await story_creator.run(subject=request.subject)
        except Exception as e:
            progress_dir = Path(".mythline/story_jobs")
            progress_file = progress_dir / f"{request.subject}.json"
            progress_file.write_text(json.dumps({
                "status": "error",
                "message": str(e),
                "current": 0,
                "total": 0,
                "details": {},
                "timestamp": 0
            }))

    # Start background task
    background_tasks[request.subject] = asyncio.create_task(run_in_background())

    return StoryResponse(
        status="started",
        message=f"Story creation started for {request.subject}. Poll /api/story/progress/{request.subject} for updates."
    )

@router.get("/story/progress/{subject}")
async def get_story_progress(subject: str):
    progress_file = Path(f".mythline/story_jobs/{subject}.json")

    if not progress_file.exists():
        raise HTTPException(status_code=404, detail="No job found")

    return json.loads(progress_file.read_text())
```

---

## Task Cleanup

### Remove Completed Tasks

```python
@router.delete("/tasks/{task_id}")
async def cleanup_task(task_id: str):
    # Remove from memory
    if task_id in background_tasks:
        task = background_tasks[task_id]
        if not task.done():
            task.cancel()
        del background_tasks[task_id]

    # Remove status file
    progress_file = Path(f".mythline/tasks/{task_id}.json")
    if progress_file.exists():
        progress_file.unlink()

    return {"status": "cleaned"}
```

### Auto-Cleanup Old Tasks

```python
import time

async def cleanup_old_tasks():
    progress_dir = Path(".mythline/tasks")
    if not progress_dir.exists():
        return

    now = time.time()
    max_age = 24 * 60 * 60  # 24 hours

    for progress_file in progress_dir.glob("*.json"):
        age = now - progress_file.stat().st_mtime
        if age > max_age:
            progress_file.unlink()
```

---

## Task Cancellation

### Cancel Running Task

```python
@router.delete("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    if task_id not in background_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = background_tasks[task_id]

    if task.done():
        return {"status": "already_completed"}

    task.cancel()
    save_progress(task_id, {"status": "cancelled"})

    return {"status": "cancelled"}
```

---

## Result Retrieval

### Get Task Result

```python
@router.get("/tasks/{task_id}/result")
async def get_result(task_id: str):
    status = load_progress(task_id)

    if status["status"] == "running":
        raise HTTPException(
            status_code=425,
            detail="Task still running"
        )

    if status["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=status["error"]
        )

    return {"result": status["result"]}
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
- Use asyncio.create_task for background operations
- Track task status persistently
- Provide progress updates
- Handle errors in background tasks
- Clean up completed tasks
- Use unique task IDs
- Validate prerequisites before starting

**DON'T:**
- Block the event loop in background tasks
- Forget error handling
- Store results indefinitely
- Use sequential processing for independent tasks
- Expose internal errors
- Forget to update progress

---

## Related Documentation

- `agent_integration.md` - Running agents in background
- `router_module.md` - Endpoint definition
- `../integration/polling_pattern.md` - Frontend polling
- `../COMMON.md` - Common backend patterns
