# Integration: Polling Pattern

Polling for background task status and results.

---

## Overview

**Use when:** Long-running tasks, progress tracking, async operations, real-time updates (without WebSocket).

**Pattern:**
```
Start Task → Poll Status → Check Progress → Complete → Fetch Results
```

---

## Basic Polling

### Frontend Polling Loop

```javascript
import { useState, useEffect } from 'react'

function PollingComponent() {
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
      const data = await response.json()

      setStatus(data.status)

      if (data.status === 'completed' || data.status === 'error') {
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [taskId])

  return <div>Status: {status}</div>
}
```

### Backend Status Endpoint

```python
from fastapi import APIRouter, HTTPException

router = APIRouter()
task_status = {}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status[task_id]
```

---

## Complete Workflow

### Start Task

**Frontend:**
```javascript
const startTask = async () => {
  const response = await fetch(`${API_BASE_URL}/api/task/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: 'input' })
  })

  const result = await response.json()
  setTaskId(result.task_id)
}
```

**Backend:**
```python
import uuid
import asyncio

@router.post("/task/start")
async def start_task(request: TaskRequest):
    task_id = str(uuid.uuid4())

    task_status[task_id] = {
        "status": "running",
        "result": None
    }

    async def run_task():
        try:
            result = await perform_long_operation(request.data)
            task_status[task_id] = {
                "status": "completed",
                "result": result
            }
        except Exception as e:
            task_status[task_id] = {
                "status": "error",
                "error": str(e)
            }

    asyncio.create_task(run_task())

    return {"task_id": task_id}
```

### Poll Status

**Frontend:**
```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/task/status/${taskId}`)
      const data = await response.json()

      setStatus(data.status)

      if (data.status === 'completed') {
        setResult(data.result)
        clearInterval(interval)
      } else if (data.status === 'error') {
        setError(data.error)
        clearInterval(interval)
      }
    } catch (err) {
      setError('Failed to check status')
      clearInterval(interval)
    }
  }, 2000)

  return () => clearInterval(interval)
}, [taskId])
```

---

## Progress Tracking

### With Progress Percentage

**Backend:**
```python
@router.post("/task/start")
async def start_task(request: TaskRequest):
    task_id = str(uuid.uuid4())

    task_status[task_id] = {
        "status": "running",
        "progress": 0
    }

    async def run_task():
        total_steps = 10

        for step in range(total_steps):
            # Do work
            await process_step(step)

            # Update progress
            progress = int((step + 1) / total_steps * 100)
            task_status[task_id] = {
                "status": "running",
                "progress": progress
            }

        task_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "result": "Done"
        }

    asyncio.create_task(run_task())
    return {"task_id": task_id}
```

**Frontend:**
```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const data = await response.json()

    setProgress(data.progress)
    setStatus(data.status)

    if (data.status === 'completed') {
      clearInterval(interval)
    }
  }, 1000)

  return () => clearInterval(interval)
}, [taskId])

// Display progress bar
<progress value={progress} max="100">{progress}%</progress>
```

### With Step Messages

**Backend:**
```python
async def run_task():
    steps = [
        "Loading data",
        "Processing data",
        "Generating output",
        "Finalizing"
    ]

    for idx, step_message in enumerate(steps):
        task_status[task_id] = {
            "status": "running",
            "current_step": step_message,
            "step": idx + 1,
            "total_steps": len(steps)
        }

        await execute_step(idx)

    task_status[task_id] = {
        "status": "completed",
        "result": "Success"
    }
```

**Frontend:**
```javascript
{status === 'running' && statusData.current_step && (
  <div>
    <p>{statusData.current_step}</p>
    <p>Step {statusData.step} of {statusData.total_steps}</p>
  </div>
)}
```

---

## Complete Example: Story Generation

### Backend

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

def save_progress(subject: str, status: dict):
    progress_dir = Path(".mythline/story_jobs")
    progress_dir.mkdir(parents=True, exist_ok=True)
    progress_file = progress_dir / f"{subject}.json"
    progress_file.write_text(json.dumps(status))

@router.post("/story/create")
async def create_story(request: StoryRequest):
    # Validate prerequisite
    if not Path(f"output/{request.subject}/research.md").exists():
        raise HTTPException(
            status_code=400,
            detail="Research file not found"
        )

    # Initialize progress
    save_progress(request.subject, {
        "status": "starting",
        "message": "Initializing story creation",
        "progress": 0
    })

    # Create and run agent in background
    async def run_agent():
        try:
            agent = StoryCreatorAgent(
                session_id=request.subject,
                player_name=request.player
            )

            await agent.run(subject=request.subject)

            save_progress(request.subject, {
                "status": "completed",
                "message": "Story creation complete",
                "progress": 100
            })
        except Exception as e:
            save_progress(request.subject, {
                "status": "error",
                "message": str(e),
                "progress": 0
            })

    background_tasks[request.subject] = asyncio.create_task(run_agent())

    return {
        "task_id": request.subject,
        "message": "Story creation started"
    }

@router.get("/story/progress/{subject}")
async def get_progress(subject: str):
    progress_file = Path(f".mythline/story_jobs/{subject}.json")

    if not progress_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    return json.loads(progress_file.read_text())
```

### Frontend

```javascript
import { useState, useEffect } from 'react'

function StoryGenerator() {
  const API_BASE_URL = 'http://localhost:8080'

  const [subject, setSubject] = useState('')
  const [player, setPlayer] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState('')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)

  const startGeneration = async () => {
    setError(null)
    setTaskId(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/story/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, player })
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail)
      }

      const data = await response.json()
      setTaskId(data.task_id)
      setStatus('running')
    } catch (err) {
      setError(err.message)
    }
  }

  // Poll for progress
  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/story/progress/${taskId}`
        )
        const data = await response.json()

        setStatus(data.status)
        setMessage(data.message)
        setProgress(data.progress || 0)

        if (data.status === 'completed') {
          clearInterval(interval)
        } else if (data.status === 'error') {
          setError(data.message)
          clearInterval(interval)
        }
      } catch (err) {
        setError('Failed to check progress')
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [taskId])

  return (
    <div>
      <h1>Story Generator</h1>

      {!taskId && (
        <form onSubmit={(e) => { e.preventDefault(); startGeneration(); }}>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject"
          />
          <input
            value={player}
            onChange={(e) => setPlayer(e.target.value)}
            placeholder="Player name"
          />
          <button type="submit">Generate</button>
        </form>
      )}

      {error && <div className="error">{error}</div>}

      {status && (
        <div>
          <p>Status: {status}</p>
          <p>{message}</p>
          {status === 'running' && (
            <>
              <progress value={progress} max="100" />
              <p>{progress}%</p>
            </>
          )}
        </div>
      )}

      {status === 'completed' && (
        <div>Story generation complete!</div>
      )}
    </div>
  )
}

export default StoryGenerator
```

---

## Polling Optimization

### Adaptive Polling Interval

```javascript
useEffect(() => {
  if (!taskId) return

  let interval = 1000 // Start with 1 second
  let attempts = 0

  const poll = async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const data = await response.json()

    setStatus(data.status)

    if (data.status === 'completed' || data.status === 'error') {
      return // Stop polling
    }

    attempts++

    // Gradually increase interval
    if (attempts > 10) interval = 2000
    if (attempts > 30) interval = 5000

    setTimeout(poll, interval)
  }

  poll()
}, [taskId])
```

### Exponential Backoff

```javascript
useEffect(() => {
  if (!taskId) return

  let attempt = 0
  const maxInterval = 10000 // Max 10 seconds

  const poll = async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const data = await response.json()

    setStatus(data.status)

    if (data.status === 'completed' || data.status === 'error') {
      return
    }

    attempt++
    const interval = Math.min(1000 * Math.pow(2, attempt), maxInterval)
    setTimeout(poll, interval)
  }

  poll()
}, [taskId])
```

---

## Error Handling

### Frontend Error Handling

```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      if (data.status === 'error') {
        setError(data.error || 'Task failed')
        clearInterval(interval)
      } else if (data.status === 'completed') {
        setResult(data.result)
        clearInterval(interval)
      }
    } catch (err) {
      setError('Network error')
      clearInterval(interval)
    }
  }, 2000)

  return () => clearInterval(interval)
}, [taskId])
```

---

## Cancellation

### Cancel Polling

```javascript
const [shouldPoll, setShouldPoll] = useState(true)

useEffect(() => {
  if (!taskId || !shouldPoll) return

  const interval = setInterval(async () => {
    // Poll status
  }, 2000)

  return () => clearInterval(interval)
}, [taskId, shouldPoll])

// Cancel polling
<button onClick={() => setShouldPoll(false)}>Cancel</button>
```

### Cancel Backend Task

**Frontend:**
```javascript
const cancelTask = async () => {
  await fetch(`${API_BASE_URL}/api/task/${taskId}/cancel`, {
    method: 'DELETE'
  })
  setShouldPoll(false)
}
```

**Backend:**
```python
@router.delete("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    if task_id in background_tasks:
        background_tasks[task_id].cancel()
        task_status[task_id] = {"status": "cancelled"}

    return {"status": "cancelled"}
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
- Clean up intervals in useEffect
- Handle network errors
- Show progress to user
- Use reasonable poll intervals (1-5 seconds)
- Stop polling when complete
- Validate task completion
- Provide cancel option for long tasks

**DON'T:**
- Poll too frequently (< 500ms)
- Poll indefinitely
- Forget to clear intervals
- Ignore error status
- Poll without error handling
- Start multiple poll intervals for same task

---

## Related Documentation

- `frontend_backend.md` - API integration
- `../frontend/api_communication.md` - API calls
- `../backend/background_tasks.md` - Background tasks
- `../COMMON.md` - Common patterns
