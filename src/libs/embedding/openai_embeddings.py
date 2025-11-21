import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv('OPENROUTER_API_KEY')
        )
    return _openai_client


def get_embedding_model() -> str:
    return os.getenv('EMBEDDING_MODEL', 'openai/text-embedding-3-small')


def generate_embedding(text: str) -> list[float]:
    client = get_openai_client()
    model = get_embedding_model()

    response = client.embeddings.create(
        input=text,
        model=model
    )

    return response.data[0].embedding
