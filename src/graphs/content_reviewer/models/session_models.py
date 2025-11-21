from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ReviewSession:
    session_id: str
    content_hash: str
    max_retries: int
    quality_threshold: float
    retry_count: int = 0
    status: str = "in_progress"
    last_review: dict | None = None
    history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def increment_retry(self):
        self.retry_count += 1
        self.updated_at = datetime.now().isoformat()

    def add_attempt(self, score: float, review_details: dict):
        attempt = {
            "attempt": self.retry_count,
            "quality_score": score,
            "timestamp": datetime.now().isoformat(),
            "review_summary": review_details.get("summary", "")
        }
        self.history.append(attempt)
        self.last_review = review_details
        self.updated_at = datetime.now().isoformat()

    def should_wipe(self) -> bool:
        return self.status in ["completed", "needs_human"]

    def needs_human_review(self) -> bool:
        return self.status == "needs_human"
