"""Embedding generation for the Storage MCP service.

Uses the shared provider-agnostic embedding strategy pattern.
Domain logic (_build_embeddable_text, enrich_with_embedding) stays here;
the actual embedding generation is delegated to shared/embedding.py.
"""

from __future__ import annotations

import logging

from shared.embedding import create_embedding_provider, EmbeddingProvider

logger = logging.getLogger(__name__)

EMBEDDABLE_TABLES = {"zone", "npc", "faction", "lore", "narrative_item"}

_provider: EmbeddingProvider | None = None


def _get_provider() -> EmbeddingProvider:
    """Lazy-init the embedding provider singleton."""
    global _provider
    if _provider is None:
        _provider = create_embedding_provider()
    return _provider


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
    """Generate an embedding vector via the configured provider.

    Returns None if the provider is not configured or the call fails.
    """
    try:
        provider = _get_provider()
        return await provider.embed(text)
    except Exception:
        logger.debug("Embedding generation failed", exc_info=True)
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
