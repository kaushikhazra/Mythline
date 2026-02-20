from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import json
from src.agents.story_research_agent.agent import StoryResearcher
from src.libs.agent_memory.context_memory import load_context
from src.graphs.story_research_graph.models.research_models import ResearchBrief

router = APIRouter()
agents = {}

OUTPUT_DIR = Path("output")

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


@router.get("/research/subjects")
async def list_subjects():
    if not OUTPUT_DIR.exists():
        return []

    subjects = []
    for subject_dir in OUTPUT_DIR.iterdir():
        if subject_dir.is_dir():
            research_file = subject_dir / "research.json"
            if research_file.exists():
                subjects.append(subject_dir.name)

    return sorted(subjects)


@router.get("/research/{subject}/data")
async def get_research_data(subject: str):
    research_file = OUTPUT_DIR / subject / "research.json"

    if not research_file.exists():
        raise HTTPException(status_code=404, detail=f"Research data not found for subject: {subject}")

    with open(research_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


class SaveResponse(BaseModel):
    status: str
    subject: str


@router.post("/research/{subject}/data", response_model=SaveResponse)
async def save_research_data(subject: str, data: ResearchBrief):
    subject_dir = OUTPUT_DIR / subject

    if not subject_dir.exists():
        raise HTTPException(status_code=404, detail=f"Subject directory not found: {subject}")

    research_file = subject_dir / "research.json"

    with open(research_file, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)

    return SaveResponse(status="saved", subject=subject)
