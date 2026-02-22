# Research Job Queue — Tasks

## 1. Models (`src/models.py`)

- [x] Velasari adds `ResearchJob` Pydantic model to `src/models.py` with fields: `job_id`, `zone_name`, `depth`, `game`, `requested_by`, `requested_at` — _US-1_
- [x] Velasari adds `JobStatus` enum to `src/models.py` with values: `ACCEPTED`, `ZONE_STARTED`, `STEP_PROGRESS`, `ZONE_COMPLETED`, `JOB_COMPLETED`, `JOB_PARTIAL_COMPLETED`, `JOB_FAILED` — _US-3_
- [x] Velasari adds `ZoneFailure` model to `src/models.py` with fields: `zone_name`, `error` — _US-3_
- [x] Velasari adds `JobStatusUpdate` model to `src/models.py` with fields: `job_id`, `status`, `zone_name`, `step_name`, `step_number`, `total_steps`, `zones_completed`, `zones_total` (running count), `zones_failed` (list of `ZoneFailure`), `error`, `timestamp` — _US-3_
- [x] Velasari adds `MessageType.RESEARCH_JOB` and `MessageType.JOB_STATUS_UPDATE` enum values to `MessageType` in `src/models.py` — _US-1, US-3_
- [x] Velasari modifies `ResearchCheckpoint` in `src/models.py`: remove `progression_queue`, `priority_queue`, `completed_zones`, `failed_zones` fields; add `job_id: str` field — _US-2_
- [x] Velasari adds `BudgetState` model to `src/models.py` with fields: `daily_tokens_used`, `last_reset_date` — _US-2_

## 2. Config (`src/config.py`, `.env.example`)

- [x] Velasari removes `STARTING_ZONE` and `RESEARCH_CYCLE_DELAY_MINUTES` from `src/config.py` and `.env.example` — _US-4_
- [x] Velasari renames `PER_CYCLE_TOKEN_BUDGET` to `PER_ZONE_TOKEN_BUDGET` in `src/config.py` and `.env.example` — _US-1_
- [x] Velasari adds `JOB_QUEUE` (default `agent.world_lore_researcher.jobs`) and `STATUS_QUEUE` (default `agent.world_lore_researcher.status`) to `src/config.py` and `.env.example` — _US-1, US-3_

## 3. Checkpoint (`src/checkpoint.py`)

- [x] Velasari updates `save_checkpoint` in `src/checkpoint.py` to accept a `checkpoint_key: str` parameter instead of using hardcoded `AGENT_ID` — _US-2_
- [x] Velasari updates `load_checkpoint` in `src/checkpoint.py` to accept a `checkpoint_key: str` parameter — _US-2_
- [x] Velasari updates `delete_checkpoint` in `src/checkpoint.py` to accept a `checkpoint_key: str` parameter — _US-2_
- [x] Velasari adds `list_checkpoints(prefix: str) -> list[str]` to `src/checkpoint.py` that queries Storage MCP for checkpoint keys matching a prefix (for crash recovery scanning) — _US-2_
- [x] Velasari adds `save_budget(budget: BudgetState)` and `load_budget() -> BudgetState` to `src/checkpoint.py`, using composite key `{AGENT_ID}:budget` — _US-2_
- [x] Velasari updates `check_daily_budget_reset`, `is_daily_budget_exhausted`, `add_tokens_used` in `src/checkpoint.py` to operate on `BudgetState` instead of `ResearchCheckpoint` — _US-2_

## 4. Pipeline (`src/pipeline.py`)

- [x] Velasari adds `skip_steps: set[str] | None = None` parameter to `run_pipeline` in `src/pipeline.py` — when a step name is in `skip_steps`, log a skip message and advance `current_step` without executing — _US-1_
- [x] Velasari modifies `step_discover_connected_zones` in `src/pipeline.py`: remove filter against `checkpoint.completed_zones` and `checkpoint.progression_queue`; remove `checkpoint.progression_queue.extend()`; keep `researcher.discover_connected_zones()` call and `step_data["discovered_zones"]` write — _US-1_

## 5. Daemon (`src/daemon.py`)

- [x] Velasari removes `_main_loop`, `_pick_next_zone`, and all `STARTING_ZONE`/`RESEARCH_CYCLE_DELAY_MINUTES` usage from `Daemon` in `src/daemon.py` — _US-4_
- [x] Velasari adds `_declare_queues()` to `Daemon` in `src/daemon.py` — declares job queue and status queue on RabbitMQ startup — _US-1_
- [x] Velasari adds `_publish_status(update: JobStatusUpdate)` to `Daemon` in `src/daemon.py` — wraps status in `MessageEnvelope` and publishes to status queue — _US-3_
- [x] Velasari adds `_on_job_message(message)` to `Daemon` in `src/daemon.py` — parses `ResearchJob` from `MessageEnvelope`, calls `_execute_job`, acks on success, nacks (requeue=false) on total failure — _US-1, US-5_
- [x] Velasari adds `_execute_job(job: ResearchJob)` to `Daemon` in `src/daemon.py` — the wave-loop job executor:
  - [x] Publishes `ACCEPTED` status on entry — _US-3_
  - [x] Scans for existing per-zone checkpoints (`{agent_id}:{job_id}:*`) for crash recovery — skips fully completed zones, resumes partial zones — _US-2_
  - [x] Runs `while zones_pending and current_depth <= max_depth` loop — pops zone, creates/loads checkpoint, calls `run_pipeline` with `skip_steps={"discover_connected_zones"}` for depth 0 or last-wave zones — _US-1_
  - [x] After each zone pipeline, reads `step_data["discovered_zones"]` and appends new zones to `zones_pending` (deduplicated against `zones_completed` and `zones_pending`) — _US-1_
  - [x] Publishes `ZONE_STARTED`, `ZONE_COMPLETED` status per zone; publishes `STEP_PROGRESS` per pipeline step — _US-3_
  - [x] On per-zone failure in multi-zone job: logs error, records `ZoneFailure`, continues with remaining zones — _US-2_
  - [x] On completion: publishes `JOB_COMPLETED` (all succeeded) or `JOB_PARTIAL_COMPLETED` (some failed, with `zones_failed`) — _US-3_
  - [x] Cleans up all per-zone checkpoints for the job only after successful ack — _US-2_
- [x] Velasari wires RabbitMQ consumer in `Daemon.run()` with `prefetch_count=1`, consuming from `JOB_QUEUE`, callback to `_on_job_message` — _US-5, US-4_

## 6. Tests

- [x] Velasari updates unit tests for `ResearchCheckpoint` — removed fields, added `job_id` — _US-2_
- [x] Velasari adds unit tests for `ResearchJob`, `JobStatus`, `JobStatusUpdate`, `ZoneFailure`, `BudgetState` models — _US-1, US-3_
- [x] Velasari adds unit tests for checkpoint functions: composite key save/load/delete, `list_checkpoints`, `save_budget`/`load_budget` — _US-2_
- [x] Velasari adds unit tests for `run_pipeline` `skip_steps` behavior — verifies skipped steps are not executed — _US-1_
- [x] Velasari adds unit tests for modified `step_discover_connected_zones` — verifies no filtering, pure discovery write to `step_data` — _US-1_
- [x] Velasari adds unit tests for `_execute_job`: single zone depth 0, multi-zone depth 1, crash recovery (existing checkpoints skipped), partial failure — _US-1, US-2, US-3_
- [x] Velasari adds unit tests for `_on_job_message`: valid job parsing, invalid message handling, ack/nack behavior — _US-1, US-5_
- [x] Velasari adds unit tests for `_publish_status` — verifies envelope construction and queue publishing — _US-3_
- [x] Velasari adds integration test: submit `ResearchJob` to RabbitMQ → daemon picks up → status updates emitted → research package published to validator queue — _US-1, US-3_
