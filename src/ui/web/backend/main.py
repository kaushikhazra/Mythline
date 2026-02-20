from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.ui.web.backend.routers import research, story

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(story.router, prefix="/api", tags=["story"])
