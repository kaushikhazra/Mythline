from typing import Literal
from pydantic import BaseModel, Field


class ShotReviewIssue(BaseModel):
    category: Literal["parameter", "cinematography", "duration", "actor", "text"]
    severity: Literal["critical", "high", "medium", "low"]
    description: str = Field(description="What the issue is")
    suggestion: str = Field(description="How to fix it")


class ShotReviewResult(BaseModel):
    passed: bool = Field(description="Whether the shot meets quality threshold")
    quality_score: float = Field(description="Overall quality score 0.0-1.0")
    parameter_validity_score: float = Field(description="TTS params in valid ranges 0.0-1.0")
    cinematography_score: float = Field(description="Camera choices appropriate 0.0-1.0")
    issues: list[ShotReviewIssue] = Field(default_factory=list, description="Specific problems found")
    suggestions: list[str] = Field(default_factory=list, description="Improvement guidance for regeneration")
    summary: str = Field(description="Brief 1-2 sentence assessment")
