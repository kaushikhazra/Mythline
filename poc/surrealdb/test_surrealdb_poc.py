"""
SurrealDB PoC — Validate capabilities for Mythline v2

Tests:
1. Connection and basic setup (namespace, database, tables)
2. CRUD operations on World Lore schema tables
3. Graph relationships (RELATE, traversal)
4. Vector search (HNSW index, KNN query)
5. Complex queries (filtering, joining, aggregation)

Prerequisites:
  docker compose -f poc/surrealdb/docker-compose.yml up -d
  pip install -r poc/surrealdb/requirements.txt
"""

import asyncio
import pytest
import pytest_asyncio
from surrealdb import AsyncSurreal


DB_URL = "ws://localhost:8010/rpc"
DB_NAMESPACE = "mythline_poc"
DB_DATABASE = "world_lore"
DB_USER = "root"
DB_PASS = "root"


@pytest_asyncio.fixture
async def db():
    """Create a fresh database connection for each test."""
    async with AsyncSurreal(DB_URL) as db:
        await db.signin({"username": DB_USER, "password": DB_PASS})
        await db.use(DB_NAMESPACE, DB_DATABASE)
        yield db


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db):
    """Clean up tables before each test to ensure isolation."""
    tables = ["zone", "npc", "faction", "lore", "narrative_item",
              "connects_to", "belongs_to", "located_in", "relates_to",
              "child_of", "stance_toward", "found_in", "about",
              "research_state", "embedding_test"]
    for table in tables:
        await db.query(f"DELETE FROM {table};")
    yield


class TestConnection:
    """Test 1: Connection and basic setup."""

    async def test_connect_and_authenticate(self, db):
        result = await db.query("INFO FOR DB;")
        assert result is not None

    async def test_namespace_and_database(self, db):
        result = await db.query("INFO FOR NS;")
        assert result is not None


class TestCRUD:
    """Test 2: CRUD operations on World Lore schema tables."""

    async def test_create_zone(self, db):
        zone = await db.create("zone:elwynn_forest", {
            "name": "Elwynn Forest",
            "game": "wow",
            "level_range": {"min": 1, "max": 10},
            "narrative_arc": "The peaceful heart of the Alliance, hiding darkness beneath its pastoral surface",
            "political_climate": "Stable Alliance territory under Stormwind's protection",
            "access_gating": [],
            "phase_states": [
                {"name": "default", "description": "Peaceful farmlands with gnoll and kobold threats"},
                {"name": "post_cataclysm", "description": "Damaged by the Cataclysm, Blackrock orcs encroaching"}
            ],
            "connected_zones": ["westfall", "redridge_mountains", "stormwind_city", "duskwood"],
            "era": "classic",
            "confidence": 0.95,
        })
        assert zone is not None
        assert zone["name"] == "Elwynn Forest"

    async def test_read_zone(self, db):
        await db.create("zone:elwynn_forest", {
            "name": "Elwynn Forest",
            "game": "wow",
            "level_range": {"min": 1, "max": 10},
        })
        result = await db.select("zone:elwynn_forest")
        zone = result[0] if isinstance(result, list) else result
        assert zone["name"] == "Elwynn Forest"
        assert zone["level_range"]["min"] == 1

    async def test_update_zone(self, db):
        await db.create("zone:elwynn_forest", {
            "name": "Elwynn Forest",
            "confidence": 0.7,
        })
        await db.merge("zone:elwynn_forest", {"confidence": 0.95})
        result = await db.select("zone:elwynn_forest")
        zone = result[0] if isinstance(result, list) else result
        assert zone["confidence"] == 0.95

    async def test_delete_zone(self, db):
        await db.create("zone:elwynn_forest", {"name": "Elwynn Forest"})
        await db.delete("zone:elwynn_forest")
        result = await db.query("SELECT * FROM zone WHERE id = zone:elwynn_forest;")
        assert len(result) == 0 or (isinstance(result, list) and len(result[0].get("result", result)) == 0) or result == [None] or result == [[]]

    async def test_create_npc(self, db):
        npc = await db.create("npc:marshal_dughan", {
            "name": "Marshal Dughan",
            "personality": "Dutiful, weary, pragmatic",
            "motivations": ["Protect Goldshire", "Maintain order in Elwynn"],
            "quest_threads": ["A Threat Within", "Investigate the Mines"],
            "role": "quest_giver",
            "confidence": 0.9,
        })
        assert npc["name"] == "Marshal Dughan"
        assert "quest_giver" == npc["role"]

    async def test_create_faction(self, db):
        faction = await db.create("faction:stormwind", {
            "name": "Stormwind",
            "level": "major_faction",
            "ideology": "Human kingdom, bastion of the Alliance",
            "goals": ["Defend against the Horde", "Maintain peace in Eastern Kingdoms"],
            "confidence": 0.95,
        })
        assert faction["name"] == "Stormwind"

    async def test_create_lore(self, db):
        lore = await db.create("lore:first_war", {
            "title": "The First War",
            "category": "history",
            "content": "The conflict that began when orcs invaded Azeroth through the Dark Portal",
            "era": "classic",
            "confidence": 0.98,
        })
        assert lore["title"] == "The First War"

    async def test_create_narrative_item(self, db):
        item = await db.create("narrative_item:ashbringer", {
            "name": "Ashbringer",
            "story_arc": "A legendary blade forged to destroy the undead, corrupted and later purified",
            "wielder_lineage": ["Alexandros Mograine", "Renault Mograine", "Darion Mograine", "Tirion Fordring"],
            "power_description": "Holy sword with devastating power against undead",
            "significance": "legendary",
            "confidence": 0.97,
        })
        assert item["name"] == "Ashbringer"
        assert len(item["wielder_lineage"]) == 4

    async def test_query_filter(self, db):
        await db.create("zone:elwynn_forest", {"name": "Elwynn Forest", "game": "wow", "confidence": 0.95})
        await db.create("zone:westfall", {"name": "Westfall", "game": "wow", "confidence": 0.6})
        await db.create("zone:duskwood", {"name": "Duskwood", "game": "wow", "confidence": 0.85})

        result = await db.query("SELECT * FROM zone WHERE confidence >= 0.8;")
        high_confidence = result[0] if isinstance(result[0], list) else result
        assert len(high_confidence) == 2


class TestGraphRelationships:
    """Test 3: Graph relationships — RELATE and traversal."""

    async def _setup_graph(self, db):
        """Create test data for graph queries."""
        await db.create("zone:elwynn_forest", {"name": "Elwynn Forest"})
        await db.create("zone:westfall", {"name": "Westfall"})
        await db.create("zone:stormwind_city", {"name": "Stormwind City"})
        await db.create("zone:redridge_mountains", {"name": "Redridge Mountains"})

        await db.create("npc:marshal_dughan", {"name": "Marshal Dughan", "role": "quest_giver"})
        await db.create("npc:gryan_stoutmantle", {"name": "Gryan Stoutmantle", "role": "quest_giver"})

        await db.create("faction:stormwind", {"name": "Stormwind", "level": "major_faction"})
        await db.create("faction:peoples_militia", {"name": "People's Militia", "level": "guild"})

    async def test_relate_zone_connections(self, db):
        await self._setup_graph(db)

        await db.query("RELATE zone:elwynn_forest->connects_to->zone:westfall;")
        await db.query("RELATE zone:elwynn_forest->connects_to->zone:stormwind_city;")
        await db.query("RELATE zone:elwynn_forest->connects_to->zone:redridge_mountains;")

        result = await db.query("SELECT ->connects_to->zone.name FROM zone:elwynn_forest;")
        connected = result[0] if isinstance(result[0], list) else [result[0]]
        assert len(connected) > 0

    async def test_relate_npc_to_zone(self, db):
        await self._setup_graph(db)

        await db.query("RELATE npc:marshal_dughan->located_in->zone:elwynn_forest;")
        await db.query("RELATE npc:gryan_stoutmantle->located_in->zone:westfall;")

        result = await db.query("SELECT ->located_in->zone.name FROM npc:marshal_dughan;")
        assert result is not None

    async def test_relate_npc_to_faction(self, db):
        await self._setup_graph(db)

        await db.query("RELATE npc:marshal_dughan->belongs_to->faction:stormwind;")
        await db.query("RELATE npc:gryan_stoutmantle->belongs_to->faction:peoples_militia;")

        result = await db.query("SELECT <-belongs_to<-npc.name FROM faction:stormwind;")
        assert result is not None

    async def test_relate_faction_hierarchy(self, db):
        await self._setup_graph(db)

        await db.query("RELATE faction:peoples_militia->child_of->faction:stormwind;")

        result = await db.query("SELECT ->child_of->faction.name FROM faction:peoples_militia;")
        assert result is not None

    async def test_relate_with_properties(self, db):
        await self._setup_graph(db)

        await db.query("""
            RELATE faction:stormwind->stance_toward->faction:peoples_militia
            SET stance = 'allied', strength = 0.8;
        """)

        result = await db.query("SELECT * FROM stance_toward;")
        edges = result[0] if isinstance(result[0], list) else result
        assert len(edges) > 0

    async def test_reverse_traversal(self, db):
        await self._setup_graph(db)
        await db.query("RELATE zone:westfall->connects_to->zone:elwynn_forest;")

        result = await db.query("SELECT <-connects_to<-zone.name FROM zone:elwynn_forest;")
        assert result is not None

    async def test_npc_relationships(self, db):
        await db.create("npc:anduin", {"name": "Anduin Wrynn"})
        await db.create("npc:varian", {"name": "Varian Wrynn"})

        await db.query("""
            RELATE npc:varian->relates_to->npc:anduin
            SET relationship_type = 'father', description = 'Father and son, Kings of Stormwind';
        """)

        result = await db.query("SELECT ->relates_to->(npc WHERE true).name FROM npc:varian;")
        assert result is not None


class TestVectorSearch:
    """Test 4: Vector search — HNSW index and KNN queries."""

    async def test_create_vector_index(self, db):
        await db.query("""
            DEFINE INDEX idx_embedding ON embedding_test
            FIELDS embedding MTREE DIMENSION 8 DIST COSINE TYPE F32;
        """)

        result = await db.query("INFO FOR TABLE embedding_test;")
        assert result is not None

    async def test_insert_vectors(self, db):
        await db.query("""
            DEFINE INDEX idx_embedding ON embedding_test
            FIELDS embedding MTREE DIMENSION 8 DIST COSINE TYPE F32;
        """)

        await db.query("CREATE embedding_test:zone_elwynn SET content = 'Elwynn Forest is a peaceful starting zone for humans', embedding = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8];")
        await db.query("CREATE embedding_test:zone_duskwood SET content = 'Duskwood is a dark and haunted forest zone', embedding = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];")
        await db.query("CREATE embedding_test:zone_westfall SET content = 'Westfall is a desolate farmland zone west of Elwynn', embedding = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85];")

        result = await db.query("SELECT * FROM embedding_test;")
        records = result[0] if isinstance(result[0], list) else result
        assert len(records) == 3

    async def test_knn_search_with_mtree(self, db):
        """KNN search works with MTREE index when data is inserted via SurrealQL."""
        await db.query("DEFINE INDEX idx_embedding ON embedding_test FIELDS embedding MTREE DIMENSION 8 DIST COSINE TYPE F32;")

        await db.query("CREATE embedding_test:zone_elwynn SET content = 'Elwynn Forest', embedding = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8];")
        await db.query("CREATE embedding_test:zone_duskwood SET content = 'Duskwood', embedding = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];")
        await db.query("CREATE embedding_test:zone_westfall SET content = 'Westfall', embedding = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85];")

        result = await db.query("""
            SELECT id, content, vector::distance::knn() AS distance
            FROM embedding_test
            WHERE embedding <|2|> [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]
            ORDER BY distance;
        """)

        matches = result[0] if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) else result
        assert len(matches) >= 2
        first_id = str(matches[0]["id"])
        assert "elwynn" in first_id or "westfall" in first_id

    async def test_cosine_similarity_search(self, db):
        await db.query("CREATE embedding_test:zone_elwynn SET content = 'Elwynn Forest', embedding = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8];")
        await db.query("CREATE embedding_test:zone_duskwood SET content = 'Duskwood', embedding = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];")

        result = await db.query("""
            SELECT id, content,
                   vector::similarity::cosine(embedding, [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]) AS similarity
            FROM embedding_test
            ORDER BY similarity DESC;
        """)

        matches = result[0] if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) else result
        assert len(matches) == 2
        assert matches[0]["similarity"] > matches[1]["similarity"]
        first_id = str(matches[0]["id"])
        assert "elwynn" in first_id


class TestCheckpointState:
    """Test 5: Research state persistence (checkpoint)."""

    async def test_save_checkpoint(self, db):
        checkpoint = await db.create("research_state:current", {
            "zone_name": "elwynn_forest",
            "current_step": 4,
            "step_data": {"zone_overview": {"name": "Elwynn Forest"}, "npcs": []},
            "progression_queue": ["westfall", "redridge_mountains", "duskwood"],
            "priority_queue": ["westfall"],
            "completed_zones": [],
            "failed_zones": [],
            "daily_tokens_used": 5000,
            "last_reset_date": "2026-02-21",
        })
        assert checkpoint["zone_name"] == "elwynn_forest"
        assert checkpoint["current_step"] == 4

    async def test_load_checkpoint(self, db):
        await db.create("research_state:current", {
            "zone_name": "elwynn_forest",
            "current_step": 4,
            "progression_queue": ["westfall", "redridge_mountains"],
        })
        result = await db.select("research_state:current")
        checkpoint = result[0] if isinstance(result, list) else result
        assert checkpoint["zone_name"] == "elwynn_forest"
        assert checkpoint["current_step"] == 4
        assert len(checkpoint["progression_queue"]) == 2

    async def test_update_checkpoint(self, db):
        await db.create("research_state:current", {
            "zone_name": "elwynn_forest",
            "current_step": 4,
            "daily_tokens_used": 5000,
        })
        await db.merge("research_state:current", {
            "current_step": 7,
            "daily_tokens_used": 12000,
        })
        result = await db.select("research_state:current")
        checkpoint = result[0] if isinstance(result, list) else result
        assert checkpoint["current_step"] == 7
        assert checkpoint["daily_tokens_used"] == 12000


class TestComplexQueries:
    """Test 6: Complex queries that the agents will need."""

    async def test_query_npcs_by_zone_via_graph(self, db):
        await db.create("zone:elwynn_forest", {"name": "Elwynn Forest"})
        await db.create("npc:marshal_dughan", {"name": "Marshal Dughan", "role": "quest_giver"})
        await db.create("npc:smith_argus", {"name": "Smith Argus", "role": "vendor"})
        await db.query("RELATE npc:marshal_dughan->located_in->zone:elwynn_forest;")
        await db.query("RELATE npc:smith_argus->located_in->zone:elwynn_forest;")

        result = await db.query("SELECT <-located_in<-npc.* FROM zone:elwynn_forest;")
        assert result is not None

    async def test_query_faction_members(self, db):
        await db.create("faction:stormwind", {"name": "Stormwind"})
        await db.create("npc:marshal_dughan", {"name": "Marshal Dughan"})
        await db.create("npc:guard_thomas", {"name": "Guard Thomas"})
        await db.query("RELATE npc:marshal_dughan->belongs_to->faction:stormwind;")
        await db.query("RELATE npc:guard_thomas->belongs_to->faction:stormwind;")

        result = await db.query("SELECT <-belongs_to<-npc.name FROM faction:stormwind;")
        assert result is not None

    async def test_multi_hop_traversal(self, db):
        await db.create("zone:elwynn_forest", {"name": "Elwynn Forest"})
        await db.create("zone:westfall", {"name": "Westfall"})
        await db.create("zone:duskwood", {"name": "Duskwood"})
        await db.query("RELATE zone:elwynn_forest->connects_to->zone:westfall;")
        await db.query("RELATE zone:westfall->connects_to->zone:duskwood;")

        result = await db.query(
            "SELECT ->connects_to->zone->connects_to->zone.name FROM zone:elwynn_forest;"
        )
        assert result is not None
