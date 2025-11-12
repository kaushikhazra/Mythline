from fastapi import APIRouter
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
