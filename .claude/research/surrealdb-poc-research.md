# SurrealDB PoC Research

**Date:** 2026-02-21
**Purpose:** Evaluate SurrealDB for Mythline v2 as a unified database (document + graph + vector)

---

## 1. SurrealDB Docker Image

### Latest Version

- **SurrealDB v3.0.0** released Feb 17, 2026 (major release)
- **SurrealDB v2.6.2** released Feb 16, 2026 (latest v2.x patch)
- Docker image: `surrealdb/surrealdb`

**Important:** v3.0.0 is brand new (4 days old). For a PoC, we should use `v2.6.2` for stability unless we specifically need v3 features. The Python SDK (v1.0.8) documents compatibility with v2.0.0 to v2.3.6; v3.0 SDK support status is unconfirmed.

### Docker Run Commands

**In-memory (simplest for PoC dev):**
```bash
docker run --rm --pull always --name surrealdb \
  -p 8000:8000 \
  surrealdb/surrealdb:v2.6.2 start \
  --log trace --user root --pass root memory
```

**Persistent storage with RocksDB:**
```bash
docker run --rm --pull always --name surrealdb \
  -p 8000:8000 \
  -v surrealdb_data:/data \
  surrealdb/surrealdb:v2.6.2 start \
  --log info --user root --pass root \
  rocksdb:/data/mythline.db
```

**Persistent storage with SurrealKV (native engine):**
```bash
docker run --rm --pull always --name surrealdb \
  -p 8000:8000 \
  -v surrealdb_data:/data \
  surrealdb/surrealdb:v2.6.2 start \
  --log info --user root --pass root \
  surrealkv:/data/mythline.db
```

### Docker Compose (recommended for PoC)

```yaml
version: "3.8"
services:
  surrealdb:
    image: surrealdb/surrealdb:v2.6.2
    container_name: mythline-surrealdb
    ports:
      - "8000:8000"
    volumes:
      - surrealdb_data:/data
    command: start --log info --user root --pass root surrealkv:/data/mythline.db
    restart: unless-stopped

volumes:
  surrealdb_data:
```

### Key Config Options

| Flag | Purpose | Example |
|------|---------|---------|
| `--user` | Root username | `--user root` |
| `--pass` | Root password | `--pass root` |
| `--log` | Log level | `--log trace/debug/info/warn/error` |
| `--bind` | Bind address | `--bind 0.0.0.0:8000` (default) |
| `--unauthenticated` | Disable auth | For dev only |
| `memory` | In-memory storage | No persistence |
| `rocksdb:/path` | RocksDB storage | Disk-based, proven |
| `surrealkv:/path` | SurrealKV storage | Native engine |

### Port

SurrealDB exposes a single port: **8000** (HTTP + WebSocket on same port).

---

## 2. SurrealDB Python SDK

### Package Info

| Property | Value |
|----------|-------|
| Package name | `surrealdb` |
| Latest version | **1.0.8** (Jan 7, 2026) |
| Status | Production/Stable |
| Python versions | 3.9, 3.10, 3.11, 3.12, 3.13 |
| Install | `pip install surrealdb` |
| SurrealDB compat | v2.0.0 to v2.3.6 (documented) |

### Stability Assessment

- 18 total releases since Sep 2022
- At v1.0.x since early 2025 -- stable release line
- Official SDK maintained by SurrealDB team
- Uses pre-built Rust bindings (wheels on PyPI)
- Production/Stable status on PyPI

### Async Support

Full async/await support via `AsyncSurreal` class. Identical API to sync `Surreal`.

### Connection Protocols

| Protocol | URI Format | Sessions | Transactions |
|----------|-----------|----------|--------------|
| WebSocket | `ws://localhost:8000/rpc` | Yes | Yes |
| WebSocket (TLS) | `wss://localhost:8000/rpc` | Yes | Yes |
| HTTP | `http://localhost:8000` | No | No |
| HTTP (TLS) | `https://localhost:8000` | No | No |
| Embedded memory | `memory` or `mem://` | No | No |
| Embedded file | `file://path` | No | No |
| Embedded SurrealKV | `surrealkv://path` | No | No |

**For Mythline PoC:** Use `ws://localhost:8000/rpc` for full feature support.

### Basic CRUD API

**Sync usage:**
```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000/rpc") as db:
    db.signin({"username": "root", "password": "root"})
    db.use("mythline", "stories")

    # CREATE
    story = db.create("story", {
        "title": "The Fall of Shadowglen",
        "genre": "dark_fantasy",
        "status": "draft"
    })

    # CREATE with specific ID
    db.create("story:shadowglen", {
        "title": "The Fall of Shadowglen"
    })

    # SELECT all from table
    stories = db.select("story")

    # SELECT specific record
    story = db.select("story:shadowglen")

    # UPDATE (replaces entire record)
    db.update("story:shadowglen", {
        "title": "The Fall of Shadowglen",
        "status": "published"
    })

    # MERGE (partial update)
    db.merge("story:shadowglen", {"status": "published"})

    # DELETE
    db.delete("story:shadowglen")

    # RAW QUERY (SurrealQL)
    result = db.query("SELECT * FROM story WHERE status = $status", {
        "status": "draft"
    })
```

**Async usage:**
```python
import asyncio
from surrealdb import AsyncSurreal

async def main():
    async with AsyncSurreal("ws://localhost:8000/rpc") as db:
        await db.signin({"username": "root", "password": "root"})
        await db.use("mythline", "stories")

        story = await db.create("story", {
            "title": "The Fall of Shadowglen",
            "genre": "dark_fantasy"
        })

        stories = await db.select("story")

        result = await db.query(
            "SELECT * FROM story WHERE genre = $genre",
            {"genre": "dark_fantasy"}
        )

asyncio.run(main())
```

### All SDK Methods

| Method | Purpose |
|--------|---------|
| `db.signin(credentials)` | Authenticate |
| `db.signup(credentials)` | Register (scope auth) |
| `db.invalidate()` | Clear auth |
| `db.authenticate(token)` | Validate JWT |
| `db.use(namespace, database)` | Select namespace/database |
| `db.info()` | Get authenticated user info |
| `db.let(key, value)` | Set connection variable |
| `db.unset(key)` | Remove connection variable |
| `db.query(sql, vars)` | Execute SurrealQL |
| `db.select(thing)` | Read records |
| `db.create(thing, data)` | Insert record |
| `db.insert(thing, data)` | Insert one or many |
| `db.update(thing, data)` | Replace record |
| `db.merge(thing, data)` | Partial update |
| `db.patch(thing, data)` | JSON Patch update |
| `db.delete(thing)` | Delete record |
| `db.live(table, diff)` | Start live query |
| `db.subscribe_live(uuid)` | Subscribe to live query |
| `db.kill(uuid)` | Stop live query |
| `db.close()` | Close connection |

### Known SDK Bug

**Issue #232 (Feb 12, 2026):** `query()` silently discards results from multi-statement queries and transactions. This means if you send multiple SurrealQL statements in a single `query()` call, only partial results may be returned.

**Workaround:** Execute one statement per `query()` call, or use raw WebSocket.

---

## 3. Vector Search

### Native Support

SurrealDB has native vector search built-in. No external vector DB needed.

### Defining Vector Fields and Indexes

```sql
-- Define a table with an embedding field
DEFINE TABLE knowledge SCHEMAFULL;
DEFINE FIELD content ON knowledge TYPE string;
DEFINE FIELD embedding ON knowledge TYPE array<float>;
DEFINE FIELD source ON knowledge TYPE string;

-- Create HNSW vector index
DEFINE INDEX idx_knowledge_embedding ON knowledge
  FIELDS embedding
  HNSW DIMENSION 1536         -- OpenAI text-embedding-3-small dimension
  DIST COSINE                  -- Distance metric
  TYPE F32;                    -- 32-bit float (good balance of speed/precision)
```

### HNSW Index Parameters

| Parameter | Default | Options | Notes |
|-----------|---------|---------|-------|
| DIMENSION | required | Any positive int | Must match embedding model output |
| DIST | EUCLIDEAN | EUCLIDEAN, COSINE, MANHATTAN, CHEBYSHEV, HAMMING, MINKOWSKI | COSINE for text embeddings |
| TYPE | F64 | F64, F32, I64, I32, I16 | F32 recommended for embeddings |
| EFC | 150 | int | Construction effort (higher = better quality, slower build) |
| M | 12 | int | Max connections per element |
| M0 | 24 | int | Max connections in lowest layer |

### Embedding Dimensions

No strict limitation. Use whatever your embedding model produces:
- OpenAI `text-embedding-3-small`: 1536
- OpenAI `text-embedding-3-large`: 3072
- OpenAI `text-embedding-ada-002`: 1536
- Sentence Transformers (various): 384, 768, 1024

### Vector Search Queries

**KNN search using HNSW index:**
```sql
LET $query_embedding = [0.012, -0.034, 0.056, ...];  -- 1536-dim vector

SELECT
    id,
    content,
    source,
    vector::distance::knn() AS distance
FROM knowledge
WHERE embedding <|5|> $query_embedding
ORDER BY distance;
```

The `<|K|>` operator returns K nearest neighbors. With HNSW index, this is fast.

**KNN with effort parameter:**
```sql
-- <|K, EF|> where EF controls search thoroughness
SELECT id, content, vector::distance::knn() AS distance
FROM knowledge
WHERE embedding <|10, 100|> $query_embedding
ORDER BY distance;
```

Higher EF = more accurate but slower. Default is index's EFC value.

**KNN with additional filtering:**
```sql
SELECT id, content, vector::distance::knn() AS distance
FROM knowledge
WHERE source = "wowpedia"
  AND embedding <|5|> $query_embedding
ORDER BY distance;
```

**Brute force (no index needed):**
```sql
SELECT id, content,
    vector::distance::cosine(embedding, $query_embedding) AS distance
FROM knowledge
WHERE vector::distance::cosine(embedding, $query_embedding) < 0.3
ORDER BY distance;
```

### Distance/Similarity Functions

**Distance (lower = more similar):**
- `vector::distance::euclidean(a, b)`
- `vector::distance::cosine(a, b)`
- `vector::distance::manhattan(a, b)`
- `vector::distance::hamming(a, b)`
- `vector::distance::chebyshev(a, b)`
- `vector::distance::minkowski(a, b, p)`
- `vector::distance::knn()` -- uses index distance metric

**Similarity (higher = more similar):**
- `vector::similarity::cosine(a, b)`
- `vector::similarity::jaccard(a, b)`
- `vector::similarity::pearson(a, b)`

### Hybrid Search (Vector + Full-Text)

```sql
-- Define full-text index
DEFINE ANALYZER simple TOKENIZERS class FILTERS lowercase, ascii;
DEFINE INDEX idx_content ON knowledge FIELDS content FULLTEXT ANALYZER simple BM25;

-- Define vector index
DEFINE INDEX idx_embedding ON knowledge FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;

-- Hybrid search with reciprocal rank fusion
LET $query_vec = [0.012, -0.034, ...];
LET $vector_results = SELECT id FROM knowledge WHERE embedding <|10, 100|> $query_vec;
LET $text_results = SELECT id FROM knowledge WHERE content @1@ 'Shadowglen lore' LIMIT 10;

search::rrf([$vector_results, $text_results], 10, 60);
```

### Verify Index Usage

```sql
SELECT id FROM knowledge WHERE embedding <|10|> $query_vec EXPLAIN FULL;
```

---

## 4. Graph Relationships

### RELATE Syntax

```sql
-- Basic relationship
RELATE person:thrall->leads->faction:horde;

-- With properties on the edge
RELATE npc:thrall->gives_quest->quest:elemental_bonds
  SET level_required = 80, zone = "Deepholm";

-- With CONTENT block
RELATE quest:elemental_bonds->rewards->item:heart_of_azeroth
  CONTENT {
    quantity: 1,
    bonus_chance: 0.15
  };
```

### Graph Traversal

**Forward traversal (->):**
```sql
-- What quests does Thrall give?
SELECT ->gives_quest->quest.* FROM npc:thrall;

-- Direct (no SELECT needed)
npc:thrall->gives_quest->quest;
```

**Reverse traversal (<-):**
```sql
-- Who gives this quest?
SELECT <-gives_quest<-npc.* FROM quest:elemental_bonds;
```

**Bidirectional (<->):**
```sql
-- All allies (regardless of direction)
SELECT <->allied_with<->faction.* FROM faction:horde;
```

**Multi-hop traversal:**
```sql
-- NPCs -> quests -> rewards
SELECT ->gives_quest->quest->rewards->item.* FROM npc:thrall;
```

**Filtering edges:**
```sql
-- Only high-level quests
SELECT ->gives_quest(WHERE level_required >= 60)->quest.* FROM npc:thrall;
```

**Projections on traversal:**
```sql
SELECT id, name, quests: ->gives_quest->quest.{id, title, zone} FROM npc;
```

### Recursive Queries (v2.1+)

```sql
-- Depth-limited: get quest chain 3 levels deep
SELECT
    @.{1}->leads_to->quest AS step_2,
    @.{2}->leads_to->quest AS step_3,
    @.{3}->leads_to->quest AS step_4
FROM ONLY quest:first_quest;

-- Recursive with nested structure
SELECT @.{3}.{
    id,
    title,
    next: ->leads_to->quest.@
} FROM quest:first_quest;
```

### Defining Relation Tables (Schema)

```sql
-- Define typed relations for data integrity
DEFINE TABLE gives_quest TYPE RELATION IN npc OUT quest;
DEFINE FIELD level_required ON gives_quest TYPE int;
DEFINE FIELD zone ON gives_quest TYPE string;

DEFINE TABLE leads_to TYPE RELATION IN quest OUT quest;
DEFINE FIELD prerequisite ON leads_to TYPE bool DEFAULT true;

DEFINE TABLE rewards TYPE RELATION IN quest OUT item;
DEFINE FIELD quantity ON rewards TYPE int DEFAULT 1;
```

### Computed Fields from Graph

```sql
-- Auto-compute quest givers
DEFINE FIELD quest_giver ON quest COMPUTED <-gives_quest<-npc;

-- Auto-compute quest chain next steps
DEFINE FIELD next_quests ON quest COMPUTED ->leads_to->quest;
```

### Preventing Duplicate Relations

```sql
DEFINE FIELD key ON TABLE allied_with VALUE <string>array::sort([in, out]);
DEFINE INDEX unique_alliance ON allied_with FIELDS key UNIQUE;
```

### Edge Deletion Behavior

Graph edges auto-delete when either linked record is deleted. No orphaned edges.

---

## 5. Known Issues & Windows Considerations

### Python SDK Issues

1. **Issue #232 (Critical):** `query()` silently discards results from multi-statement queries. **Workaround:** One statement per `query()` call.

2. **Sessions/Transactions:** Only work over WebSocket (`ws://`). HTTP and embedded connections raise `NotImplementedError`.

3. **IF EXISTS / IF NOT EXISTS:** Not available in SDK DEFINE statements (v1.x known issue). Workaround: Use raw SurrealQL via `query()`.

4. **DELETE ONLY clause fails** (v1.x). Workaround: Add `RETURN $before` to the DELETE statement.

5. **Open feature requests (7 total, low bug count):**
   - Connection pooling not yet supported (#170)
   - No OpenTelemetry tracing (#219)
   - No custom TLS certificate verification (#107)

### Windows-Specific

- No Windows-specific bugs documented in the Python SDK GitHub issues.
- Docker image runs normally on Windows via Docker Desktop.
- Python SDK marked as "OS Independent" on PyPI.
- The SDK uses pre-built Rust wheels which include Windows builds.
- Embedded mode (`file://`, `surrealkv://`) paths on Windows: use forward slashes in the URI (`surrealkv://C:/data/mythline.db`) or relative paths.

### SurrealDB v3.0.0 Considerations

- Released Feb 17, 2026 (4 days ago). Very new.
- Breaking changes from v2.x: function renames, schema changes, parameter declaration requires `LET`.
- Python SDK v1.0.8 documents compatibility with v2.0.0 to v2.3.6.
- **Recommendation for PoC: Use v2.6.2 Docker image with Python SDK v1.0.8.**
- v3.0 notable features for future: context graphs, WASM extensions for AI model integration, GraphQL support, file storage.

### Alternative Python Client

If the official SDK has issues, `surrealist` (community package) is available:
- PyPI: `pip install surrealist`
- GitHub: github.com/kotolex/surrealist
- Pure Python, no Rust bindings
- May be more debuggable

---

## Summary Assessment for Mythline PoC

| Capability | Status | Notes |
|-----------|--------|-------|
| Docker deployment | Ready | Single container, port 8000 |
| Python SDK (sync) | Stable | v1.0.8, full CRUD |
| Python SDK (async) | Stable | AsyncSurreal, identical API |
| Vector search (HNSW) | Native | Any dimension, COSINE/EUCLIDEAN/etc |
| Graph relationships | Native | RELATE, traversal, recursive queries |
| Hybrid search | Supported | Vector + full-text via RRF |
| Windows compat | Good | No known issues |
| Maturity risk | Low-Medium | v2.6.2 is stable; SDK multi-query bug exists |

### Recommended PoC Stack

```
SurrealDB v2.6.2 (Docker) + surrealdb v1.0.8 (Python) + WebSocket connection
```

This gives us document storage, graph relationships, AND vector search in a single database -- replacing the need for separate Qdrant + graph DB + document DB.

---

## 6. PoC Validation Results (2026-02-21)

**Decision: PASS — SurrealDB is validated for Mythline v2**

### Test Summary

28/28 tests passing across 6 test classes:

| Test Class | Tests | Status | Notes |
|------------|-------|--------|-------|
| TestConnection | 2 | PASS | WebSocket auth, namespace/db selection |
| TestCRUD | 9 | PASS | All 5 table types + query filter |
| TestGraphRelationships | 7 | PASS | RELATE, traversal, reverse, multi-hop |
| TestVectorSearch | 4 | PASS | MTREE index, KNN, cosine similarity |
| TestCheckpointState | 3 | PASS | Save, load, update checkpoint |
| TestComplexQueries | 3 | PASS | Graph-based NPC/faction queries, multi-hop |

### Key Findings

1. **`select()` returns a list, not a dict.** Must use `result[0] if isinstance(result, list) else result` when expecting a single record.

2. **HNSW index KNN returns empty results.** On small datasets in memory mode, HNSW KNN (`<|K|>`) returns nothing. Not a blocker — MTREE index works correctly for KNN.

3. **MTREE index works for KNN search.** Use `DEFINE INDEX ... MTREE DIMENSION N DIST COSINE TYPE F32` instead of HNSW for reliable KNN on small-to-medium datasets.

4. **`vector::similarity::cosine()` works without any index.** Brute-force similarity search is reliable and can serve as fallback for small collections.

5. **Python SDK `create()` may not trigger vector index.** Data inserted via `db.create()` is not always searchable via KNN. Use `db.query()` with SurrealQL `CREATE` statements for vector-indexed data.

6. **Issue #232 confirmed.** Multi-statement `query()` calls lose results. One statement per call.

7. **Port 8000 conflict.** Changed to port 8010 for PoC since v1 MCP servers use 8000. Production docker-compose will assign unique ports.

### Architecture Implications

- Use **MTREE** (not HNSW) for vector indexes in the Storage MCP schema definitions
- Use **`db.query()` with SurrealQL** for all vector-indexed inserts (not `db.create()`)
- Use **one statement per `query()` call** to avoid issue #232
- Wrap `select()` results with list-to-single-record helper
- SurrealDB replaces both Qdrant (vector) and any separate graph DB — single unified backend
