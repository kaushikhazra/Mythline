"""SurrealDB connection management for the Storage MCP service."""

import json
import os
from datetime import datetime
from typing import Any

from surrealdb import AsyncSurreal

SURREALDB_URL = os.getenv("SURREALDB_URL", "ws://localhost:8010/rpc")
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASS = os.getenv("SURREALDB_PASS", "root")
SURREALDB_NAMESPACE = os.getenv("SURREALDB_NAMESPACE", "mythline")
SURREALDB_DATABASE = os.getenv("SURREALDB_DATABASE", "world_lore")

_db_instance: AsyncSurreal | None = None


async def get_db() -> AsyncSurreal:
    """Get or create the SurrealDB connection singleton.

    Returns a connected and authenticated AsyncSurreal instance.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = AsyncSurreal(SURREALDB_URL)
        await _db_instance.connect()
        await _db_instance.signin({"username": SURREALDB_USER, "password": SURREALDB_PASS})
        await _db_instance.use(SURREALDB_NAMESPACE, SURREALDB_DATABASE)
    return _db_instance


async def close_db() -> None:
    """Close the SurrealDB connection."""
    global _db_instance
    if _db_instance is not None:
        await _db_instance.close()
        _db_instance = None


def _first(result: Any) -> dict | None:
    """Extract the first record from a SurrealDB result.

    SurrealDB select() returns a list for table selects and a dict for
    record selects, but behavior varies. This normalizes the result.
    """
    if isinstance(result, list):
        return result[0] if result else None
    return result


class SurrealEncoder(json.JSONEncoder):
    """JSON encoder that handles SurrealDB-specific types.

    SurrealDB returns RecordID objects for 'id' fields and may return
    datetime objects. This encoder converts them to strings.
    """

    def default(self, o: Any) -> Any:
        if hasattr(o, "table_name") and hasattr(o, "id"):
            return f"{o.table_name}:{o.id}"
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def to_json(obj: Any) -> str:
    """Serialize an object to JSON, handling SurrealDB types."""
    return json.dumps(obj, cls=SurrealEncoder)
