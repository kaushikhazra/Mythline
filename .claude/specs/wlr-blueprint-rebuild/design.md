# WLR Blueprint Rebuild — Design

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Extract research topics to `config/research_topics.yml` (YAML, not JSON) | Project already uses YAML for `config/sources.yml`. YAML handles multi-line strings natively with `\|` blocks. Keeps the config layer consistent. _(BR-2)_ |
| D2 | Merge `RESEARCH_TOPICS`, `TOPIC_SCHEMA_HINTS`, and `TOPIC_SECTION_HEADERS` into one YAML file keyed by topic | Eliminates three parallel dicts. Each topic's instructions, schema hints, and section header live together. Single source of truth per topic. _(BR-2)_ |
| D3 | All tunable constants in `config.py` as module-level variables | Follows blueprint anatomy: config.py = "centralised env var reads + sensible defaults". Even non-env-var constants belong here when they're tunable values (char limits, queue names). _(BR-1)_ |
| D4 | Fix two inline imports (daemon.py `main()`, pipeline.py `_reconstruct_labeled_content()`) by moving to top-level | Blueprint hard constraint #4: "No inline imports". No exceptions. _(BR-3)_ |
| D5 | Create `test_mcp_client.py` to cover `mcp_client.py` | Blueprint hard constraint #7: "Every module has tests". Currently missing. _(BR-3, BR-6)_ |
| D6 | Rewrite each file from scratch, not incremental refactor | The code was built across 3 specs (world-lore-researcher, research-job-queue, wlr-research-depth). A fresh write per file ensures each reads as a coherent unit following its blueprint role, not an accumulation of patches. Functional equivalence verified by existing tests. _(BR-4, BR-5)_ |

---

## 1. Configuration Centralization

### 1.1 Constants Migration

Three constants move into `config.py`:

```python
# --- Tuning Constants ---
EXTRACT_CONTENT_CHAR_LIMIT = _int_env("EXTRACT_CONTENT_CHAR_LIMIT", 300_000)
CRAWL_CONTENT_TRUNCATE_CHARS = _int_env("CRAWL_CONTENT_TRUNCATE_CHARS", 5_000)

# --- Queue Names ---
VALIDATOR_QUEUE = os.getenv("VALIDATOR_QUEUE", "agent.world_lore_validator")
```

- `_EXTRACT_CONTENT_CHAR_LIMIT` loses the underscore prefix (it's no longer module-private — it's a public config constant).
- All three become env-var-backed with the current hardcoded values as defaults (backward compatible).

### 1.2 config.py Sections

The rebuilt config.py is organized into clear sections:

```python
# --- Agent Identity ---
AGENT_ID, AGENT_ROLE, GAME_NAME

# --- Token Budgets ---
DAILY_TOKEN_BUDGET, PER_ZONE_TOKEN_BUDGET

# --- Limits ---
MAX_RESEARCH_VALIDATE_ITERATIONS, RATE_LIMIT_REQUESTS_PER_MINUTE
EXTRACT_CONTENT_CHAR_LIMIT, CRAWL_CONTENT_TRUNCATE_CHARS

# --- Queue Names ---
JOB_QUEUE, STATUS_QUEUE, VALIDATOR_QUEUE

# --- Service URLs ---
RABBITMQ_URL, MCP_STORAGE_URL, MCP_WEB_SEARCH_URL, MCP_WEB_CRAWLER_URL, MCP_SUMMARIZER_URL

# --- LLM ---
LLM_MODEL

# --- Config Loaders ---
load_sources_config(), get_source_domains_by_tier(), get_all_trusted_domains(),
get_source_tier_for_domain(), get_source_weight(), load_research_topics()
```

### 1.3 Research Topics Config File

New file: `config/research_topics.yml`

```yaml
topics:
  zone_overview_research:
    section_header: "## ZONE OVERVIEW"
    schema_hints: |
      zone metadata: name, level range, expansion era.
      MUST PRESERVE: narrative arc (full storyline — political backstory,
      primary conflict, factional tensions, and resolution — not a tagline),
      political climate (governing factions, neglected populations, power
      struggles), phase states (Cataclysm changes, quest progression phases),
      sub-areas and landmarks.
      Preserve ALL proper nouns (NPC names, faction names, place names)
      even when compressing surrounding text.
    instructions: |
      Focus on zone overview for {zone} in {game}.

      Phase 1 — Search for the zone's main wiki page and overview articles. ...

      Phase 2 — If the zone has a major storyline or dungeon, search for ...

  npc_research:
    section_header: "## NPCs AND NOTABLE CHARACTERS"
    schema_hints: |
      NPCs: names, titles, faction allegiance. ...
    instructions: |
      Focus on NPCs and notable characters in {zone} in {game}. ...

  faction_research:
    section_header: "## FACTIONS AND ORGANIZATIONS"
    schema_hints: |
      factions: names, type (major faction, guild, cult, military). ...
    instructions: |
      Focus on factions and organizations in {zone} in {game}. ...

  lore_research:
    section_header: "## LORE, HISTORY, AND MYTHOLOGY"
    schema_hints: |
      lore: event titles, era/timeline placement. ...
    instructions: |
      Focus on lore, history, mythology, and cosmology of {zone} in {game}. ...

  narrative_items_research:
    section_header: "## LEGENDARY ITEMS AND NARRATIVE OBJECTS"
    schema_hints: |
      items and artifacts: names, significance tier. ...
    instructions: |
      Focus on narrative items and artifacts in {zone} in {game}. ...
```

Each topic has three fields:
- `section_header` — used by `_reconstruct_labeled_content()` to delimit content sections
- `schema_hints` — used by `_maybe_summarize_sections()` as the MCP Summarizer's schema hint
- `instructions` — used by `_make_research_step()` with `{zone}` and `{game}` placeholders

### 1.4 Loading Function

Added to `config.py`:

```python
def load_research_topics() -> dict:
    """Load research topic configuration from config/research_topics.yml."""
    topics_path = AGENT_DIR / "config" / "research_topics.yml"
    with open(topics_path) as f:
        return yaml.safe_load(f)
```

Returns the full YAML structure. Callers access `topics["topics"][topic_key]`.

### 1.5 Pipeline Integration

`pipeline.py` loads topics once at module level and replaces the three dicts:

```python
from src.config import load_research_topics

_TOPICS_CONFIG = load_research_topics()["topics"]


def _get_topic_instructions(topic_key: str) -> str:
    return _TOPICS_CONFIG[topic_key]["instructions"]


def _get_topic_section_header(topic_key: str) -> str:
    return _TOPICS_CONFIG[topic_key]["section_header"]


def _get_topic_schema_hints(topic_key: str) -> str:
    return _TOPICS_CONFIG[topic_key]["schema_hints"]
```

`_make_research_step()` calls `_get_topic_instructions(topic_key)` instead of indexing `RESEARCH_TOPICS`.
`_reconstruct_labeled_content()` calls `_get_topic_section_header(topic)`.
`_maybe_summarize_sections()` calls `_get_topic_schema_hints(topic)`.

---

## 2. Per-File Rebuild Scope

### 2.1 config.py — Centralized Configuration

**Exports:** All constants + all loader functions.

**Changes:**
- Add `EXTRACT_CONTENT_CHAR_LIMIT`, `CRAWL_CONTENT_TRUNCATE_CHARS`, `VALIDATOR_QUEUE`
- Add `load_research_topics()`
- Organize into sections (see 1.2)
- All other content preserved as-is

### 2.2 agent.py — LLM Brain

**Exports:** `LoreResearcher`, `ResearchContext`

**Changes:**
- Rewrite from scratch following blueprint anatomy
- `ResearchContext` dataclass stays (blueprint allows runtime deps as dataclasses in agent.py)
- `EXTRACTION_CATEGORIES` stays (agent wiring configuration)
- `LoreResearcher` class rewritten cleanly: same methods, same signatures, same behavior
- `crawl_webpage` tool import and registration stays

### 2.3 models.py — Pure Pydantic Models

**Exports:** All model classes and enums.

**Changes:**
- Rewrite from scratch with consistent organization:
  1. Enums (`SourceTier`, `FactionStance`, `LoreCategory`, `ItemSignificance`, `MessageType`, `JobStatus`)
  2. Sub-models (`SourceReference`, `PhaseState`, `NPCRelationship`, `FactionRelation`, `Conflict`, `ValidationFeedback`)
  3. Domain models (`ZoneData`, `NPCData`, `FactionData`, `LoreData`, `NarrativeItemData`)
  4. Message models (`ResearchJob`, `ZoneFailure`, `JobStatusUpdate`, `BudgetState`, `MessageEnvelope`, `ResearchPackage`, `ValidationResult`, `UserDecisionRequired`, `UserDecisionResponse`)
  5. Checkpoint (`ResearchCheckpoint`)
  6. Agent output models (`ZoneExtraction`, `NPCExtractionResult`, `FactionExtractionResult`, `LoreExtractionResult`, `NarrativeItemExtractionResult`, `CrossReferenceResult`, `ResearchResult`, `ConnectedZonesResult`)
- No logic changes — same fields, same types, same validators

### 2.4 logging_config.py — Structured Logging

**Exports:** `setup_logging`, `StructuredJsonFormatter`

**Changes:**
- Rewrite from scratch
- Same `StructuredJsonFormatter`, same `setup_logging()`, same `EVENT_TYPES`, same `DOMAIN`
- No behavioral changes

### 2.5 tools.py — RunContext Tool Functions

**Exports:** `crawl_webpage`, `normalize_url`, `make_source_ref`

**Changes:**
- Remove `CRAWL_CONTENT_TRUNCATE_CHARS` constant (import from config)
- Same tool function signatures and behavior

### 2.6 pipeline.py — Orchestration

**Exports:** `PIPELINE_STEPS`, `run_pipeline`

**Changes:**
- Remove `RESEARCH_TOPICS`, `TOPIC_SECTION_HEADERS`, `TOPIC_SCHEMA_HINTS` dicts
- Remove `_EXTRACT_CONTENT_CHAR_LIMIT` constant
- Add `_TOPICS_CONFIG` loaded from config at module level
- Add three accessor functions (`_get_topic_instructions`, `_get_topic_section_header`, `_get_topic_schema_hints`)
- Fix inline import: `from collections import OrderedDict` moves to top of file
- Import `EXTRACT_CONTENT_CHAR_LIMIT` from config
- `_make_research_step()` uses `_get_topic_instructions()`
- `_reconstruct_labeled_content()` uses `_get_topic_section_header()`
- `_maybe_summarize_sections()` uses `_get_topic_schema_hints()` and `EXTRACT_CONTENT_CHAR_LIMIT`
- All step functions and `run_pipeline()` unchanged

### 2.7 daemon.py — Process Lifecycle

**Exports:** `Daemon`, `main`

**Changes:**
- Remove `VALIDATOR_QUEUE` constant (import from config)
- Fix inline import: `from src.logging_config import setup_logging` moves to top of file
- Import `VALIDATOR_QUEUE` from config
- All other logic unchanged

### 2.8 mcp_client.py — MCP Interaction Wrappers

**Exports:** `mcp_call`, `crawl_url`

**Changes:**
- Rewrite from scratch
- Same functions, same signatures, same behavior
- No structural issues to fix

### 2.9 checkpoint.py — State Persistence

**Exports:** All checkpoint + budget functions.

**Changes:**
- Rewrite from scratch
- Same functions, same signatures, same behavior
- No structural issues to fix

---

## 3. Blueprint Violation Fixes

| # | Violation | Location | Fix |
|---|-----------|----------|-----|
| V1 | Inline import `from src.logging_config import setup_logging` | daemon.py:426 | Move to top-level imports |
| V2 | Inline import `from collections import OrderedDict` | pipeline.py:304 | Move to top-level imports |
| V3 | Config constant `_EXTRACT_CONTENT_CHAR_LIMIT` outside config.py | pipeline.py:296 | Move to config.py as `EXTRACT_CONTENT_CHAR_LIMIT` |
| V4 | Config constant `CRAWL_CONTENT_TRUNCATE_CHARS` outside config.py | tools.py:8 | Move to config.py |
| V5 | Config constant `VALIDATOR_QUEUE` outside config.py | daemon.py:46 | Move to config.py |
| V6 | Missing test file for mcp_client.py | tests/ | Create `test_mcp_client.py` |

---

## 4. Test Updates

### 4.1 Import Path Changes

Tests that import moved constants need updating:
- `test_pipeline.py`: References to `_EXTRACT_CONTENT_CHAR_LIMIT` → `EXTRACT_CONTENT_CHAR_LIMIT` from config
- `test_pipeline.py`: References to `RESEARCH_TOPICS`, `TOPIC_SCHEMA_HINTS`, `TOPIC_SECTION_HEADERS` → access via `_TOPICS_CONFIG` or accessor functions
- `test_tools.py`: References to `CRAWL_CONTENT_TRUNCATE_CHARS` → import from config
- `test_daemon.py`: References to `VALIDATOR_QUEUE` → import from config

### 4.2 New Test File

`test_mcp_client.py` covers:
- `mcp_call()` — success path, error path, timeout
- `crawl_url()` — success, HTTP error, empty content, connection error
- `_parse_result()` — single text, multiple texts, no content, non-JSON text
- `_extract_all_text()` — concatenation

### 4.3 Functional Equivalence Gate

All existing tests must pass after rebuild. The test count must be >= current count. No test logic changes — only import path updates where constants or access patterns changed.

---

## 5. New File

| File | Purpose |
|------|---------|
| `config/research_topics.yml` | Research topic configuration: per-topic instructions, schema hints, section headers. Extracted from pipeline.py. |

---

## Files Changed

| File | Change |
|------|--------|
| `src/config.py` | Add 3 constants (`EXTRACT_CONTENT_CHAR_LIMIT`, `CRAWL_CONTENT_TRUNCATE_CHARS`, `VALIDATOR_QUEUE`), add `load_research_topics()`, organize into sections. Rewrite. _(BR-1, BR-4)_ |
| `src/agent.py` | Rewrite from scratch. Same class, same methods, same behavior. _(BR-4)_ |
| `src/models.py` | Rewrite from scratch. Reorganize into consistent section order. Same models. _(BR-4)_ |
| `src/logging_config.py` | Rewrite from scratch. Same formatter, same setup. _(BR-4)_ |
| `src/tools.py` | Remove `CRAWL_CONTENT_TRUNCATE_CHARS`, import from config. Rewrite. _(BR-1, BR-4)_ |
| `src/pipeline.py` | Remove 3 domain dicts + 1 constant, load topics from config YAML, fix inline import. Rewrite. _(BR-1, BR-2, BR-3, BR-4)_ |
| `src/daemon.py` | Remove `VALIDATOR_QUEUE`, import from config, fix inline import. Rewrite. _(BR-1, BR-3, BR-4)_ |
| `src/mcp_client.py` | Rewrite from scratch. Same functions. _(BR-4)_ |
| `src/checkpoint.py` | Rewrite from scratch. Same functions. _(BR-4)_ |
| `config/research_topics.yml` | **NEW** — research topic configuration extracted from pipeline.py. _(BR-2)_ |
| `tests/test_pipeline.py` | Update imports for moved constants and topic accessors. _(BR-5)_ |
| `tests/test_tools.py` | Update import for `CRAWL_CONTENT_TRUNCATE_CHARS`. _(BR-5)_ |
| `tests/test_daemon.py` | Update import for `VALIDATOR_QUEUE`. _(BR-5)_ |
| `tests/test_mcp_client.py` | **NEW** — tests for `mcp_call`, `crawl_url`, result parsing. _(BR-3, BR-6)_ |
| `tests/test_config.py` | Add tests for `load_research_topics()` and new constants. _(BR-5)_ |
