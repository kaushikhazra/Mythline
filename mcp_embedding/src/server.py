"""Embedding MCP Service — generates vector embeddings via OpenRouter."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MCP_EMBEDDING_PORT = int(os.getenv("MCP_EMBEDDING_PORT", "8004"))

server = FastMCP(name="Embedding Service", host="0.0.0.0", port=MCP_EMBEDDING_PORT)


@server.tool()
async def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for the given text using OpenRouter.

    Args:
        text: The text to generate an embedding for.

    Returns:
        A list of floats representing the embedding vector.
    """
    if not text.strip():
        raise ValueError("Text must not be empty")

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


@server.tool()
async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate vector embeddings for multiple texts in a single API call.

    Args:
        texts: A list of texts to generate embeddings for.

    Returns:
        A list of embedding vectors, one per input text, in the same order.
    """
    if not texts:
        raise ValueError("Texts list must not be empty")

    cleaned = [t for t in texts if t.strip()]
    if len(cleaned) != len(texts):
        raise ValueError("All texts must be non-empty strings")

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


if __name__ == "__main__":
    server.run(transport="streamable-http")
