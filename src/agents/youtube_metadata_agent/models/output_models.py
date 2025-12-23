from pydantic import BaseModel


class YouTubeMetadata(BaseModel):
    title: str
    description: str
    tags: list[str]
