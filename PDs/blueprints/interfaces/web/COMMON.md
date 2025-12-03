# Web Interface Common Patterns

Shared patterns and conventions used across all web interface components.

---

## Technology Stack

### Frontend

**React 18**
- Functional components with hooks
- No class components
- JSX syntax

**Vite 6**
- Fast development server
- Hot module replacement
- Build optimization

**JavaScript**
- No TypeScript
- ES6+ features
- Module imports

**Styling**
- Plain CSS
- CSS Modules (optional)
- Inline styles for dynamic values

### Backend

**FastAPI**
- Modern Python web framework
- Automatic API documentation
- Pydantic integration

**Uvicorn**
- ASGI server
- Hot reload in development
- Production ready

**Pydantic AI**
- Agent framework
- Type-safe responses
- Streaming support

---

## Project Structure

### Standard Web Layout

```
src/ui/web/
├── frontend/
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Research.jsx
│   │   │   └── StoryGenerator.jsx
│   │   ├── components/ (optional)
│   │   │   └── Header.jsx
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env (optional)
└── backend/
    ├── api/
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── research.py
    │   │   └── story_generator.py
    │   ├── __init__.py
    │   └── main.py
    ├── requirements.txt
    └── .env
```

### File Organization Conventions

**Frontend:**
- `pages/` - Full page components
- `components/` - Reusable UI components
- `App.jsx` - Main app with routing
- `main.jsx` - Entry point

**Backend:**
- `api/routers/` - Route modules
- `api/main.py` - FastAPI app
- `requirements.txt` - Python dependencies

---

## Development Setup

### Frontend Setup

**Install dependencies:**
```bash
cd src/ui/web/frontend
npm install
```

**Development server:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
```

### Backend Setup

**Install dependencies:**
```bash
cd src/ui/web/backend
pip install -r requirements.txt
```

**Development server:**
```bash
uvicorn api.main:app --reload --port 8080
```

**Production server:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

---

## Environment Configuration

### Frontend Environment

**File:** `frontend/.env` (optional)

```env
VITE_API_BASE_URL=http://localhost:8080
```

**Access in code:**
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
```

### Backend Environment

**File:** `backend/.env`

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Agent Configuration
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=openai/gpt-4o

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Access in code:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
API_PORT = int(os.getenv('API_PORT', 8080))
```

---

## Common Dependencies

### Frontend Dependencies

**package.json:**
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.22.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^6.0.0"
  }
}
```

### Backend Dependencies

**requirements.txt:**
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
pydantic-ai>=0.0.14
python-dotenv>=1.0.0
```

---

## Import Patterns

### Frontend Imports

**React imports:**
```javascript
import { useState, useEffect } from 'react'
```

**Router imports:**
```javascript
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
```

**Component imports:**
```javascript
import Research from './pages/Research'
import StoryGenerator from './pages/StoryGenerator'
```

### Backend Imports

**FastAPI imports:**
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
```

**Agent imports:**
```python
from src.agents.story_research_agent import StoryResearchAgent
from src.agents.story_creator_agent import StoryCreatorAgent
```

**Utility imports:**
```python
from src.libs.filesystem.file_operations import read_file, write_file
from src.libs.agent_memory.context_memory import load_context
```

---

## API Communication Patterns

### Frontend API Calls

**GET request:**
```javascript
const response = await fetch(`${API_BASE_URL}/api/endpoint`)
if (!response.ok) {
  throw new Error(`Error: ${response.statusText}`)
}
const data = await response.json()
```

**POST request:**
```javascript
const response = await fetch(`${API_BASE_URL}/api/endpoint`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ key: 'value' })
})
const data = await response.json()
```

**Error handling:**
```javascript
try {
  const data = await fetchData()
  setData(data)
} catch (error) {
  console.error('Error:', error)
  setError(error.message)
}
```

### Backend Response Patterns

**Success response:**
```python
return {"status": "success", "data": result}
```

**Error response:**
```python
raise HTTPException(status_code=404, detail="Resource not found")
```

**Custom response:**
```python
from fastapi.responses import JSONResponse
return JSONResponse(content={"key": "value"}, status_code=200)
```

---

## State Management Patterns

### React Hooks

**useState:**
```javascript
const [value, setValue] = useState(initialValue)
```

**useEffect:**
```javascript
useEffect(() => {
  // Side effect
  return () => {
    // Cleanup
  }
}, [dependencies])
```

**Common state patterns:**
```javascript
// Loading state
const [isLoading, setIsLoading] = useState(false)

// Error state
const [error, setError] = useState(null)

// Data state
const [data, setData] = useState(null)

// Form state
const [formData, setFormData] = useState({ field: '' })
```

---

## Error Handling Patterns

### Frontend Error Handling

**Try-catch pattern:**
```javascript
const handleSubmit = async () => {
  setError(null)
  setIsLoading(true)

  try {
    const result = await apiCall()
    setData(result)
  } catch (err) {
    setError(err.message)
  } finally {
    setIsLoading(false)
  }
}
```

**Error display:**
```javascript
{error && <div className="error">{error}</div>}
```

### Backend Error Handling

**HTTPException pattern:**
```python
if not resource_exists:
    raise HTTPException(status_code=404, detail="Resource not found")
```

**Try-except pattern:**
```python
try:
    result = agent.run(prompt)
    return {"output": result.output}
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Routing Patterns

### Frontend Routing

**React Router setup:**
```javascript
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/research">Research</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/research" element={<Research />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### Backend Routing

**Router organization:**
```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import research, story_generator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(story_generator.router, prefix="/api/story", tags=["story"])
```

**Router module:**
```python
# api/routers/research.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/sessions")
async def get_sessions():
    return {"sessions": []}

@router.post("/query")
async def submit_query(request: QueryRequest):
    return {"result": "data"}
```

---

## CORS Configuration

### Backend CORS Setup

**Standard CORS:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Production CORS:**
```python
import os

origins = os.getenv('CORS_ORIGINS', '').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## File Upload/Download Patterns

### Frontend File Upload

**File input:**
```javascript
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData
  })
}
```

### Backend File Handling

**File upload:**
```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename}
```

**File download:**
```python
from fastapi.responses import FileResponse

@router.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(path=f"path/to/{filename}", filename=filename)
```

---

## Background Task Patterns

### Backend Background Tasks

**Task tracking:**
```python
task_status = {}

@router.post("/start")
async def start_task(background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task_status[task_id] = {"status": "running", "result": None}
    background_tasks.add_task(run_task, task_id)
    return {"task_id": task_id}

def run_task(task_id: str):
    try:
        result = perform_operation()
        task_status[task_id] = {"status": "completed", "result": result}
    except Exception as e:
        task_status[task_id] = {"status": "error", "error": str(e)}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    return task_status.get(task_id, {"status": "not_found"})
```

### Frontend Polling

**Status polling:**
```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const status = await response.json()

    if (status.status === 'completed') {
      setResult(status.result)
      clearInterval(interval)
    } else if (status.status === 'error') {
      setError(status.error)
      clearInterval(interval)
    }
  }, 2000)

  return () => clearInterval(interval)
}, [taskId])
```

---

## Request/Response Models

### Pydantic Models

**Request model:**
```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    prompt: str
    session_id: str

class StoryRequest(BaseModel):
    subject: str
    session_id: str
```

**Response model:**
```python
class QueryResponse(BaseModel):
    output: str
    session_id: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
```

**Usage:**
```python
@router.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    result = agent.run(request.prompt)
    return QueryResponse(output=result.output, session_id=request.session_id)
```

---

## Common Pitfalls

### Frontend Pitfalls

**Missing dependency array:**
```javascript
// Wrong - infinite loop
useEffect(() => {
  fetchData()
})

// Correct
useEffect(() => {
  fetchData()
}, [])
```

**Not handling async errors:**
```javascript
// Wrong
const fetchData = async () => {
  const data = await fetch(url)  // Might throw
}

// Correct
const fetchData = async () => {
  try {
    const data = await fetch(url)
  } catch (error) {
    setError(error.message)
  }
}
```

### Backend Pitfalls

**Missing await:**
```python
# Wrong
result = agent.run_sync(prompt)  # Blocks event loop

# Correct
result = await agent.run(prompt)
```

**Not handling CORS:**
```python
# Must configure CORS middleware for cross-origin requests
app.add_middleware(CORSMiddleware, ...)
```

---

## Performance Considerations

### Frontend Optimization

**Avoid unnecessary re-renders:**
```javascript
// Use useMemo for expensive calculations
const expensiveValue = useMemo(() => calculate(data), [data])

// Use useCallback for handlers
const handleClick = useCallback(() => {
  doSomething()
}, [dependency])
```

**Debounce API calls:**
```javascript
useEffect(() => {
  const timer = setTimeout(() => {
    searchAPI(query)
  }, 500)
  return () => clearTimeout(timer)
}, [query])
```

### Backend Optimization

**Use background tasks:**
```python
# Don't block the response
background_tasks.add_task(long_operation)
return {"status": "started"}
```

**Cache expensive operations:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_operation(param):
    return result
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Related Documentation

- `INDEX.md` - Master web interface index (this directory)
- `frontend/` - Frontend pattern blueprints
- `backend/` - Backend pattern blueprints
- `integration/` - Integration pattern blueprints
- `../../libs/` - Library blueprints
- `../interface_cli.md` - CLI interface patterns
