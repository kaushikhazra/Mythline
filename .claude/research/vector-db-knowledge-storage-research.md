# Vector Database & Knowledge Storage Research

## Date: 2026-02-21
## Context: Mythline v2 Architecture - Storage MCP Technology Selection

---

## Use Case Summary

Single Storage MCP service backing 5 knowledge domain collections:

| Domain | Nature | Access Pattern | Shape |
|--------|--------|---------------|-------|
| World Lore | Shared, mostly static, era-versioned | Semantic search + structured filter (zone, faction, NPC by name/type) | Graph-shaped (NPCs relate to factions, zones contain NPCs) |
| Quest Lore | Shared, structured | Structured queries (by quest ID, chain, prereqs) + semantic | Tree/DAG-shaped (quest chains, prerequisites) |
| Character | Per-character, evolving | CRUD + structured queries (by character, by field) + some semantic | Document-shaped with nested graph (reputation graph) |
| Dynamics | Computed, ephemeral | Assembled at scene time from Character + World + History | Computed/assembled, not stored long-term |
| Narrative History | Per-character, cumulative | Semantic search + structured (by scene, by NPC, by thread status) | Document-shaped with cross-references |

Scale: ~thousands of documents, not millions. Local-only (Windows 11). Must be wrappable as a single MCP service.

---

## v1 Baseline: What We Had

Qdrant in local/embedded mode (`QdrantClient(path=...)`) with:
- Multiple collections derived from directory names
- Simple payload structure: text, source_file, section_header, chunk_index
- Pure vector search (no structured filtering used)
- Separate stories collection with richer payloads (story_title, quest_ids, npcs, phase, section)
- Context manager pattern for client lifecycle
- 1536-dimension OpenAI embeddings, cosine distance

**v1 Pain Points:**
- No structured queries (everything was semantic-only)
- No graph relationships between entities
- No update/delete granularity (only full re-index)
- Single flat chunk model -- no entity-level storage
- No cross-collection relationships

---

## Technology Evaluation

### 1. Qdrant (Current - v1 incumbent)

**What's New (2025-2026):**
- Score-Boosting Reranking for tunable relevance
- Full-Text Filtering with native multilingual tokenization and stemming
- ACORN algorithm for higher-quality filtered HNSW queries
- 2026 roadmap: 4-bit quantization, read-write segregation, advanced relevance feedback, scalable multitenancy
- Sparse vector support (BM25 via FastEmbed) for true hybrid search
- Named vectors: a single point can carry both dense AND sparse vectors

**Multi-Collection:** YES. Multiple collections per instance. Local mode stores collections in a dictionary. Single `QdrantClient(path=...)` manages all.

**Hybrid Search:** YES (since 2024). Dense + sparse vectors in same collection. RRF fusion. Also supports payload filtering during vector search (numeric ranges, text match, nested filters, datetime, geo).

**Structured Queries:** GOOD. Payload filtering with must/should/must_not conditions. Supports: match (exact), range (numeric/datetime), full-text match, nested object filtering, geo filtering. Payload indexing for performance. But it is NOT SQL -- you cannot do arbitrary joins or aggregations.

**Python SDK:** Excellent. `qdrant-client` is mature, well-documented, type-hinted. Local mode works via `QdrantClient(path=...)` or `QdrantClient(":memory:")`.

**Local/Embedded:** YES. Pure Python local mode, no server needed. Single-process limitation (one client at a time per path). For concurrent access, need Qdrant server (Docker).

**Performance at our scale:** Overkill for thousands of docs, but runs fine. Local mode is slower than server mode but adequate.

**CRUD:** Full support -- upsert points, update payloads (set_payload, overwrite_payload), delete points by ID or filter. Async write-ahead log.

**Maturity:** High. Production-grade, large community, active development, well-funded company.

**MCP Wrappable:** Already done in v1. Straightforward.

**Limitations:**
- Not a graph database -- no traversal queries
- Local mode is single-process (no concurrent MCP + agent access from different processes)
- Payload filtering is powerful but not SQL-level flexibility
- No native graph relationships between collections

**Verdict:** Strong choice for vector + structured. Falls short for graph-shaped data (World Lore relationships, Character reputation graph). Would need a separate graph layer.

---

### 2. ChromaDB

**Multi-Collection:** YES. Create/get/delete collections via client API.

**Hybrid Search:** PARTIAL. Supports metadata filtering on vector queries (where clauses with operators). 2025 Rust-core rewrite added 4x performance. Supports full-text search via Chroma Cloud, but the open-source embedded version's full-text search is more limited.

**Structured Queries:** BASIC. Where clauses with $and, $or, $eq, $ne, $gt, $lt, $gte, $lte, $in, $nin. No nested object filtering. No datetime-specific handling. No range queries as expressive as Qdrant's.

**Python SDK:** Good. Very Pythonic, NumPy-like API. Simple to learn. `pip install chromadb` and go.

**Local/Embedded:** YES. Default mode is embedded. Persistent storage via `PersistentClient(path=...)`.

**Performance at our scale:** Fine. Designed for < 10M vectors. Our thousands are well within range.

**CRUD:** Basic. Add, query, update, delete by ID. Update metadata via `collection.update()`.

**Maturity:** Medium. Popular for prototyping and learning. Not as battle-tested as Qdrant for production. Company pivoting toward cloud offering (Chroma Cloud).

**MCP Wrappable:** Easy. Similar pattern to v1 Qdrant wrapper.

**Limitations:**
- Less sophisticated filtering than Qdrant
- No sparse vector support (no native BM25 hybrid)
- Weaker at structured queries -- no nested filtering, no datetime ranges
- Company focus shifting to cloud product
- Not a graph database

**Verdict:** Simpler than Qdrant but strictly less capable. We would be downgrading from v1. No compelling reason to switch.

---

### 3. LanceDB

**Multi-Collection:** YES. Called "tables" not "collections". `db.create_table()`, `db.open_table()`, `db.table_names()`.

**Hybrid Search:** YES. Native BM25 full-text search + vector search with RRF fusion. `query_type="hybrid"` or `query_type="auto"`. Full-text search index (FTS) built on Lance format.

**Structured Queries:** GOOD. SQL-like `.where()` clauses: `"date > '2025-01-01' AND category = 'lore'"`. Supports comparison operators, AND/OR, string matching. Built on Apache Arrow, so column-typed data with bitmap indices. More SQL-like than Qdrant's filter DSL.

**Python SDK:** Good. Pandas/Polars integration. Arrow-native. `pip install lancedb`. Async API available. Schema defined via PyArrow or Pydantic models.

**Local/Embedded:** YES. Fully embedded, SQLite-like. No server process. `lancedb.connect("path/to/db")`. Zero external dependencies for the core.

**Performance at our scale:** Excellent for our scale. Designed to scale from embedded to billions, but the embedded mode is fast for small data too. Lance columnar format is efficient.

**CRUD:** Full. `table.add()`, `table.update()`, `table.delete()`, `table.search()`. Update supports SQL-like WHERE conditions. Delete supports filter conditions.

**Maturity:** Medium-High. Growing rapidly. Backed by LanceDB Inc (formerly ETO). Active GitHub, good documentation. Used in production at several companies.

**MCP Wrappable:** Easy. Similar complexity to Qdrant wrapper. Pure Python, embedded.

**Limitations:**
- Not a graph database
- Full-text search maturity is behind Qdrant's (BM25 support is newer)
- Fewer community resources than Qdrant
- Schema evolution needs care (Lance format versioning)
- No native graph traversal

**Verdict:** Strong contender. The SQL-like WHERE clauses and Pydantic schema support are attractive for structured queries. True hybrid search (BM25 + vector). Embedded with no server overhead. The weakest point vs Qdrant is community size and maturity, but the feature set is compelling.

---

### 4. Milvus / Milvus Lite

**Multi-Collection:** YES. Full collection management.

**Hybrid Search:** YES. Dense + sparse vectors. BM25 support.

**Structured Queries:** YES. Expression-based filtering.

**Python SDK:** Good. `pymilvus` package.

**Local/Embedded:** YES via Milvus Lite. `MilvusClient("milvus.db")` for embedded mode. Data stored in SQLite file.

**Performance at our scale:** Documentation explicitly says "only suitable for small scale prototyping (usually less than a million vectors)." Our scale fits.

**CRUD:** Full CRUD operations.

**Maturity:** HIGH for full Milvus. Milvus Lite is more of a dev/test tool. Full Milvus requires Docker/k8s.

**MCP Wrappable:** Yes, via Milvus Lite.

**Limitations:**
- Milvus Lite is explicitly a prototyping tool, not for production
- No partitions in Lite mode
- No user/role management in Lite
- Full Milvus is heavy (requires Docker, etcd, MinIO)
- Massive overkill for our scale
- Not a graph database

**Verdict:** Overkill. Full Milvus is a distributed system for massive scale. Milvus Lite is positioned as a toy/prototype. Neither fits our "local production service" use case well.

---

### 5. Weaviate

**Multi-Collection:** YES. Called "classes" or "collections". Full CRUD per collection.

**Hybrid Search:** EXCELLENT. Best-in-class hybrid search combining BM25 + vector with configurable alpha parameter and fusion methods (RankedFusion, RelativeScoreFusion). This is Weaviate's flagship feature.

**Structured Queries:** GOOD. GraphQL-based queries with where filters. Supports operators, cross-references between collections (proto-graph).

**Python SDK:** Good. v4 client is well-designed. Type-hinted, async support.

**Local/Embedded:** PARTIAL. Embedded mode exists BUT:
  - **NOT supported on Windows.** Linux and macOS only.
  - Requires downloading binary packages
  - Docker is the recommended approach for local use

**CRITICAL BLOCKER: No Windows embedded support.** Our environment is Windows 11.

**Performance at our scale:** Fine, but requires Docker or WSL on Windows.

**CRUD:** Full CRUD with batch operations.

**Maturity:** HIGH. Well-funded, large community, production-grade.

**MCP Wrappable:** Yes, but requires Docker/WSL on Windows.

**Limitations:**
- **No native Windows embedded mode** -- dealbreaker for our setup
- Requires Docker or WSL for Windows local development
- Heavier than Qdrant or LanceDB for embedded use
- GraphQL query syntax has a learning curve

**Verdict:** Would be excellent for hybrid search, but the Windows limitation is a hard blocker for our "runs locally, no Docker" requirement. Eliminated.

---

### 6. pgvector (PostgreSQL)

**Multi-Collection:** YES (tables). Full SQL with vector columns.

**Hybrid Search:** YES. BM25 via pg_search/ParadeDB + pgvector for vector. Full SQL power for combining results.

**Structured Queries:** EXCELLENT. Full SQL. Joins, aggregations, CTEs, window functions, transactions. This is the gold standard for structured queries.

**Python SDK:** Excellent. psycopg2/psycopg3, SQLAlchemy, asyncpg. Mature ecosystem.

**Local/Embedded:** PARTIAL. PostgreSQL requires a running server process. Not truly embedded like SQLite. Can run locally via installer or Docker, but always a separate process. No in-process embedded mode.

**Performance at our scale:** Overkill but fine. PostgreSQL handles thousands of rows trivially.

**CRUD:** Full SQL CRUD. Transactions. Constraints. The works.

**Maturity:** HIGHEST. PostgreSQL is decades old, pgvector is well-maintained.

**MCP Wrappable:** Yes, but requires PostgreSQL server running.

**Limitations:**
- Requires running PostgreSQL server (not embedded/in-process)
- Installation and maintenance overhead
- Not designed for vector search first -- it's an extension on a relational DB
- No native graph traversal (would need recursive CTEs or Apache AGE extension)
- Heavy dependency for what should be a lightweight local service

**Verdict:** Maximum structured query power, but the operational overhead of running PostgreSQL for a local AI agent system is too heavy. Not the right tool for an embedded local service.

---

### 7. SQLite + sqlite-vec

**Multi-Collection:** YES (tables). Full SQL.

**Hybrid Search:** LIMITED. sqlite-vec provides KNN search. No native BM25 (would need sqlite FTS5 separately and manual fusion).

**Structured Queries:** GOOD (via SQL). But sqlite-vec metadata filtering is limited:
  - Only basic comparison operators on metadata columns
  - No LIKE, REGEXP, GLOB on vec0 metadata
  - JOIN limitations with virtual tables
  - No IS/ISNOT operators on metadata

**Python SDK:** Built-in (`sqlite3` module). sqlite-vec loads as extension.

**Local/Embedded:** PERFECT. SQLite is the gold standard for embedded databases.

**Performance at our scale:** Excellent. SQLite handles thousands of rows effortlessly.

**CRUD:** Full SQL CRUD (on regular tables). Virtual table (vec0) has limited update semantics.

**Maturity:** SQLite is extremely mature. sqlite-vec is young (v0.1.x) but actively developed.

**MCP Wrappable:** Very easy. Single file database, pure embedded.

**Limitations:**
- sqlite-vec is immature (v0.1.x)
- Metadata filtering is primitive compared to Qdrant/LanceDB
- No native hybrid search (would need manual BM25 + vector fusion)
- Virtual table limitations break some SQL patterns
- No graph capabilities
- Would need significant custom code to bridge gaps

**Verdict:** The embedded model is ideal, but sqlite-vec is too immature for production use. The metadata filtering limitations would force workarounds. Not ready yet.

---

### 8. Hybrid Solutions

#### 8a. SurrealDB (Multi-model: Document + Graph + Vector)

**What is it:** A multi-model database combining document, graph, relational, time-series, geospatial, and key-value with vector search. Written in Rust.

**Multi-Collection:** YES. Tables with flexible schemas. Supports SCHEMAFULL and SCHEMALESS modes.

**Hybrid Search:** YES. Full-text search + vector search in SurrealQL.

**Structured Queries:** EXCELLENT. SurrealQL is SQL-like with graph traversal built in. Can do `->relates_to->npc` graph traversals AND vector similarity in the same query.

**Graph Support:** YES. First-class graph edges between records. `RELATE npc:thrall->belongs_to->faction:horde`. Graph traversal via `->` and `<-` operators in queries.

**Python SDK:** AVAILABLE but YOUNG. `pip install surrealdb`. Async-first. Testing across Python 3.10-3.13. Some query functionality not yet in SDK.

**Local/Embedded:** YES. Can run embedded in Python (`surreal://memory` or `file://path`). Single Rust binary, can be embedded in-app. SurrealKV storage engine for persistence.

**Performance at our scale:** Fine. Designed to scale from embedded to distributed.

**CRUD:** Full CRUD via SurrealQL. CREATE, SELECT, UPDATE, DELETE with graph-aware syntax.

**Maturity:** MEDIUM. Active development, growing community. v2.x is current. But Python SDK is less mature than Qdrant's. Some missing features (multi-session transactions not available in embedded mode).

**MCP Wrappable:** Yes. Single embedded instance serves all 5 collections + graph relationships.

**Key Advantage:** This is the ONLY option that natively combines vector search + graph traversal + structured queries in a single engine. For our World Lore domain (NPCs relate to factions, zones contain NPCs) and Character reputation graphs, this is architecturally compelling.

**Limitations:**
- Python SDK is young (less mature than Qdrant/LanceDB)
- Some query features not yet available in embedded SDK
- Smaller community than PostgreSQL, Qdrant, or ChromaDB
- Documentation is decent but not as comprehensive as Qdrant
- Multi-session transactions not available in embedded mode
- Relatively new -- less battle-tested

**Verdict:** The most architecturally aligned option for our data model. World Lore IS a graph. Quest chains ARE a DAG. Character reputation IS a graph. SurrealDB can model all of this natively without layering graph-on-top-of-vector. The risk is SDK maturity. This deserves a proof-of-concept.

#### 8b. KuzuDB (Embedded Property Graph + Vector)

**What is it:** Embedded property graph database with built-in vector search and full-text search. Implements Cypher.

**Status:** **ARCHIVED on GitHub (October 2025).** The maintainers have stated they no longer actively support the project.

**Pre-Archive Features:**
- Embedded graph database (similar to SQLite for graphs)
- Cypher query language
- Native HNSW vector index
- Full-text search
- Python API

**Verdict:** ELIMINATED. Project archived. No future development. Using it would mean betting on abandoned software. There is a community fork (RyuGraph) but it's too small/new to trust.

#### 8c. FalkorDB (Graph + Vector)

**What is it:** Graph database using GraphBLAS sparse matrices. Vector search support. Targets Knowledge Graph for LLM use cases.

**Local Mode:** Requires Redis. Not truly embedded. Docker recommended.

**Python SDK:** Available but Redis-dependent.

**Verdict:** ELIMINATED. Redis dependency makes it not truly embeddable. Too heavy for our local use case.

#### 8d. Qdrant + NetworkX (Vector + In-Memory Graph)

**What is it:** Use Qdrant for vector/structured storage + NetworkX for in-memory graph operations.

**How it would work:**
- Qdrant: stores all 5 collections with payloads and vector search
- NetworkX: loads graph relationships from Qdrant payloads into a DiGraph for traversal queries
- On startup: build NetworkX graph from stored relationships
- On write: update both Qdrant and NetworkX

**Advantages:**
- Qdrant is battle-tested for vector + structured
- NetworkX is the standard Python graph library, zero learning curve
- Both are fully embedded/local
- Can persist graph in Qdrant payloads, load into NetworkX for traversal

**Disadvantages:**
- Two systems to maintain (sync between them)
- Graph lives in memory only (must rebuild on restart)
- NetworkX is pure Python (slow for large graphs, but fine for thousands of nodes)
- No single query language spanning both

**Verdict:** Pragmatic workaround. Solves the graph gap without introducing a new database. The sync complexity is manageable at our scale. Worth considering as a fallback if SurrealDB proves too immature.

---

## Knowledge Graph Libraries (Standalone Research)

For the World Lore and Dynamics domains specifically:

### NetworkX
- **Type:** Pure Python in-memory graph library
- **Strengths:** Standard library for graph analysis, comprehensive algorithms (shortest path, centrality, community detection), well-documented, huge community
- **Weaknesses:** Pure Python = slow at scale, no persistence, no query language, no vector search
- **Our scale fit:** Excellent. Thousands of nodes is trivial for NetworkX
- **Use case:** Build in-memory graph from stored data, traverse relationships (NPC->faction, zone->NPCs, quest->prerequisites)

### Neo4j
- **Type:** Full graph database with Cypher query language
- **Strengths:** Industry standard, GraphRAG support, excellent Python driver, Cypher is powerful
- **Weaknesses:** Requires Java runtime, server process, heavy for embedded use, commercial license for some features
- **Our scale fit:** Massive overkill. Running a Java-based graph server for thousands of nodes is architecturally wrong
- **Verdict:** Eliminated for our use case

### RDFLib
- **Type:** Python library for RDF knowledge graphs
- **Strengths:** W3C standards compliant, SPARQL queries, good for ontologies
- **Weaknesses:** RDF is verbose, SPARQL learning curve, not designed for AI/vector use cases
- **Verdict:** Wrong paradigm for our use case. We need property graphs, not RDF triples.

---

## Comparison Matrix

| Criteria | Qdrant | ChromaDB | LanceDB | Milvus Lite | Weaviate | pgvector | sqlite-vec | SurrealDB |
|----------|--------|----------|---------|-------------|----------|----------|------------|-----------|
| Multi-Collection | 5/5 | 4/5 | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Hybrid Search | 5/5 | 2/5 | 4/5 | 4/5 | 5/5 | 4/5 | 1/5 | 4/5 |
| Structured Queries | 4/5 | 2/5 | 4/5 | 3/5 | 4/5 | 5/5 | 3/5 | 5/5 |
| Graph Support | 0/5 | 0/5 | 0/5 | 0/5 | 1/5 | 0/5 | 0/5 | 4/5 |
| Python SDK | 5/5 | 4/5 | 4/5 | 4/5 | 4/5 | 5/5 | 3/5 | 3/5 |
| Local/Embedded | 4/5 | 5/5 | 5/5 | 3/5 | 0/5* | 2/5 | 5/5 | 4/5 |
| Windows Support | 5/5 | 5/5 | 5/5 | 4/5 | 0/5* | 3/5 | 5/5 | 4/5 |
| CRUD Ops | 4/5 | 3/5 | 4/5 | 4/5 | 4/5 | 5/5 | 3/5 | 4/5 |
| Maturity | 5/5 | 3/5 | 4/5 | 3/5 | 5/5 | 5/5 | 2/5 | 3/5 |
| Community | 5/5 | 4/5 | 3/5 | 4/5 | 4/5 | 5/5 | 2/5 | 3/5 |
| Single MCP Svc | 5/5 | 5/5 | 5/5 | 4/5 | 2/5 | 3/5 | 5/5 | 5/5 |
| **TOTAL** | **47** | **37** | **43** | **37** | **34** | **42** | **34** | **44** |

*Weaviate: Embedded mode not supported on Windows -- dealbreaker.

---

## Eliminated Options (with reasons)

| Option | Reason |
|--------|--------|
| **Weaviate** | No Windows embedded support. Requires Docker or WSL. |
| **Milvus/Milvus Lite** | Lite is explicitly a prototype tool. Full Milvus requires Docker/k8s. Overkill. |
| **pgvector** | Requires PostgreSQL server process. Not embedded. Operational overhead. |
| **sqlite-vec** | Immature (v0.1.x). Metadata filtering too limited. No hybrid search. |
| **KuzuDB** | Archived October 2025. Abandoned. |
| **FalkorDB** | Requires Redis. Not embeddable. |
| **ChromaDB** | Strictly less capable than Qdrant (which we already use). No reason to downgrade. |
| **Neo4j** | Java runtime, server process, overkill for thousands of nodes. |

---

## Shortlist: Top 3 Options

### Option A: Qdrant (evolved from v1)
**Architecture:** Qdrant for all 5 collections, with richer payload schemas and hybrid search.

**Pros:**
- We already know it. Migration path from v1 is smooth
- Mature, well-documented, strong community
- Full hybrid search (dense + sparse/BM25)
- Powerful payload filtering for structured queries
- Local mode works on Windows

**Cons:**
- No graph relationships. World Lore and Dynamics are inherently graph-shaped
- Would need supplementary graph layer (NetworkX in-memory or stored as payload relationships)
- Local mode is single-process (MCP service would need to be the sole accessor)

**Graph Workaround:** Store relationship edges as points in a "relationships" collection with payloads like `{from_type: "npc", from_id: "thrall", to_type: "faction", to_id: "horde", relation: "leader_of"}`. Load into NetworkX for traversal queries. Or store adjacency lists in entity payloads.

**Risk Level:** LOW. Known quantity.

---

### Option B: LanceDB (modern embedded alternative)
**Architecture:** LanceDB for all 5 collections as tables, with Pydantic-defined schemas.

**Pros:**
- Truly embedded, zero server overhead (like SQLite for vectors)
- SQL-like WHERE clauses (more intuitive than Qdrant's filter DSL)
- Native BM25 hybrid search
- Pydantic model integration for schema definition (aligns with our Pydantic AI stack)
- Apache Arrow foundation (efficient columnar storage)
- Good CRUD with filter-based updates/deletes
- No single-process limitation (Lance format handles concurrent reads)

**Cons:**
- No graph relationships (same gap as Qdrant)
- Smaller community than Qdrant
- BM25/FTS support is newer (less battle-tested)
- Would need same NetworkX graph supplement as Qdrant

**Graph Workaround:** Same as Qdrant -- supplementary graph layer.

**Risk Level:** LOW-MEDIUM. Well-designed, but we'd be learning a new tool.

---

### Option C: SurrealDB (multi-model unified)
**Architecture:** SurrealDB for all 5 collections + graph edges, single unified query language.

**Pros:**
- Vector search + graph traversal + structured SQL in ONE system
- Graph relationships are first-class (RELATE, ->, <- operators)
- World Lore NPC-faction-zone relationships modeled naturally
- Quest chain DAGs modeled naturally
- Character reputation graph modeled naturally
- Dynamics can be computed via graph queries
- Single SurrealQL query can: find similar lore (vector) WHERE faction = "Horde" AND ->belongs_to->zone.name = "Orgrimmar"
- Embedded in Python (no server needed)
- No need for supplementary graph layer

**Cons:**
- Python SDK is young (3/5 maturity)
- Smaller community
- Some embedded mode limitations (no multi-session transactions)
- Less battle-tested than Qdrant
- Learning curve for SurrealQL
- Risk of hitting SDK bugs or missing features

**Graph Advantage Example:**
```sql
-- Find NPCs in a zone who belong to a faction the character is hostile with
SELECT * FROM npc
WHERE ->located_in->zone.name = "Elwynn Forest"
AND ->belongs_to->faction<-hostile_with<-character:player1
```
This query is impossible in Qdrant/LanceDB without multiple round-trips and application-level joins.

**Risk Level:** MEDIUM. The architecture fit is excellent but SDK maturity is a concern.

---

## Recommendation

### Primary Recommendation: Option C (SurrealDB) with Option A (Qdrant) as fallback

**Reasoning:**

1. **Data model alignment.** Our 5 knowledge domains are NOT flat document collections. World Lore is a property graph. Quest Lore is a DAG. Character has a reputation graph. Dynamics is computed via graph traversal. Forcing graph-shaped data into a vector-only store means building and maintaining a parallel graph layer (NetworkX), which adds complexity and sync overhead.

2. **SurrealDB is the only option that doesn't require "AND also use X for graphs."** Every other option needs vector DB + something else. SurrealDB is vector + graph + structured in one.

3. **The risk is manageable.** We can de-risk with a focused proof-of-concept:
   - Model a subset of World Lore (one zone, its NPCs, factions, relationships)
   - Test: vector search + graph traversal + CRUD + embedded Python
   - Evaluate SDK stability, query performance, error handling
   - If PoC fails, fall back to Qdrant + NetworkX (Option A hybrid)

4. **Qdrant as fallback is safe.** We already have v1 experience. The Qdrant + NetworkX hybrid is less elegant but proven technology.

### Proof-of-Concept Scope

Before committing to SurrealDB, validate:
- [ ] Embedded mode works on Windows 11 with Python 3.10+
- [ ] Can create 5 separate tables with different schemas
- [ ] Can store vectors and perform similarity search
- [ ] Can create graph edges (RELATE) between records across tables
- [ ] Can do graph traversal queries (->)
- [ ] Can combine vector search with graph traversal in one query
- [ ] Can do CRUD operations (create, read, update, delete)
- [ ] Python SDK stability under normal operations
- [ ] Can wrap as MCP service (FastMCP + SurrealDB embedded)
- [ ] Data persistence across restarts

### If SurrealDB PoC Fails: Fallback Architecture

**Qdrant + NetworkX hybrid:**
- Qdrant: 5 collections with rich payloads, hybrid search (dense + BM25 sparse)
- NetworkX: in-memory DiGraph for World Lore, Quest Lore, and Character relationship traversal
- Graph persisted as Qdrant points in a "relationships" collection
- On MCP startup: load relationship points -> build NetworkX graph
- On write: update Qdrant + NetworkX simultaneously
- Complexity: manageable at our scale (thousands of nodes)

---

## Sources

### Qdrant
- [Qdrant 2025 Recap](https://qdrant.tech/blog/2025-recap/)
- [Qdrant Hybrid Queries](https://qdrant.tech/documentation/concepts/hybrid-queries/)
- [Qdrant Payload Filtering](https://qdrant.tech/documentation/concepts/filtering/)
- [Qdrant Points CRUD](https://qdrant.tech/documentation/concepts/points/)
- [Qdrant Python Client](https://github.com/qdrant/qdrant-client)
- [Qdrant Local Mode](https://python-client.qdrant.tech/_modules/qdrant_client/local/qdrant_local)

### ChromaDB
- [ChromaDB GitHub](https://github.com/chroma-core/chroma)
- [ChromaDB Query & Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)
- [ChromaDB Multi-Category Filters](https://cookbook.chromadb.dev/strategies/multi-category-filters/)

### LanceDB
- [LanceDB Homepage](https://lancedb.com/)
- [LanceDB GitHub](https://github.com/lancedb/lancedb)
- [LanceDB Table Operations](https://docs.lancedb.com/tables)
- [LanceDB Full-Text Search](https://lancedb.com/docs/search/full-text-search/)
- [LanceDB Hybrid Search](https://deepwiki.com/lancedb/lancedb/6.4-hybrid-search)
- [LanceDB Python API](https://lancedb.github.io/lancedb/python/python/)

### Milvus
- [Milvus Lite Documentation](https://milvus.io/docs/milvus_lite.md)
- [Milvus Lite PyPI](https://pypi.org/project/milvus-lite/)

### Weaviate
- [Weaviate Embedded Mode](https://weaviate.io/developers/weaviate/installation/embedded)
- [Weaviate Windows Issue](https://github.com/weaviate/weaviate/issues/4668)
- [Weaviate Hybrid Search](https://docs.weaviate.io/weaviate/search/hybrid)

### pgvector
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [ParadeDB Hybrid Search](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)

### sqlite-vec
- [sqlite-vec GitHub](https://github.com/asg017/sqlite-vec)
- [sqlite-vec Metadata Filtering](https://alexgarcia.xyz/blog/2024/sqlite-vec-metadata-release/index.html)
- [Metadata Filtering Tracking Issue](https://github.com/asg017/sqlite-vec/issues/26)

### SurrealDB
- [SurrealDB Homepage](https://surrealdb.com)
- [SurrealDB Vector Search](https://surrealdb.com/docs/surrealdb/models/vector)
- [SurrealDB Python SDK](https://github.com/surrealdb/surrealdb.py)
- [SurrealDB Embedding in Python](https://surrealdb.com/docs/surrealdb/embedding/python)
- [SurrealDB Features](https://surrealdb.com/features)

### KuzuDB
- [KuzuDB GitHub (Archived)](https://github.com/kuzudb/kuzu)
- [KuzuDB Vector Search](https://docs.kuzudb.com/extensions/vector/)

### FalkorDB
- [FalkorDB Homepage](https://www.falkordb.com/)
- [FalkorDB GitHub](https://github.com/FalkorDB/FalkorDB)

### NetworkX
- [NetworkX Documentation](https://networkx.org/documentation/stable/reference/introduction.html)
- [Simple In-Memory Knowledge Graphs](https://safjan.com/simple-inmemory-knowledge-graphs-for-quick-graph-querying/)
- [NetworkX is Fast Now (PyData 2025)](https://cfp.pydata.org/london2025/talk/XTU8RH/)

### Comparisons
- [ChromaDB vs Qdrant (Airbyte)](https://airbyte.com/data-engineering-resources/chroma-db-vs-qdrant)
- [Best Vector Databases 2025 (Firecrawl)](https://www.firecrawl.dev/blog/best-vector-databases)
- [Milvus Alternatives: Chroma, Qdrant, LanceDB](https://www.myscale.com/blog/milvus-alternatives-chroma-qdrant-lancedb/)
