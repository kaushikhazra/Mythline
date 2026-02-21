"""Embedding generation for the Storage MCP service.

Generates vector embeddings on write by calling OpenRouter directly.
This avoids the overhead of MCP-to-MCP protocol communication.
The Embedding MCP exists for agents to use via MCP protocol; the Storage
MCP as infrastructure calls the API directly.
"""

import os

import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

EMBEDDABLE_TABLES = {"zone", "npc", "faction", "lore", "narrative_item"}


def _build_embeddable_text(table: str, data: dict) -> str:
    """Build a text representation of a record suitable for embedding.

    Combines the most semantically meaningful fields into a single
    string for vector encoding. Different tables emphasize different fields.
    """
    parts = []

    if table == "zone":
        parts = [
            data.get("name", ""),
            data.get("narrative_arc", ""),
            data.get("political_climate", ""),
            data.get("era", ""),
        ]
    elif table == "npc":
        parts = [
            data.get("name", ""),
            data.get("personality", ""),
            " ".join(data.get("motivations", [])),
            data.get("role", ""),
        ]
    elif table == "faction":
        parts = [
            data.get("name", ""),
            data.get("ideology", ""),
            " ".join(data.get("goals", [])),
            data.get("level", ""),
        ]
    elif table == "lore":
        parts = [
            data.get("title", ""),
            data.get("category", ""),
            data.get("content", ""),
        ]
    elif table == "narrative_item":
        parts = [
            data.get("name", ""),
            data.get("story_arc", ""),
            data.get("power_description", ""),
            data.get("significance", ""),
        ]

    return " ".join(p for p in parts if p).strip()


async def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding vector by calling OpenRouter directly.

    Returns None if the API key is not set or the call fails.
    """
    if not OPENROUTER_API_KEY:
        return None

    try:
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
    except (httpx.HTTPError, KeyError, IndexError):
        return None


async def enrich_with_embedding(table: str, data: dict) -> dict:
    """Add an embedding vector to a record if the table supports it.

    Returns the data dict with an 'embedding' field added, or the
    original data if embedding generation fails or is not applicable.
    """
    if table not in EMBEDDABLE_TABLES:
        return data

    text = _build_embeddable_text(table, data)
    if not text:
        return data

    embedding = await generate_embedding(text)
    if embedding:
        data["embedding"] = embedding

    return data
