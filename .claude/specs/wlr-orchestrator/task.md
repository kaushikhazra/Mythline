# WLR LLM-Driven Orchestrator — Tasks

## 1. Config Foundation

- [x] Velasari adds topic accessor functions (`get_topic_instructions`, `get_topic_section_header`, `get_topic_schema_hints`) to `src/config.py` with module-level `_TOPICS_CONFIG` — _WO-3, D11_
- [x] Velasari adds unit tests for topic accessors in `tests/test_config.py` — _WO-3_

## 2. Orchestrator Prompts

- [x] Velasari creates `prompts/orchestrator_system.md` with orchestrator persona, available tools, workflow guidance, and constraints — _WO-1_
- [x] Velasari creates `prompts/orchestrator_task.md` with per-zone task template (`{zone_name}`, `{game_name}`, `{skip_discovery}`) — _WO-1, D12_

## 3. Orchestrator Tools

- [x] Velasari creates `src/orchestrator_tools.py` with 6 tool functions (`research_topic`, `extract_category`, `cross_reference`, `discover_zones`, `summarize_content`, `crawl_webpage`) — _WO-2_
  - [x] Each tool uses `RunContext[OrchestratorContext]`, delegates to worker agents via deps
  - [x] Each tool accumulates structured results in deps, returns brief text summary to orchestrator LLM
  - [x] `CATEGORY_TO_TOPIC` mapping defined for extract_category
- [x] Velasari creates `tests/test_orchestrator_tools.py` with unit tests for all 6 tools — _WO-2_
  - [x] Happy path for each tool
  - [x] Error handling: no content for extract, no zone_data for cross_reference
  - [x] Accumulation verification: deps fields populated correctly
  - [x] Token tracking: worker_tokens incremented after each tool call

## 4. Agent Rewrite

- [x] Velasari adds `OrchestratorContext` and `OrchestratorResult` dataclasses to `src/agent.py` — _WO-1, D8_
- [x] Velasari adds orchestrator agent construction and tool registration in `LoreResearcher.__init__` — _WO-1_
- [x] Velasari rewrites `research_zone()` to use orchestrator (new signature: `zone_name, skip_discovery -> OrchestratorResult`) — _WO-1, WO-4_
- [x] Velasari removes old facade methods (`extract_category`, `cross_reference`, `discover_connected_zones`) — _WO-3_
- [x] Velasari updates `tests/test_agent.py` for new API — _WO-1_

## 5. Daemon Rewrite

- [x] Velasari replaces `run_pipeline()` call with `researcher.research_zone()` in `src/daemon.py` — _WO-3, WO-4_
- [x] Velasari adds `_assemble_package()` method to daemon — _WO-4_
- [x] Velasari moves `_compute_quality_warnings()` and `_apply_confidence_caps()` from pipeline.py to daemon.py — _WO-3, D6_
- [x] Velasari adds `zone_tokens` structured log event after each zone — _WO-5_
- [x] Velasari removes checkpoint logic, step progress callback, `TOTAL_STEPS`, pipeline import — _WO-3, WO-4_
- [x] Velasari updates `tests/test_daemon.py` for new flow — _WO-4_

## 6. Pipeline Elimination + Model Cleanup

- [x] Velasari deletes `src/pipeline.py` and `tests/test_pipeline.py` — _WO-3, D10_
- [x] Velasari removes `ResearchResult` from `src/models.py` — _WO-3_
- [x] Velasari runs full test suite — all tests pass, no references to deleted code — _WO-6_
