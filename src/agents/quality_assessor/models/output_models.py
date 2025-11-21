from pydantic import BaseModel, Field

class ReviewIssue(BaseModel):
    category: str = Field(description="Issue category (clarity, accuracy, structure, tone, grammar)")
    severity: str = Field(description="Severity level (critical, high, medium, low)")
    location: str = Field(description="Where issue occurs (paragraph, section, etc.)")
    description: str = Field(description="What the issue is")
    suggestion: str = Field(description="How to fix it")
    example: str | None = Field(default=None, description="Example of corrected version")

class QualityAssessment(BaseModel):
    quality_score: float = Field(description="Overall score (0.0-1.0)")
    confidence: float = Field(description="Confidence in assessment (0.0-1.0)")
    strengths: list[str] = Field(description="Positive aspects")
    weaknesses: list[str] = Field(description="Areas needing improvement")
    issues: list[ReviewIssue] = Field(description="Detailed issues found")
    recommendations: list[str] = Field(description="Actionable recommendations")
    summary: str = Field(description="Brief assessment (2-3 sentences)")
    meets_standards: bool = Field(description="Does it meet basic standards?")
