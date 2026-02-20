# Backend: Agent Integration

Integrating Pydantic AI agents with FastAPI endpoints.

---

## Overview

**Use when:** Connecting agents to API, running agent operations, managing agent state, streaming responses.

**Pattern:**
```
Import Agent → Initialize Agent → Run Agent → Return Response → Handle Errors
```

---

## Basic Agent Integration

### Simple Agent Call

```python
from fastapi import APIRouter
from pydantic import BaseModel
from src.agents.my_agent import MyAgent

router = APIRouter()

class AgentRequest(BaseModel):
    prompt: str

class AgentResponse(BaseModel):
    output: str

@router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id="default")
    result = agent.run(request.prompt)

    return AgentResponse(output=result.output)
```

---

## Agent Lifecycle Management

### Single Instance (Stateless)

```python
# Create once, reuse for all requests
agent = MyStatelessAgent()

@router.post("/process")
async def process(request: Request):
    result = agent.run(request.prompt)
    return {"output": result.output}
```

### Instance Per Session (Stateful)

```python
# Store agents by session
agents = {}

def get_or_create_agent(session_id: str):
    if session_id not in agents:
        agents[session_id] = MyStatefulAgent(session_id)
    return agents[session_id]

@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = get_or_create_agent(request.session_id)
    result = agent.run(request.prompt)
    return {"output": result.output}
```

### Instance Per Request

```python
@router.post("/run")
async def run_agent(request: AgentRequest):
    # Create new instance for each request
    agent = MyAgent(session_id=request.session_id)
    result = agent.run(request.prompt)
    return {"output": result.output}
```

---

## Async Agent Execution

### Using async/await

```python
@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id=request.session_id)

    # Use run_async for async execution
    result = await agent.run_async(request.prompt)

    return {"output": result.output}
```

### Why Async?

```python
# Wrong - blocks event loop
@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id=request.session_id)
    result = agent.run(request.prompt)  # Blocks
    return {"output": result.output}

# Correct - non-blocking
@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id=request.session_id)
    result = await agent.run_async(request.prompt)  # Non-blocking
    return {"output": result.output}
```

---

## Session Management

### Auto-Generate Session ID

```python
from datetime import datetime

@router.post("/run")
async def run_agent(request: AgentRequest):
    if request.session_id:
        session_id = request.session_id
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    agent = get_or_create_agent(session_id)
    result = await agent.run_async(request.prompt)

    return {
        "session_id": session_id,
        "output": result.output
    }
```

### Session Cleanup

```python
# Remove agent from memory
@router.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    if session_id in agents:
        del agents[session_id]
    return {"status": "closed"}
```

---

## Error Handling

### Basic Error Handling

```python
from fastapi import HTTPException

@router.post("/run")
async def run_agent(request: AgentRequest):
    try:
        agent = MyAgent(session_id=request.session_id)
        result = await agent.run_async(request.prompt)
        return {"output": result.output}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Agent execution failed")
```

### Detailed Error Messages

```python
@router.post("/run")
async def run_agent(request: AgentRequest):
    try:
        agent = MyAgent(session_id=request.session_id)
        result = await agent.run_async(request.prompt)
        return {"output": result.output}
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Required file not found: {str(e)}"
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Agent execution timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )
```

---

## Response Formatting

### Extract Output

```python
@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id=request.session_id)
    result = await agent.run_async(request.prompt)

    # Return just the output
    return {"output": result.output}
```

### Include Metadata

```python
@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(session_id=request.session_id)
    result = await agent.run_async(request.prompt)

    return {
        "output": result.output,
        "session_id": request.session_id,
        "message_count": len(result.all_messages()),
        "timestamp": datetime.now().isoformat()
    }
```

---

## Complete Examples

### Research Agent Integration

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.agents.story_research_agent.agent import StoryResearcher

router = APIRouter()
agents = {}

class ResearchRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ResearchResponse(BaseModel):
    session_id: str
    response: str

def get_or_create_agent(session_id: str) -> StoryResearcher:
    if session_id not in agents:
        agents[session_id] = StoryResearcher(session_id)
    return agents[session_id]

@router.post("/research/run", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    # Generate session ID if not provided
    if request.session_id:
        session_id = request.session_id
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Get or create agent
    agent = get_or_create_agent(session_id)

    # Run agent asynchronously
    result = await agent.run_async(request.message)

    return ResearchResponse(
        session_id=session_id,
        response=result.output
    )
```

### Story Creator with Prerequisite Check

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from src.agents.story_creator_agent.agent import StoryCreatorAgent

router = APIRouter()

class StoryRequest(BaseModel):
    subject: str
    player: str

class StoryResponse(BaseModel):
    session_id: str
    output: str

@router.post("/story/create")
async def create_story(request: StoryRequest):
    # Check prerequisite file
    research_path = f"output/{request.subject}/research.md"

    if not Path(research_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Research file not found. Please research {request.subject} first."
        )

    # Create agent
    session_id = request.subject
    agent = StoryCreatorAgent(
        session_id=session_id,
        player_name=request.player
    )

    # Run agent
    result = await agent.run(subject=request.subject)

    return StoryResponse(
        session_id=session_id,
        output=result.output
    )
```

---

## Agent Configuration

### Passing Configuration

```python
class AgentRequest(BaseModel):
    prompt: str
    session_id: str
    temperature: float = 0.7
    max_tokens: int = 1000

@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(
        session_id=request.session_id,
        model_settings={
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
    )

    result = await agent.run_async(request.prompt)
    return {"output": result.output}
```

### Environment-Based Configuration

```python
import os

@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = MyAgent(
        session_id=request.session_id,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=os.getenv("LLM_MODEL", "openai/gpt-4o")
    )

    result = await agent.run_async(request.prompt)
    return {"output": result.output}
```

---

## Multi-Agent Orchestration

### Sequential Agent Calls

```python
@router.post("/pipeline")
async def run_pipeline(request: PipelineRequest):
    # Step 1: Research
    research_agent = ResearchAgent(session_id=request.session_id)
    research_result = await research_agent.run_async(request.topic)

    # Step 2: Generate using research
    story_agent = StoryAgent(session_id=request.session_id)
    story_result = await story_agent.run_async(research_result.output)

    return {
        "research": research_result.output,
        "story": story_result.output
    }
```

### Parallel Agent Calls

```python
import asyncio

@router.post("/parallel")
async def run_parallel(request: ParallelRequest):
    # Create agents
    agent1 = Agent1(session_id=request.session_id)
    agent2 = Agent2(session_id=request.session_id)

    # Run in parallel
    results = await asyncio.gather(
        agent1.run_async(request.prompt1),
        agent2.run_async(request.prompt2)
    )

    return {
        "result1": results[0].output,
        "result2": results[1].output
    }
```

---

## Accessing Agent Context

### Get Message History

```python
from src.libs.agent_memory.context_memory import load_context

@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str):
    agent_id = "my_agent"
    messages = load_context(agent_id, session_id)

    formatted = []
    for msg in messages:
        for part in msg.parts:
            if part.part_kind == 'user-prompt':
                formatted.append({"role": "user", "content": part.content})
            elif part.part_kind == 'text':
                formatted.append({"role": "assistant", "content": part.content})

    return {"messages": formatted}
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
- Use async def and await for agent calls
- Handle agent errors gracefully
- Validate prerequisites before running agents
- Use session management for stateful agents
- Clean up agent instances when done
- Return structured responses
- Use Pydantic models for requests/responses

**DON'T:**
- Block the event loop with synchronous agent.run()
- Expose internal agent errors to clients
- Create agents without error handling
- Forget to manage agent lifecycle
- Store sensitive data in responses
- Hardcode agent configuration

---

## Related Documentation

- `router_module.md` - Route organization
- `background_tasks.md` - Long-running agent operations
- `session_management.md` - Session handling patterns
- `../COMMON.md` - Common backend patterns
- `../../libs/agent_memory/` - Agent memory libraries
