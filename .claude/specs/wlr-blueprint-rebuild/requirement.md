# WLR Blueprint Rebuild — Requirements

## Overview

The World Lore Researcher agent was built incrementally across three specs (world-lore-researcher, research-job-queue, wlr-research-depth). The result is functional and well-tested (101 unit tests, 8 integration tests), but the source code carries structural drift from iterative development. Configuration constants are scattered across modules, the pipeline contains large domain-specific data dicts that are prompt/research configuration rather than orchestration logic, and one inline import violates the blueprint hard constraints.

This rebuild rewrites the `src/` Python files from scratch against the current agent design blueprint (`anatomy.md`). Same functionality, same prompts, same MCP interactions — clean structure.

---

## User Stories

### BR-1: Configuration Centralization

**As a** developer maintaining the WLR agent,
**I want** ALL configuration constants centralized in `config.py`,
**so that** changing any tunable value requires editing exactly one file.

**Acceptance Criteria:**
- `EXTRACT_CONTENT_CHAR_LIMIT` (currently `_EXTRACT_CONTENT_CHAR_LIMIT` in pipeline.py) defined in config.py
- `CRAWL_CONTENT_TRUNCATE_CHARS` (currently in tools.py) defined in config.py
- `VALIDATOR_QUEUE` (currently hardcoded in daemon.py) defined in config.py
- No module outside config.py defines constants sourced from environment variables or hardcoded tunables
- All existing env var names unchanged (backward compatible)
- Source config helpers (`load_sources_config`, `get_source_domains_by_tier`, etc.) remain in config.py

### BR-2: Pipeline as Pure Orchestration

**As a** developer reading `pipeline.py`,
**I want** it to contain ONLY step functions and orchestration logic,
**so that** domain-specific research configuration is clearly separated from execution flow.

**Acceptance Criteria:**
- `RESEARCH_TOPICS` dict extracted from pipeline.py into a dedicated config file under `config/`
- `TOPIC_SCHEMA_HINTS` dict extracted alongside `RESEARCH_TOPICS`
- `TOPIC_SECTION_HEADERS` dict extracted alongside `RESEARCH_TOPICS`
- Pipeline step functions load or receive these as parameters
- `PIPELINE_STEPS` list and `run_pipeline()` orchestration flow unchanged
- Step dispatch table (`STEP_FUNCTIONS`) unchanged

### BR-3: Zero Blueprint Violations

**As a** developer,
**I want** zero violations of the 9 hard constraints from the agent blueprint,
**so that** WLR serves as the reference implementation for all subsequent agents.

**Acceptance Criteria:**
- No inline imports anywhere (daemon.py `main()` inline import fixed)
- No prompt strings in Python code (all in `prompts/*.md`)
- No MCP construction in Python (all via `config/mcp_config.json`)
- No Pydantic `BaseModel` subclasses outside `models.py`
- Every source module has a corresponding test file
- All imports at top of file, ordered: stdlib, third-party, local

### BR-4: Clean Module Anatomy

**As a** developer building the next agent (World Lore Validator),
**I want** each WLR source file to be a clean, canonical example of its blueprint role,
**so that** I can use it as a pattern reference.

**Acceptance Criteria:**
- `agent.py`: LLM agent wiring only — Agent instances, tool registration, MCP context management, `ResearchContext` dataclass
- `config.py`: All env vars with sensible defaults, all tunable constants, source config helpers
- `models.py`: All `BaseModel` subclasses and enums, no business logic
- `logging_config.py`: `StructuredJsonFormatter` + `setup_logging()` only
- `tools.py`: `crawl_webpage` RunContext tool + private helpers (`normalize_url`, `make_source_ref`)
- `pipeline.py`: Step functions + `run_pipeline()` orchestration + step dispatch only
- `daemon.py`: `Daemon` class (RabbitMQ consumer, wave-loop executor, signal handling) only
- `mcp_client.py`: `mcp_call()` + `crawl_url()` + result parsing helpers only
- `checkpoint.py`: Checkpoint CRUD + budget helpers only

### BR-5: Functional Equivalence

**As the** system,
**I want** the rebuilt source code to produce identical runtime behavior,
**so that** no downstream integration breaks.

**Acceptance Criteria:**
- All existing unit tests pass (updated for import path changes only, no logic changes)
- Same pipeline steps execute in same order with same names
- Same MCP calls with same arguments and same response handling
- Same RabbitMQ messages published with same schemas
- Same structured log events emitted with same fields
- Test count >= current test count (no test regression)

### BR-6: Test Structure Alignment

**As a** developer,
**I want** test files to mirror source files 1:1,
**so that** finding tests for any module is trivial.

**Acceptance Criteria:**
- Every `src/*.py` module has a corresponding `tests/test_*.py` file
- Test imports reflect the new module structure
- No test file tests code from multiple unrelated modules
- Existing test coverage maintained — no tests deleted without equivalent replacement

---

## Out of Scope

- **Prompts** (`prompts/*.md`) — not touched, same content
- **MCP config** (`config/mcp_config.json`) — not touched
- **Dockerfile** — not touched
- **pyproject.toml / uv.lock** — not touched
- **conftest.py** — not touched (unless imports change)
- **.env / .env.example** — not touched
- **New features** — no new functionality added
- **config/sources.yml** — not touched (already exists)
- **shared/** utilities — not touched
