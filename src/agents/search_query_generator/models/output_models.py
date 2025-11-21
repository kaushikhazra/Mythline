from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    kb_query: str = Field(description="Search query for knowledge base to find past reviews, guidelines, and human feedback")
    web_query: str = Field(description="Search query for web to find current best practices, industry standards, and expert guidance")
