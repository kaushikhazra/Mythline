from dataclasses import dataclass, field

from src.graphs.content_reviewer.models.session_models import ReviewSession
from src.agents.search_query_generator.models import SearchQueries

@dataclass
class ReviewState:
    session_id: str
    content: str
    max_retries: int = 3
    quality_threshold: float = 0.8
    session: ReviewSession | None = None
    search_queries: SearchQueries | None = None
    saved_context: str | None = None
    web_data: list[dict] = field(default_factory=list)
    current_review: dict | None = None
    quality_score: float = 0.0
    workflow_stage: str = ""
    error_message: str | None = None
    human_feedback: str | None = None
    human_invoked: bool = False
