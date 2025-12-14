from typing import Literal
from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    category: Literal["lore", "narrative", "word_count", "consistency", "dialogue", "template", "game_data", "addressee", "exposition"]
    severity: Literal["critical", "high", "medium", "low"]
    description: str = Field(description="What the issue is")
    suggestion: str = Field(description="How to fix it")


class StoryReviewResult(BaseModel):
    passed: bool = Field(description="Whether the segment meets quality threshold")
    quality_score: float = Field(description="Overall quality score 0.0-1.0")
    lore_accuracy_score: float = Field(description="WoW lore correctness 0.0-1.0")
    narrative_quality_score: float = Field(description="Writing quality 0.0-1.0")
    issues: list[ReviewIssue] = Field(default_factory=list, description="Specific problems found")
    suggestions: list[str] = Field(default_factory=list, description="Improvement guidance for regeneration")
    summary: str = Field(description="Brief 1-2 sentence assessment")
