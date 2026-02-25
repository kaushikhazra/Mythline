# WLR Blueprint Rebuild — Tasks

## 1. Config Foundation

- [x] Velasari rewrites `src/config.py` with centralized constants and section organization — _BR-1_
  - [x] Add `EXTRACT_CONTENT_CHAR_LIMIT` (env-backed, default 300000)
  - [x] Add `CRAWL_CONTENT_TRUNCATE_CHARS` (env-backed, default 5000)
  - [x] Add `VALIDATOR_QUEUE` (env-backed, default "agent.world_lore_validator")
  - [x] Add `load_research_topics()` function that reads `config/research_topics.yml`
  - [x] Organize into sections: identity, budgets, limits, queues, URLs, LLM, loaders
- [x] Velasari creates `config/research_topics.yml` with all 5 topics extracted from pipeline.py — _BR-2_
  - [x] Each topic has `section_header`, `schema_hints`, `instructions` fields
  - [x] Content matches current `RESEARCH_TOPICS`, `TOPIC_SCHEMA_HINTS`, `TOPIC_SECTION_HEADERS` exactly
- [x] Velasari updates `tests/test_config.py` with tests for new constants and YAML loader — _BR-5_

## 2. Core Module Rewrites

- [x] Velasari rewrites `src/models.py` with consistent section organization — _BR-4_
  - [x] Sections: enums, sub-models, domain models, message models, checkpoint, agent output models
  - [x] Same fields, same types, same validators — no logic changes
- [x] Velasari rewrites `src/logging_config.py` from scratch — _BR-4_
- [x] Velasari rewrites `src/mcp_client.py` from scratch — _BR-4_
- [x] Velasari rewrites `src/checkpoint.py` from scratch — _BR-4_
- [x] Velasari creates `tests/test_mcp_client.py` covering mcp_call, crawl_url, result parsing — _BR-3, BR-6_

## 3. Tool and Agent Rewrites

- [x] Velasari rewrites `src/tools.py` — imports `CRAWL_CONTENT_TRUNCATE_CHARS` from config — _BR-1, BR-4_
- [x] Velasari rewrites `src/agent.py` — clean `LoreResearcher` class, same methods — _BR-4_
- [x] Velasari updates `tests/test_tools.py` for import path changes — _BR-5_
- [x] Velasari updates `tests/test_agent.py` for import path changes — _BR-5_

## 4. Pipeline Rewrite

- [x] Velasari rewrites `src/pipeline.py` — removes domain dicts, loads from YAML config — _BR-2, BR-4_
  - [x] Remove `RESEARCH_TOPICS`, `TOPIC_SCHEMA_HINTS`, `TOPIC_SECTION_HEADERS` dicts
  - [x] Add `_TOPICS_CONFIG` loaded from `config.load_research_topics()` at module level
  - [x] Add accessor functions: `_get_topic_instructions`, `_get_topic_section_header`, `_get_topic_schema_hints`
  - [x] Fix inline `from collections import OrderedDict` import — _BR-3_
  - [x] Import `EXTRACT_CONTENT_CHAR_LIMIT` from config — _BR-1_
- [x] Velasari updates `tests/test_pipeline.py` for new access patterns — _BR-5_

## 5. Daemon Rewrite + Regression

- [x] Velasari rewrites `src/daemon.py` — imports `VALIDATOR_QUEUE` from config, fixes inline import — _BR-1, BR-3, BR-4_
- [x] Velasari updates `tests/test_daemon.py` for import path changes — _BR-5_
- [x] Velasari runs full test suite to verify functional equivalence — _BR-5_
  - [x] All unit tests pass (253 passed, 8 integration skipped)
  - [x] Test count >= current count (253 >= 237 baseline)
