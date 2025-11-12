from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from src.agents.story_research_agent.agent import StoryResearcher
from src.libs.agent_memory.context_memory import load_context

router = APIRouter()
agents = {}

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

def get_or_create_agent(session_id: str) -> StoryResearcher:
    if session_id not in agents:
        agents[session_id] = StoryResearcher(session_id)
    return agents[session_id]

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
            last_modified=datetime.fromtimestamp(session_file.stat().st_mtime).isoformat(),
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
        formatted_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    return SessionHistory(
        session_id=session_id,
        messages=formatted_messages
    )

@router.post("/research/run", response_model=ResearchResponse)
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
