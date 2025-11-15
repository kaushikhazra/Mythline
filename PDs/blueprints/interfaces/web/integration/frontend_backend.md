# Integration: Frontend-Backend

Connecting React frontend to FastAPI backend.

---

## Overview

**Use when:** Setting up new features, defining API contracts, debugging integration, understanding data flow.

**Pattern:**
```
Define API Contract → Frontend Calls → Backend Processes → Response → UI Update
```

---

## API Contract

### Define Request/Response Models

**Backend (FastAPI):**
```python
from pydantic import BaseModel

class ResearchRequest(BaseModel):
    message: str
    session_id: str

class ResearchResponse(BaseModel):
    session_id: str
    response: str
```

**Frontend (JavaScript):**
```javascript
// Request
const request = {
  message: "Tell me about Shadowglen",
  session_id: "session_20240113"
}

// Expected response
const response = {
  session_id: "session_20240113",
  response: "Shadowglen is..."
}
```

---

## CORS Configuration

### Backend Setup

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Development: Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Production: Specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "https://yourdomain.com"  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## Request Flow

### GET Request Flow

**Frontend:**
```javascript
// 1. Frontend makes GET request
const response = await fetch('http://localhost:8080/api/sessions')

// 2. Parse JSON response
const data = await response.json()

// 3. Update state
setSessions(data.sessions)
```

**Backend:**
```python
# 1. Backend receives request
@router.get("/sessions")
async def list_sessions():
    # 2. Process request
    sessions = get_sessions()

    # 3. Return response
    return {"sessions": sessions}
```

### POST Request Flow

**Frontend:**
```javascript
// 1. Prepare request data
const requestData = {
  message: query,
  session_id: selectedSession
}

// 2. Send POST request
const response = await fetch('http://localhost:8080/api/research/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(requestData)
})

// 3. Parse response
const result = await response.json()

// 4. Update UI
setOutput(result.response)
```

**Backend:**
```python
# 1. Receive and validate request
@router.post("/research/run")
async def run_research(request: ResearchRequest):
    # 2. Process request
    agent = get_agent(request.session_id)
    result = await agent.run_async(request.message)

    # 3. Return response
    return ResearchResponse(
        session_id=request.session_id,
        response=result.output
    )
```

---

## Complete Integration Examples

### Research Feature

**Backend Router:**
```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class ResearchRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ResearchResponse(BaseModel):
    session_id: str
    response: str

class SessionInfo(BaseModel):
    session_id: str
    message_count: int

@router.get("/research/sessions", response_model=List[SessionInfo])
async def list_sessions():
    sessions = load_all_sessions()
    return sessions

@router.post("/research/run", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    session_id = request.session_id or generate_session_id()
    agent = get_agent(session_id)
    result = await agent.run_async(request.message)

    return ResearchResponse(
        session_id=session_id,
        response=result.output
    )
```

**Frontend Component:**
```javascript
import { useState, useEffect } from 'react'

function Research() {
  const API_BASE_URL = 'http://localhost:8080'

  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState('')
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      const res = await fetch(`${API_BASE_URL}/api/research/sessions`)
      const data = await res.json()
      setSessions(data)

      if (data.length > 0) {
        setSelectedSession(data[0].session_id)
      }
    }

    loadSessions()
  }, [])

  // Submit query
  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/research/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          session_id: selectedSession
        })
      })

      const data = await res.json()
      setResponse(data.response)
      setQuery('')
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div>
      <select
        value={selectedSession}
        onChange={(e) => setSelectedSession(e.target.value)}
      >
        {sessions.map(s => (
          <option key={s.session_id} value={s.session_id}>
            {s.session_id}
          </option>
        ))}
      </select>

      <form onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter research query..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Loading...' : 'Submit'}
        </button>
      </form>

      {response && <div>{response}</div>}
    </div>
  )
}

export default Research
```

---

## Error Handling

### Backend Error Response

```python
from fastapi import HTTPException

@router.post("/process")
async def process_data(request: DataRequest):
    if not request.data:
        raise HTTPException(
            status_code=400,
            detail="Data is required"
        )

    try:
        result = await process(request.data)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Frontend Error Handling

```javascript
const handleSubmit = async () => {
  setError(null)

  try {
    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Request failed')
    }

    const result = await response.json()
    setResult(result)
  } catch (err) {
    setError(err.message)
  }
}

// Display error
{error && <div className="error">{error}</div>}
```

---

## Data Transformation

### Backend to Frontend

**Backend returns:**
```python
return {
    "created_at": datetime.now().isoformat(),
    "user_count": 42,
    "is_active": True
}
```

**Frontend receives:**
```javascript
const data = await response.json()

// Transform data
const displayData = {
  createdAt: new Date(data.created_at).toLocaleDateString(),
  userCount: data.user_count,
  isActive: data.is_active
}
```

### Frontend to Backend

**Frontend sends:**
```javascript
const formData = {
  userName: 'John Doe',
  emailAddress: 'john@example.com',
  isSubscribed: true
}

await fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_name: formData.userName,           // camelCase → snake_case
    email_address: formData.emailAddress,
    is_subscribed: formData.isSubscribed
  })
})
```

**Backend receives:**
```python
class UserRequest(BaseModel):
    user_name: str
    email_address: str
    is_subscribed: bool
```

---

## Environment Configuration

### Development Setup

**Frontend (.env):**
```env
VITE_API_BASE_URL=http://localhost:8080
```

**Backend (.env):**
```env
API_HOST=0.0.0.0
API_PORT=8080
CORS_ORIGINS=http://localhost:5173
```

### Production Setup

**Frontend:**
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.production.com'
```

**Backend:**
```python
import os

origins = os.getenv('CORS_ORIGINS', '').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins)
```

---

## Debugging Integration

### Frontend Debugging

```javascript
const submitData = async () => {
  // Log request
  console.log('Request:', {
    url: `${API_BASE_URL}/api/endpoint`,
    method: 'POST',
    body: data
  })

  try {
    const response = await fetch(`${API_BASE_URL}/api/endpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })

    // Log response status
    console.log('Response status:', response.status)

    const result = await response.json()

    // Log response data
    console.log('Response data:', result)
  } catch (error) {
    console.error('Error:', error)
  }
}
```

### Backend Debugging

```python
@router.post("/endpoint")
async def endpoint(request: DataRequest):
    # Log request
    print(f"Received request: {request.model_dump()}")

    try:
        result = await process(request.data)

        # Log response
        print(f"Sending response: {result}")

        return {"result": result}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
```

---

## Common Integration Patterns

### Load Data on Mount

```javascript
useEffect(() => {
  const fetchData = async () => {
    const response = await fetch(`${API_BASE_URL}/api/data`)
    const data = await response.json()
    setData(data)
  }

  fetchData()
}, [])
```

### Submit Form

```javascript
const handleSubmit = async (event) => {
  event.preventDefault()

  const response = await fetch(`${API_BASE_URL}/api/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  })

  const result = await response.json()
  onSuccess(result)
}
```

### Poll for Status

```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const status = await response.json()

    if (status.status === 'completed') {
      clearInterval(interval)
      setResult(status.result)
    }
  }, 2000)

  return () => clearInterval(interval)
}, [taskId])
```

---

## Best Practices

**DO:**
- Use consistent naming conventions
- Handle all error cases
- Validate data on both sides
- Use TypeScript/Pydantic for type safety
- Configure CORS properly
- Use environment variables
- Log requests/responses in development

**DON'T:**
- Hardcode API URLs
- Expose sensitive data
- Trust client data without validation
- Forget error handling
- Use different data formats
- Skip CORS configuration
- Commit API keys

---

## Related Documentation

- `polling_pattern.md` - Polling implementation
- `../frontend/api_communication.md` - Frontend API calls
- `../backend/router_module.md` - Backend endpoints
- `../COMMON.md` - Common patterns
