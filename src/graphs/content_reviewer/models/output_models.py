from datetime import datetime
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    session_id: str = Field(description="Session identifier")
    retry_count: int = Field(description="Current retry count")
    max_retries: int = Field(description="Maximum retries allowed")
    quality_score: float = Field(description="Quality score (0.0-1.0)")
    quality_threshold: float = Field(description="Required threshold (0.0-1.0)")
    passed: bool = Field(description="Did content meet threshold?")
    max_retries_reached: bool = Field(description="Was max reached?")
    needs_human_review: bool = Field(description="Does it need human review?")
    human_feedback_provided: bool = Field(description="Was human invoked THIS call?")
    session_completed: bool = Field(description="Was session wiped (done)?")
    review_details: dict = Field(description="Full review details")
    saved_context_summary: str | None = Field(default=None, description="Context used summary")
    web_references: list[dict] = Field(default_factory=list, description="Web references used")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="When this result was generated")
    attempt_history: list[dict] = Field(default_factory=list, description="History of all attempts")
