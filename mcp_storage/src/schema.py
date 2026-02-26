"""SurrealDB schema initialization for the World Lore domain."""

from src.db import get_db

SCHEMA_STATEMENTS = [
    # --- Tables ---
    "DEFINE TABLE IF NOT EXISTS zone SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS npc SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS faction SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS lore SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS narrative_item SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS research_state SCHEMALESS",

    # --- Graph relation tables ---
    "DEFINE TABLE IF NOT EXISTS connects_to TYPE RELATION IN zone OUT zone",
    "DEFINE TABLE IF NOT EXISTS belongs_to TYPE RELATION IN npc OUT faction",
    "DEFINE TABLE IF NOT EXISTS located_in TYPE RELATION IN npc OUT zone",
    "DEFINE TABLE IF NOT EXISTS relates_to TYPE RELATION IN npc OUT npc",
    "DEFINE TABLE IF NOT EXISTS child_of TYPE RELATION IN faction OUT faction",
    "DEFINE TABLE IF NOT EXISTS stance_toward TYPE RELATION IN faction OUT faction",
    "DEFINE TABLE IF NOT EXISTS found_in TYPE RELATION IN narrative_item OUT zone",
    "DEFINE TABLE IF NOT EXISTS about TYPE RELATION IN lore OUT zone",

    # --- Wiki Crawler tables ---
    "DEFINE TABLE IF NOT EXISTS crawl_zone SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS crawl_page SCHEMALESS",
    "DEFINE TABLE IF NOT EXISTS crawl_domain SCHEMALESS",

    # --- Wiki Crawler relation tables ---
    "DEFINE TABLE IF NOT EXISTS has_page TYPE RELATION IN crawl_zone OUT crawl_page",
    "DEFINE TABLE IF NOT EXISTS connected_to TYPE RELATION IN crawl_zone OUT crawl_zone",
    "DEFINE TABLE IF NOT EXISTS links_to TYPE RELATION IN crawl_page OUT crawl_page",
    "DEFINE TABLE IF NOT EXISTS from_domain TYPE RELATION IN crawl_page OUT crawl_domain",

    # --- Wiki Crawler indexes ---
    "DEFINE INDEX IF NOT EXISTS idx_crawl_zone_status ON crawl_zone FIELDS status",
    "DEFINE INDEX IF NOT EXISTS idx_crawl_zone_crawled_at ON crawl_zone FIELDS crawled_at",
    "DEFINE INDEX IF NOT EXISTS idx_crawl_page_url ON crawl_page FIELDS url UNIQUE",
    "DEFINE INDEX IF NOT EXISTS idx_crawl_page_type ON crawl_page FIELDS page_type",
    "DEFINE INDEX IF NOT EXISTS idx_crawl_page_domain ON crawl_page FIELDS domain",

    # --- Vector indexes (MTREE, validated in PoC) ---
    "DEFINE INDEX IF NOT EXISTS idx_zone_embedding ON zone FIELDS embedding MTREE DIMENSION 1536 DIST COSINE TYPE F32",
    "DEFINE INDEX IF NOT EXISTS idx_npc_embedding ON npc FIELDS embedding MTREE DIMENSION 1536 DIST COSINE TYPE F32",
    "DEFINE INDEX IF NOT EXISTS idx_faction_embedding ON faction FIELDS embedding MTREE DIMENSION 1536 DIST COSINE TYPE F32",
    "DEFINE INDEX IF NOT EXISTS idx_lore_embedding ON lore FIELDS embedding MTREE DIMENSION 1536 DIST COSINE TYPE F32",
    "DEFINE INDEX IF NOT EXISTS idx_narrative_item_embedding ON narrative_item FIELDS embedding MTREE DIMENSION 1536 DIST COSINE TYPE F32",
]


async def initialize_schema() -> None:
    """Create all tables, relation tables, and vector indexes.

    Uses IF NOT EXISTS so this is safe to call on every startup.
    Statements are executed one at a time per SurrealDB SDK issue #232.
    """
    db = await get_db()
    for statement in SCHEMA_STATEMENTS:
        await db.query(statement)
