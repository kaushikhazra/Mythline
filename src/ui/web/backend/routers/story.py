from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
import asyncio
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
    research_path = f"output/{request.subject}/research.md"

    if not os.path.exists(research_path):
        raise HTTPException(
            status_code=400,
            detail=f"Research file not found at {research_path}. Please research {request.subject} first."
        )

    save_initial_progress(request.subject)

    session_id = request.subject
    story_creator = StoryCreatorAgent(session_id=session_id, player_name=request.player)

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

@router.get("/stories/list")
async def list_stories():
    output_dir = Path("output")
    if not output_dir.exists():
        return []

    stories = []
    for item in output_dir.iterdir():
        if item.is_dir():
            story_file = item / "story.json"
            if story_file.exists():
                stories.append(item.name)

    return sorted(stories)

@router.get("/stories/{subject}")
async def get_story(subject: str):
    story_file = Path(f"output/{subject}/story.json")

    if not story_file.exists():
        raise HTTPException(status_code=404, detail=f"Story not found for subject: {subject}")

    return json.loads(story_file.read_text())
