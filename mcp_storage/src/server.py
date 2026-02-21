"""Storage MCP Service — SurrealDB backend for world lore and research state."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.db import get_db, close_db, _first, to_json
from src.embedding import enrich_with_embedding, EMBEDDABLE_TABLES
from src.schema import initialize_schema

MCP_STORAGE_PORT = int(os.getenv("MCP_STORAGE_PORT", "8005"))

server = FastMCP(name="Storage Service", port=MCP_STORAGE_PORT)

VALID_TABLES = {"zone", "npc", "faction", "lore", "narrative_item"}
VALID_RELATIONS = {
    "connects_to", "belongs_to", "located_in", "relates_to",
    "child_of", "stance_toward", "found_in", "about",
}


# --- Lifecycle ---


@server.tool()
async def initialize() -> str:
    """Initialize the storage schema. Call this on service startup.

    Creates all tables, relation tables, and vector indexes if they
    don't already exist.

    Returns:
        Confirmation message.
    """
    await initialize_schema()
    return "Schema initialized successfully"


# --- World Lore CRUD ---


@server.tool()
async def create_record(table: str, record_id: str, data: str) -> str:
    """Create a new record in the specified table.

    Automatically generates an embedding vector for embeddable tables
    (zone, npc, faction, lore, narrative_item).

    Args:
        table: Table name (zone, npc, faction, lore, narrative_item).
        record_id: Record ID (e.g., "elwynn_forest", "thrall").
        data: JSON string of the record data.

    Returns:
        JSON string of the created record.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of {VALID_TABLES}")

    parsed = json.loads(data)
    parsed["updated_at"] = datetime.now(timezone.utc).isoformat()

    parsed = await enrich_with_embedding(table, parsed)

    db = await get_db()
    thing = f"{table}:{record_id}"

    if parsed.get("embedding"):
        # SurrealDB SDK doesn't reliably index vectors inserted via create().
        # Use raw SurrealQL CREATE with embedding as a literal array.
        embedding = parsed.pop("embedding")
        embedding_json = json.dumps(embedding)
        result = await db.query(f"CREATE {thing} CONTENT $data", {"data": parsed})
        await db.query(f"UPDATE {thing} SET embedding = {embedding_json}")
    else:
        result = await db.query(f"CREATE {thing} CONTENT $data", {"data": parsed})

    final = _first(await db.select(thing))
    return to_json(final)


@server.tool()
async def get_record(table: str, record_id: str) -> str:
    """Get a record by table and ID.

    Args:
        table: Table name (zone, npc, faction, lore, narrative_item).
        record_id: Record ID.

    Returns:
        JSON string of the record, or null if not found.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of {VALID_TABLES}")

    db = await get_db()
    result = await db.select(f"{table}:{record_id}")
    record = _first(result)
    return to_json(record)


@server.tool()
async def update_record(table: str, record_id: str, data: str) -> str:
    """Update an existing record (partial merge).

    Re-generates embedding if embeddable fields change.

    Args:
        table: Table name (zone, npc, faction, lore, narrative_item).
        record_id: Record ID.
        data: JSON string of the fields to update.

    Returns:
        JSON string of the updated record.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of {VALID_TABLES}")

    parsed = json.loads(data)
    parsed["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    existing = _first(await db.select(f"{table}:{record_id}"))
    if existing:
        merged = {**existing, **parsed}
        merged = await enrich_with_embedding(table, merged)
        if merged.get("embedding"):
            embedding = merged.pop("embedding")
            embedding_json = json.dumps(embedding)
            await db.update(f"{table}:{record_id}", merged)
            await db.query(f"UPDATE {table}:{record_id} SET embedding = {embedding_json}")
        else:
            await db.update(f"{table}:{record_id}", merged)
    else:
        parsed = await enrich_with_embedding(table, parsed)
        await db.query(f"CREATE {table}:{record_id} CONTENT $data", {"data": parsed})

    result = _first(await db.select(f"{table}:{record_id}"))
    return to_json(result)


@server.tool()
async def delete_record(table: str, record_id: str) -> str:
    """Delete a record by table and ID.

    Args:
        table: Table name (zone, npc, faction, lore, narrative_item).
        record_id: Record ID.

    Returns:
        Confirmation message.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of {VALID_TABLES}")

    db = await get_db()
    await db.delete(f"{table}:{record_id}")
    return json.dumps({"deleted": f"{table}:{record_id}"})


@server.tool()
async def query_records(table: str, filter_expr: str = "", limit: int = 50) -> str:
    """Query records from a table with optional SurrealQL filter.

    Args:
        table: Table name (zone, npc, faction, lore, narrative_item).
        filter_expr: Optional SurrealQL WHERE clause (without "WHERE").
                     Example: "game = 'wow' AND confidence > 0.8"
        limit: Maximum number of records to return.

    Returns:
        JSON string of matching records.
    """
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of {VALID_TABLES}")

    query = f"SELECT * FROM {table}"
    if filter_expr:
        query += f" WHERE {filter_expr}"
    query += f" LIMIT {limit}"

    db = await get_db()
    result = await db.query(query)
    return to_json(_extract_query_result(result))


@server.tool()
async def search_similar(table: str, text: str, top_k: int = 5) -> str:
    """Search for records similar to the given text using vector similarity.

    Uses cosine similarity on the embedding field. Works on any embeddable
    table (zone, npc, faction, lore, narrative_item).

    Args:
        table: Table name to search.
        text: The search text to find similar records for.
        top_k: Number of results to return.

    Returns:
        JSON string of similar records with similarity scores.
    """
    if table not in EMBEDDABLE_TABLES:
        raise ValueError(f"Table {table} does not support vector search")

    from src.embedding import generate_embedding
    query_embedding = await generate_embedding(text)
    if not query_embedding:
        return json.dumps([])

    embedding_json = json.dumps(query_embedding)
    query = (
        f"SELECT *, vector::similarity::cosine(embedding, {embedding_json}) AS similarity "
        f"FROM {table} "
        f"WHERE embedding IS NOT NONE "
        f"ORDER BY similarity DESC "
        f"LIMIT {top_k}"
    )

    db = await get_db()
    result = await db.query(query)
    return to_json(_extract_query_result(result))


# --- Graph Relationships ---


@server.tool()
async def create_relation(
    relation_type: str, from_record: str, to_record: str, properties: str = "{}"
) -> str:
    """Create a graph relationship between two records.

    Args:
        relation_type: Relation type (connects_to, belongs_to, located_in,
                       relates_to, child_of, stance_toward, found_in, about).
        from_record: Source record ID (e.g., "npc:thrall").
        to_record: Target record ID (e.g., "faction:horde").
        properties: Optional JSON string of edge properties.

    Returns:
        JSON string of the created relationship.
    """
    if relation_type not in VALID_RELATIONS:
        raise ValueError(f"Invalid relation type: {relation_type}. Must be one of {VALID_RELATIONS}")

    props = json.loads(properties)
    db = await get_db()

    if props:
        props_set = ", ".join(f"{k} = $props.{k}" for k in props)
        query = f"RELATE {from_record}->{relation_type}->{to_record} SET {props_set}"
        result = await db.query(query, {"props": props})
    else:
        query = f"RELATE {from_record}->{relation_type}->{to_record}"
        result = await db.query(query)

    return to_json(_extract_query_result(result))


@server.tool()
async def traverse(record_id: str, relation_type: str, direction: str = "out") -> str:
    """Traverse graph relationships from a record.

    Args:
        record_id: Starting record ID (e.g., "zone:elwynn_forest").
        relation_type: Relation type to traverse.
        direction: "out" for forward, "in" for reverse, "both" for bidirectional.

    Returns:
        JSON string of related records.
    """
    if relation_type not in VALID_RELATIONS:
        raise ValueError(f"Invalid relation type: {relation_type}")

    db = await get_db()
    if direction == "out":
        query = f"SELECT ->{relation_type}->?.* AS related FROM {record_id}"
    elif direction == "in":
        query = f"SELECT <-{relation_type}<-?.* AS related FROM {record_id}"
    else:
        query = f"SELECT <->{relation_type}<->?.* AS related FROM {record_id}"

    result = await db.query(query)
    extracted = _extract_query_result(result)
    if extracted and isinstance(extracted, list) and "related" in extracted[0]:
        return to_json(extracted[0]["related"])
    return json.dumps([])


# --- Checkpoint / Research State ---


@server.tool()
async def save_checkpoint(agent_id: str, state: str) -> str:
    """Save a research checkpoint for an agent.

    Overwrites any existing checkpoint for this agent.

    Args:
        agent_id: Agent identifier (e.g., "world_lore_researcher").
        state: JSON string of the ResearchCheckpoint data.

    Returns:
        Confirmation message.
    """
    parsed = json.loads(state)
    parsed["saved_at"] = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    existing = _first(await db.select(f"research_state:{agent_id}"))
    if existing:
        await db.update(f"research_state:{agent_id}", parsed)
    else:
        await db.query(
            f"CREATE research_state:{agent_id} CONTENT $data",
            {"data": parsed},
        )

    return json.dumps({"saved": f"research_state:{agent_id}"})


@server.tool()
async def load_checkpoint(agent_id: str) -> str:
    """Load a research checkpoint for an agent.

    Args:
        agent_id: Agent identifier (e.g., "world_lore_researcher").

    Returns:
        JSON string of the checkpoint data, or null if none exists.
    """
    db = await get_db()
    result = _first(await db.select(f"research_state:{agent_id}"))
    return to_json(result)


@server.tool()
async def delete_checkpoint(agent_id: str) -> str:
    """Delete a research checkpoint for an agent.

    Args:
        agent_id: Agent identifier (e.g., "world_lore_researcher").

    Returns:
        Confirmation message.
    """
    db = await get_db()
    await db.delete(f"research_state:{agent_id}")
    return json.dumps({"deleted": f"research_state:{agent_id}"})


# --- Helpers ---


def _extract_query_result(result: Any) -> Any:
    """Extract the actual data from a SurrealDB query() response.

    query() wraps results in a list of dicts with 'result' and 'status' keys.
    """
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict) and "result" in first:
            return first["result"]
        return result
    return result


if __name__ == "__main__":
    server.run(transport="streamable-http")
