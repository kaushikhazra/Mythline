"""Integration tests for the Storage MCP server.

Requires SurrealDB running on ws://localhost:8010/rpc.
Start via: cd poc/surrealdb && docker compose up -d
"""

import json
from unittest.mock import patch, AsyncMock

import pytest

import src.db as db_module
import src.embedding as emb_module
from src.db import get_db, close_db, _first
from src.schema import initialize_schema
from src.server import (
    create_record,
    get_record,
    update_record,
    delete_record,
    query_records,
    create_relation,
    traverse,
    save_checkpoint,
    load_checkpoint,
    delete_checkpoint,
    initialize,
)


@pytest.fixture(autouse=True)
def disable_embedding():
    """Disable embedding API calls for all tests."""
    with patch.object(emb_module, "OPENROUTER_API_KEY", ""):
        yield


@pytest.fixture(autouse=True)
async def setup_db():
    """Connect to SurrealDB and clean up after each test."""
    with patch.object(db_module, "SURREALDB_URL", "ws://localhost:8010/rpc"), \
         patch.object(db_module, "SURREALDB_NAMESPACE", "test_mythline"), \
         patch.object(db_module, "SURREALDB_DATABASE", "test_storage"):
        db_module._db_instance = None
        db = await get_db()
        await initialize_schema()
        yield db
        for table in ["zone", "npc", "faction", "lore", "narrative_item", "research_state"]:
            await db.query(f"DELETE FROM {table}")
        for rel in ["connects_to", "belongs_to", "located_in", "relates_to",
                     "child_of", "stance_toward", "found_in", "about"]:
            await db.query(f"DELETE FROM {rel}")
        await close_db()


class TestInitialize:
    async def test_schema_initialization(self):
        result = await initialize()
        assert "initialized" in result.lower()


class TestCRUD:
    async def test_create_and_get_zone(self):
        zone_data = {
            "name": "Elwynn Forest",
            "game": "wow",
            "level_range": {"min": 1, "max": 10},
            "narrative_arc": "Introduction to the Alliance",
            "political_climate": "Stable under Stormwind",
            "era": "Classic",
        }
        result = await create_record("zone", "elwynn_forest", json.dumps(zone_data))
        created = json.loads(result)
        assert created is not None

        result = await get_record("zone", "elwynn_forest")
        record = json.loads(result)
        assert record["name"] == "Elwynn Forest"
        assert record["game"] == "wow"
        assert record["level_range"]["min"] == 1

    async def test_create_npc(self):
        npc_data = {
            "name": "Marshal McBride",
            "personality": "Stern but fair military officer",
            "motivations": ["Protect Northshire", "Train new recruits"],
            "role": "quest_giver",
        }
        result = await create_record("npc", "marshal_mcbride", json.dumps(npc_data))
        created = json.loads(result)
        assert created is not None

        result = await get_record("npc", "marshal_mcbride")
        record = json.loads(result)
        assert record["name"] == "Marshal McBride"
        assert record["role"] == "quest_giver"

    async def test_update_record(self):
        zone_data = {"name": "Westfall", "game": "wow", "era": "Classic"}
        await create_record("zone", "westfall", json.dumps(zone_data))

        update_data = {"narrative_arc": "Rise of the Defias", "confidence": 0.85}
        result = await update_record("zone", "westfall", json.dumps(update_data))
        updated = json.loads(result)
        assert updated["narrative_arc"] == "Rise of the Defias"
        assert updated["confidence"] == 0.85
        assert updated["name"] == "Westfall"

    async def test_delete_record(self):
        await create_record("zone", "deadmines", json.dumps({"name": "The Deadmines"}))
        result = await delete_record("zone", "deadmines")
        assert "deleted" in json.loads(result)

        result = await get_record("zone", "deadmines")
        assert json.loads(result) is None

    async def test_query_with_filter(self):
        await create_record("zone", "z1", json.dumps({"name": "Zone 1", "game": "wow"}))
        await create_record("zone", "z2", json.dumps({"name": "Zone 2", "game": "wow"}))
        await create_record("zone", "z3", json.dumps({"name": "Zone 3", "game": "ff14"}))

        result = await query_records("zone", "game = 'wow'")
        records = json.loads(result)
        assert len(records) == 2
        names = {r["name"] for r in records}
        assert names == {"Zone 1", "Zone 2"}

    async def test_query_without_filter(self):
        await create_record("zone", "z1", json.dumps({"name": "Zone 1", "game": "wow"}))
        await create_record("zone", "z2", json.dumps({"name": "Zone 2", "game": "wow"}))

        result = await query_records("zone")
        records = json.loads(result)
        assert len(records) == 2

    async def test_invalid_table_raises_error(self):
        with pytest.raises(ValueError, match="Invalid table"):
            await create_record("invalid_table", "id1", json.dumps({"test": True}))

    async def test_create_all_table_types(self):
        tables_data = {
            "faction": ("horde", {"name": "The Horde", "ideology": "Strength and honor"}),
            "lore": ("titan_creation", {"title": "Titan Creation", "category": "cosmology", "content": "The titans shaped Azeroth"}),
            "narrative_item": ("ashbringer", {"name": "Ashbringer", "story_arc": "The Corrupted Blade", "significance": "legendary"}),
        }
        for table, (record_id, data) in tables_data.items():
            result = await create_record(table, record_id, json.dumps(data))
            assert json.loads(result) is not None

            result = await get_record(table, record_id)
            record = json.loads(result)
            assert record is not None


class TestGraphRelationships:
    async def test_create_zone_connection(self):
        await create_record("zone", "elwynn", json.dumps({"name": "Elwynn Forest"}))
        await create_record("zone", "westfall", json.dumps({"name": "Westfall"}))

        result = await create_relation("connects_to", "zone:elwynn", "zone:westfall")
        relation = json.loads(result)
        assert relation is not None

    async def test_create_npc_faction_relation(self):
        await create_record("npc", "thrall", json.dumps({"name": "Thrall"}))
        await create_record("faction", "horde", json.dumps({"name": "The Horde"}))

        result = await create_relation("belongs_to", "npc:thrall", "faction:horde")
        assert json.loads(result) is not None

    async def test_create_relation_with_properties(self):
        await create_record("npc", "n1", json.dumps({"name": "NPC 1"}))
        await create_record("npc", "n2", json.dumps({"name": "NPC 2"}))

        props = {"relationship_type": "rival", "description": "Bitter enemies"}
        result = await create_relation(
            "relates_to", "npc:n1", "npc:n2", json.dumps(props)
        )
        assert json.loads(result) is not None

    async def test_traverse_forward(self):
        await create_record("zone", "a", json.dumps({"name": "Zone A"}))
        await create_record("zone", "b", json.dumps({"name": "Zone B"}))
        await create_record("zone", "c", json.dumps({"name": "Zone C"}))
        await create_relation("connects_to", "zone:a", "zone:b")
        await create_relation("connects_to", "zone:a", "zone:c")

        result = await traverse("zone:a", "connects_to", "out")
        related = json.loads(result)
        assert len(related) == 2

    async def test_traverse_reverse(self):
        await create_record("npc", "thrall", json.dumps({"name": "Thrall"}))
        await create_record("faction", "horde", json.dumps({"name": "The Horde"}))
        await create_relation("belongs_to", "npc:thrall", "faction:horde")

        result = await traverse("faction:horde", "belongs_to", "in")
        related = json.loads(result)
        assert len(related) == 1
        assert related[0]["name"] == "Thrall"

    async def test_invalid_relation_type(self):
        with pytest.raises(ValueError, match="Invalid relation type"):
            await create_relation("invalid_rel", "zone:a", "zone:b")


class TestCheckpoint:
    async def test_save_and_load_checkpoint(self):
        state = {
            "zone_name": "Elwynn Forest",
            "current_step": 3,
            "step_data": {"zone_overview": {"name": "Elwynn Forest"}},
            "progression_queue": ["Westfall", "Loch Modan"],
            "priority_queue": [],
            "completed_zones": [],
            "failed_zones": [],
            "daily_tokens_used": 5000,
            "last_reset_date": "2026-02-21",
        }
        await save_checkpoint("world_lore_researcher", json.dumps(state))

        result = await load_checkpoint("world_lore_researcher")
        loaded = json.loads(result)
        assert loaded["zone_name"] == "Elwynn Forest"
        assert loaded["current_step"] == 3
        assert loaded["daily_tokens_used"] == 5000
        assert loaded["progression_queue"] == ["Westfall", "Loch Modan"]

    async def test_update_checkpoint(self):
        state = {"zone_name": "Zone A", "current_step": 1}
        await save_checkpoint("test_agent", json.dumps(state))

        updated_state = {"zone_name": "Zone A", "current_step": 5, "daily_tokens_used": 10000}
        await save_checkpoint("test_agent", json.dumps(updated_state))

        result = await load_checkpoint("test_agent")
        loaded = json.loads(result)
        assert loaded["current_step"] == 5
        assert loaded["daily_tokens_used"] == 10000

    async def test_load_nonexistent_checkpoint(self):
        result = await load_checkpoint("nonexistent_agent")
        assert json.loads(result) is None

    async def test_delete_checkpoint(self):
        await save_checkpoint("temp_agent", json.dumps({"zone_name": "Test"}))
        await delete_checkpoint("temp_agent")

        result = await load_checkpoint("temp_agent")
        assert json.loads(result) is None


class TestEmbeddingOnWrite:
    """Tests that verify embedding integration is wired correctly."""

    async def test_create_record_calls_embedding(self):
        mock_embedding = [0.1] * 1536
        with patch.object(emb_module, "OPENROUTER_API_KEY", "fake-key"), \
             patch.object(emb_module, "generate_embedding", new_callable=AsyncMock, return_value=mock_embedding):
            zone_data = {
                "name": "Elwynn Forest",
                "narrative_arc": "Alliance starting zone",
                "political_climate": "Stable",
                "era": "Classic",
            }
            await create_record("zone", "elwynn_emb", json.dumps(zone_data))

            result = await get_record("zone", "elwynn_emb")
            record = json.loads(result)
            assert record is not None
            assert record["name"] == "Elwynn Forest"

    async def test_no_embedding_when_key_missing(self):
        """Without API key, record is created without embedding."""
        zone_data = {"name": "Test Zone", "narrative_arc": "Test"}
        await create_record("zone", "no_emb", json.dumps(zone_data))

        result = await get_record("zone", "no_emb")
        record = json.loads(result)
        assert record["name"] == "Test Zone"
        assert "embedding" not in record or record.get("embedding") is None

    async def test_research_state_not_embedded(self):
        """Checkpoint records should never get embeddings."""
        with patch.object(emb_module, "OPENROUTER_API_KEY", "fake-key"), \
             patch.object(emb_module, "generate_embedding", new_callable=AsyncMock) as mock_gen:
            await save_checkpoint("test", json.dumps({"zone_name": "Test"}))
            mock_gen.assert_not_called()
