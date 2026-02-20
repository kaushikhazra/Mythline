# Web Interface Blueprint - Index

This is the master index for web interface patterns in Pydantic AI projects. Use this guide to choose the right web pattern for your needs.

---

## Quick Pattern Selector

**I need to...**

- **Create a new page component** → [`frontend/page_component.md`](#page-component)
- **Make API calls from React** → [`frontend/api_communication.md`](#api-communication)
- **Manage component state** → [`frontend/state_management.md`](#state-management)
- **Build forms with validation** → [`frontend/form_handling.md`](#form-handling)
- **Create API endpoints** → [`backend/router_module.md`](#router-module)
- **Integrate agents with API** → [`backend/agent_integration.md`](#agent-integration)
- **Run background tasks** → [`backend/background_tasks.md`](#background-tasks)
- **Handle file operations** → [`backend/file_operations.md`](#file-operations)
- **Manage sessions** → [`backend/session_management.md`](#session-management)
- **Connect frontend to backend** → [`integration/frontend_backend.md`](#frontend-backend-integration)
- **Implement polling for updates** → [`integration/polling_pattern.md`](#polling-pattern)

---

## Pattern Overview

### Common Components
**File:** `COMMON.md`

Shared components used across all web patterns:
- Technology stack (React, Vite, FastAPI)
- Project structure
- Development setup
- Environment configuration
- Common dependencies
- Cross-cutting patterns

**Read this first** to understand foundational components.

---

### Frontend Patterns

#### Page Component
**File:** `frontend/page_component.md`

React page component structure and organization.

**Pattern:**
```
Component Definition → State Setup → API Integration → Render UI
```

**Key Features:**
- Functional components with hooks
- Component organization
- Props and state management
- Event handlers
- Conditional rendering

**Use when:**
- Creating new pages
- Building reusable components
- Structuring UI logic

**Examples in codebase:**
- `src/ui/web/frontend/src/pages/Research.jsx`
- `src/ui/web/frontend/src/pages/StoryGenerator.jsx`

---

#### API Communication
**File:** `frontend/api_communication.md`

Making API calls from React components.

**Pattern:**
```
Define API Function → Call in useEffect/Handler → Update State → Handle Errors
```

**Key Features:**
- Fetch API usage
- Async/await patterns
- Error handling
- Loading states
- Response parsing

**Use when:**
- Fetching data from backend
- Submitting forms
- Polling for updates
- File uploads/downloads

**Examples in codebase:**
- Research page API calls
- Story generator polling

---

#### State Management
**File:** `frontend/state_management.md`

Managing component state with React hooks.

**Pattern:**
```
Initialize State → Update via Handlers → Trigger Re-renders → Side Effects
```

**Key Features:**
- useState for local state
- useEffect for side effects
- Derived state patterns
- State initialization
- State updates

**Use when:**
- Managing form data
- Tracking UI state
- Handling async operations
- Component lifecycle

**Examples in codebase:**
- Research page session state
- Story generator progress tracking

---

#### Form Handling
**File:** `frontend/form_handling.md`

Building forms with validation and submission.

**Pattern:**
```
Form State → Validation → Submission → Error Handling → Success
```

**Key Features:**
- Controlled inputs
- Form validation
- Submit handlers
- Error display
- Success feedback

**Use when:**
- User input forms
- Data submission
- Multi-step forms
- File uploads

**Examples in codebase:**
- Research query form
- Story generator form

---

### Backend Patterns

#### Router Module
**File:** `backend/router_module.md`

FastAPI router organization and endpoint definition.

**Pattern:**
```
Create Router → Define Endpoints → Request Models → Response Models → Error Handling
```

**Key Features:**
- APIRouter usage
- Route definitions
- HTTP methods (GET, POST, PUT, DELETE)
- Path parameters
- Query parameters

**Use when:**
- Creating API endpoints
- Organizing routes
- Defining API structure
- RESTful design

**Examples in codebase:**
- `src/ui/web/backend/api/routers/research.py`
- `src/ui/web/backend/api/routers/story_generator.py`

---

#### Agent Integration
**File:** `backend/agent_integration.md`

Integrating Pydantic AI agents with FastAPI endpoints.

**Pattern:**
```
Import Agent → Initialize Agent → Run Agent → Return Response → Handle Errors
```

**Key Features:**
- Agent instantiation
- Session management
- Async agent calls
- Response formatting
- Error handling

**Use when:**
- Connecting agents to API
- Running agent operations
- Managing agent state
- Streaming responses

**Examples in codebase:**
- Research agent integration
- Story creator integration

---

#### Background Tasks
**File:** `backend/background_tasks.md`

Running long operations in background with status tracking.

**Pattern:**
```
Start Task → Store Status → Update Progress → Complete → Retrieve Results
```

**Key Features:**
- BackgroundTasks usage
- Task status tracking
- Progress updates
- Result storage
- Error handling

**Use when:**
- Long-running operations
- Async task execution
- Progress tracking needed
- Non-blocking responses

**Examples in codebase:**
- Story generation task
- Shot generation task

---

#### File Operations
**File:** `backend/file_operations.md`

File upload, download, and management in FastAPI.

**Pattern:**
```
Upload File → Validate → Process → Store → Return Response
```

**Key Features:**
- File upload handling
- File download responses
- Directory operations
- Path validation
- Error handling

**Use when:**
- File uploads
- File downloads
- Directory listing
- File validation

**Examples in codebase:**
- Session file retrieval
- Story file downloads

---

#### Session Management
**File:** `backend/session_management.md`

Managing user sessions and session-based data.

**Pattern:**
```
List Sessions → Load Session → Create Session → Delete Session
```

**Key Features:**
- Session listing
- Session loading
- Session creation
- Session cleanup
- Path handling

**Use when:**
- Multi-session support
- Session persistence
- Session switching
- Session cleanup

**Examples in codebase:**
- Research session management
- Story generator sessions

---

### Integration Patterns

#### Frontend-Backend Integration
**File:** `integration/frontend_backend.md`

Connecting React frontend to FastAPI backend.

**Pattern:**
```
Define API Contract → Frontend Calls → Backend Processes → Response → UI Update
```

**Key Features:**
- API endpoint mapping
- CORS configuration
- Request/response flow
- Error propagation
- Data transformation

**Use when:**
- Setting up new features
- Defining API contracts
- Debugging integration
- Understanding data flow

**Examples in codebase:**
- Research page integration
- Story generator integration

---

#### Polling Pattern
**File:** `integration/polling_pattern.md`

Polling for background task status and results.

**Pattern:**
```
Start Task → Poll Status → Check Progress → Complete → Fetch Results
```

**Key Features:**
- Polling intervals
- Status checking
- Progress updates
- Completion detection
- Error handling

**Use when:**
- Long-running tasks
- Progress tracking
- Async operations
- Real-time updates (without WebSocket)

**Examples in codebase:**
- Story generation polling
- Shot generation status

---

## Decision Tree

```
What do you need?

├─ Frontend Development
│  ├─ New page or component? → page_component.md
│  ├─ API communication? → api_communication.md
│  ├─ State management? → state_management.md
│  └─ Form handling? → form_handling.md
│
├─ Backend Development
│  ├─ API endpoints? → router_module.md
│  ├─ Agent integration? → agent_integration.md
│  ├─ Background tasks? → background_tasks.md
│  ├─ File operations? → file_operations.md
│  └─ Session management? → session_management.md
│
└─ Integration
   ├─ Connect frontend to backend? → frontend_backend.md
   └─ Implement polling? → polling_pattern.md
```

---

## Pattern Comparison

| Pattern | Layer | Complexity | State | Async | Use Case |
|---------|-------|------------|-------|-------|----------|
| **Page Component** | Frontend | Medium | Local | No | UI pages |
| **API Communication** | Frontend | Medium | Local | Yes | Data fetching |
| **State Management** | Frontend | Low | Local | No | UI state |
| **Form Handling** | Frontend | Medium | Local | Yes | User input |
| **Router Module** | Backend | Low | Stateless | No | API structure |
| **Agent Integration** | Backend | High | Stateful | Yes | AI operations |
| **Background Tasks** | Backend | High | Stateful | Yes | Long operations |
| **File Operations** | Backend | Medium | Stateless | No | File I/O |
| **Session Management** | Backend | Medium | Stateful | No | Multi-session |
| **Frontend-Backend** | Integration | Medium | Both | Yes | Full stack |
| **Polling Pattern** | Integration | Medium | Both | Yes | Progress tracking |

---

## Technology Stack

**Frontend:**
- React 18
- Vite 6
- JavaScript (no TypeScript)
- CSS Modules

**Backend:**
- FastAPI
- Uvicorn
- Pydantic AI
- Python 3.11+

**Integration:**
- REST API
- Polling (no WebSocket)
- CORS enabled

---

## Project Structure

```
src/ui/web/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Research.jsx
│   │   │   └── StoryGenerator.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── backend/
    ├── api/
    │   ├── routers/
    │   │   ├── research.py
    │   │   └── story_generator.py
    │   └── main.py
    └── requirements.txt
```

---

## Development Setup

**Frontend:**
```bash
cd src/ui/web/frontend
npm install
npm run dev
```

**Backend:**
```bash
cd src/ui/web/backend
pip install -r requirements.txt
uvicorn api.main:app --reload
```

---

## Common Import Patterns

**Frontend:**
```javascript
import { useState, useEffect } from 'react'
```

**Backend:**
```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.agents.{agent_name} import AgentClass
```

---

## Getting Started

**To create a new web feature:**

1. **Choose patterns** from the quick selector above
2. **Read `COMMON.md`** for shared components
3. **Read specific pattern files** for your use case
4. **Follow the templates** and customize marked sections
5. **Test frontend and backend** separately, then together

---

## File Location

All blueprint files are in `PDs/blueprints/interfaces/web/`:

```
PDs/blueprints/interfaces/web/
├── INDEX.md (this file)
├── COMMON.md
├── frontend/
│   ├── page_component.md
│   ├── api_communication.md
│   ├── state_management.md
│   └── form_handling.md
├── backend/
│   ├── router_module.md
│   ├── agent_integration.md
│   ├── background_tasks.md
│   ├── file_operations.md
│   └── session_management.md
└── integration/
    ├── frontend_backend.md
    └── polling_pattern.md
```

---

## Related Documentation

- `COMMON.md` - Shared web components (this directory)
- `../../libs/` - Library blueprints
- `../cli/` - CLI interface patterns
- `../../pydantic/pydantic_ai_agent_guide.md` - Agent development patterns

---

## Examples by Use Case

### Research & Exploration
- Page Component → Research page with session selection
- API Communication → Fetch sessions, submit queries
- Polling Pattern → Not needed (immediate response)

### Content Generation
- Background Tasks → Long-running story/shot generation
- Polling Pattern → Check generation progress
- File Operations → Download generated content

### Form-Based Interaction
- Form Handling → Subject input, validation
- State Management → Form state, errors
- API Communication → Submit form data

---

## Quick Reference

**Create a page:**
```javascript
function MyPage() {
  const [data, setData] = useState(null)

  useEffect(() => {
    // Fetch data
  }, [])

  return <div>{/* UI */}</div>
}
```

**Create an endpoint:**
```python
router = APIRouter()

@router.post("/endpoint")
async def endpoint(request: RequestModel):
    return {"result": "data"}
```

**Polling pattern:**
```javascript
useEffect(() => {
  const interval = setInterval(() => {
    // Check status
  }, 2000)
  return () => clearInterval(interval)
}, [taskId])
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Support

For questions about:
- **Web patterns** → Read specific pattern file
- **Technology stack** → Read `COMMON.md`
- **Agent integration** → Read `backend/agent_integration.md`
- **Full stack flow** → Read `integration/frontend_backend.md`
