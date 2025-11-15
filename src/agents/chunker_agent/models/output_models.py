from pydantic import BaseModel


class Chunk(BaseModel):
    text: str
    actor: str
    chunk_type: str
    reference: str
