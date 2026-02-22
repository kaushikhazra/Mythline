# Research Job Queue — Design

## Overview

Transform the World Lore Researcher daemon from a self-driving loop into a job consumer. The daemon starts, connects to RabbitMQ, and blocks on a job queue. When a job arrives, it executes the research pipeline for the requested zone(s) at the requested depth, reports progress, and waits for the next job.

---

## 1. Job Message Schema

A new Pydantic model for the inbound job message:

```python
class ResearchJob(BaseModel):
    job_id: str                # UUID, assigned by the sender
    zone_name: str             # Root zone to research (e.g., "elwynn_forest")
    depth: int = 0             # 0 = root only, 1 = root + neighbors, 2 = root + neighbors + their neighbors
    game: str = "wow"          # Target game
    requested_by: str = ""     # Who requested (user ID or "system")
    requested_at: datetime     # When the job was submitted
```

This arrives as the `payload` inside an existing `MessageEnvelope` with `message_type = MessageType.RESEARCH_JOB`.

New `MessageType` enum value: `RESEARCH_JOB = "research_job"`.

---

## 2. Job Status Message Schema

```python
class JobStatus(str, Enum):
    ACCEPTED = "accepted"            # Job received, starting
    ZONE_STARTED = "zone_started"    # Beginning research on a zone
    STEP_PROGRESS = "step_progress"  # Pipeline step completed within a zone
    ZONE_COMPLETED = "zone_completed"  # Zone research finished
    JOB_COMPLETED = "job_completed"  # All zones in job scope done (full success)
    JOB_PARTIAL_COMPLETED = "job_partial_completed"  # Some zones succeeded, some failed
    JOB_FAILED = "job_failed"        # Job failed entirely (with reason)

class JobStatusUpdate(BaseModel):
    job_id: str
    status: JobStatus
    zone_name: str = ""
    step_name: str = ""
    step_number: int = 0
    total_steps: int = 0
    zones_completed: int = 0
    zones_total: int = 0             # Running count — grows as zones are discovered. Only final at JOB_COMPLETED/JOB_PARTIAL_COMPLETED.
    zones_failed: list[ZoneFailure] = Field(default_factory=list)  # Populated on JOB_PARTIAL_COMPLETED
    error: str = ""
    timestamp: datetime = Field(default_factory=_now)

class ZoneFailure(BaseModel):
    zone_name: str
    error: str
```

Published to a dedicated status queue: `agent.world_lore_researcher.status`.

New `MessageType` enum value: `JOB_STATUS_UPDATE = "job_status_update"`.

---

## 3. Queue Topology

| Queue | Direction | Purpose |
|-------|-----------|---------|
| `agent.world_lore_researcher.jobs` | Inbound | Job submissions (consumed by researcher) |
| `agent.world_lore_researcher.status` | Outbound | Status updates (published by researcher) |
| `agent.world_lore_validator` | Outbound | Research packages (existing, unchanged) |

The researcher declares and consumes from the `.jobs` queue. It publishes to `.status` and `.validator` queues.

---

## 4. Daemon Restructure

### Current Flow (remove)
```
start → load checkpoint → loop { pick_next_zone → run_pipeline → sleep } → shutdown
```

### New Flow
```
start → connect RabbitMQ → declare queues → consume(.jobs, prefetch=1) → on_message:
    parse ResearchJob from envelope
    publish status(ACCEPTED)
    scan for existing checkpoints (crash recovery — skip completed zones, resume partial)
    while zones_pending and current_depth <= max_depth:
        zone = zones_pending.pop(0)
        publish status(ZONE_STARTED)
        create or load per-zone checkpoint
        run_pipeline(checkpoint, researcher, publish_fn, skip_steps)
        publish status(ZONE_COMPLETED)
        if current_depth < max_depth: append discovered zones to zones_pending (deduplicated)
    clean up all per-zone checkpoints for this job
    publish status(JOB_COMPLETED)
    ack message
```

### Key Changes to `Daemon`

- **Remove** `_main_loop`, `_pick_next_zone`, `STARTING_ZONE` config usage.
- **Remove** `RESEARCH_CYCLE_DELAY_MINUTES` — no polling, no sleep.
- **Add** `_on_job_message(message)` — the callback for incoming jobs.
- **Add** `_declare_queues()` — declare job and status queues on startup.
- **Add** `_publish_status(update: JobStatusUpdate)` — helper to emit status updates.
- **Add** `_execute_job(job: ResearchJob)` — the wave-loop job executor. Manages `zones_pending`, `zones_completed`, depth tracking, and crash recovery. Zone discovery is incremental — the full zone list is unknowable at job start.

### Zone Expansion (Depth)

Depth expansion uses the existing `discover_connected_zones` pipeline step, but restructured:

1. **Depth 0**: Research only the root zone. Skip step 8 (discover connected zones) entirely.
2. **Depth 1**: Research root zone with step 8 enabled. The discovered zones become the next batch. Research each of those with step 8 disabled.
3. **Depth N**: Repeat — each wave discovers the next wave's targets, up to N waves total.

This means zone discovery happens incrementally during execution, not upfront. The daemon can't know the full zone list at job start — it builds it wave by wave.

### Zone List Tracking

The job executor maintains:
```python
zones_completed: list[str] = []
zones_pending: list[str] = [root_zone]
current_depth: int = 0
max_depth: int = job.depth
```

After each zone completes, if `current_depth < max_depth`, newly discovered zones are appended to `zones_pending`. Zones already in `zones_completed` or `zones_pending` are deduplicated.

### Crash Recovery — Zone Progress Persistence

Per-zone checkpoints are **not cleaned up** until the entire job acks successfully. This means on crash recovery:

1. RabbitMQ redelivers the unacked job message.
2. On job start, the daemon scans for existing per-zone checkpoints matching `{agent_id}:{job_id}:*`.
3. Any zone with a checkpoint at `current_step == TOTAL_STEPS` (fully completed) is added to `zones_completed` and skipped.
4. Any zone with a checkpoint at a partial step is resumed from that step.
5. Only after the job acks successfully does the daemon clean up all per-zone checkpoints for that job.

This prevents duplicate research packages — completed zones are detected and skipped on redelivery.

**Checkpoint scan**: Add a `list_checkpoints(prefix: str) -> list[str]` function to `checkpoint.py` that queries Storage MCP for all checkpoint keys matching a prefix. The Storage MCP's `agent_id` parameter accepts arbitrary string keys, so `{agent_id}:{job_id}:` works as a prefix query. If the MCP doesn't support prefix queries natively, the daemon can query by known zone names from the job context.

---

## 5. Checkpoint Changes

### Current (remove)
Single global checkpoint per agent — tracks the ongoing zone, progression queue, completed zones, budget.

### New
Per-job, per-zone checkpoint. The checkpoint key becomes `{agent_id}:{job_id}:{zone_name}` instead of just `{agent_id}`.

The `ResearchCheckpoint` model changes:
- **Remove**: `progression_queue`, `priority_queue`, `completed_zones`, `failed_zones` — these were autonomous-mode concepts.
- **Keep**: `zone_name`, `current_step`, `step_data` — still needed for crash resilience within a zone pipeline.
- **Add**: `job_id` — correlates checkpoint to its parent job.

```python
class ResearchCheckpoint(BaseModel):
    job_id: str
    zone_name: str
    current_step: int = 0
    step_data: dict = Field(default_factory=dict)
    daily_tokens_used: int = 0
    last_reset_date: str = ""
```

Budget tracking (`daily_tokens_used`, `last_reset_date`) stays on the checkpoint but is shared across the agent instance — not per-job. This needs a separate budget checkpoint keyed by `{agent_id}:budget`.

### Budget Checkpoint Functions

Add to `checkpoint.py`:

```python
async def save_budget(budget: BudgetState) -> None:
    """Save budget state. Uses the same MCP tool with composite key."""
    await mcp_call(MCP_STORAGE_URL, "save_checkpoint",
        {"agent_id": f"{AGENT_ID}:budget", "state": budget.model_dump_json()})

async def load_budget() -> BudgetState:
    """Load budget state. Returns fresh state if none exists."""
    result = await mcp_call(MCP_STORAGE_URL, "load_checkpoint",
        {"agent_id": f"{AGENT_ID}:budget"})
    # ... parse or return default BudgetState

class BudgetState(BaseModel):
    daily_tokens_used: int = 0
    last_reset_date: str = ""
```

The Storage MCP's `save_checkpoint` tool uses `agent_id` as a SurrealDB record ID (`research_state:{agent_id}`). It accepts arbitrary string keys — composite keys like `world_lore_researcher:budget` work without MCP changes.

---

## 6. Pipeline Changes

### Step 8: Discover Connected Zones

Currently writes to `checkpoint.progression_queue` and filters against `checkpoint.completed_zones`. Both fields are removed from `ResearchCheckpoint` in section 5, so **step 8 must be modified**.

Changes to `step_discover_connected_zones`:
- **Remove** the filter against `checkpoint.completed_zones` and `checkpoint.progression_queue` — these fields no longer exist.
- **Keep** the call to `researcher.discover_connected_zones(checkpoint.zone_name)`.
- **Keep** writing all discovered zone slugs to `step_data["discovered_zones"]`.
- The step becomes a pure discovery function — it reports what it finds. Deduplication (against already-completed and already-pending zones) is the daemon's job executor responsibility, which has the `zones_completed` and `zones_pending` lists.

Skipping for depth 0:
- **Depth 0 jobs**: The daemon passes `skip_steps={"discover_connected_zones"}` to `run_pipeline`. See `run_pipeline` signature change below.
- **Depth > 0 jobs**: Step runs normally. The daemon reads `step_data["discovered_zones"]` after the pipeline completes and decides whether to queue them based on remaining depth.

### `run_pipeline` Signature

Add an optional `skip_steps` parameter:

```python
async def run_pipeline(
    checkpoint: ResearchCheckpoint,
    researcher: LoreResearcher,
    publish_fn: Callable | None = None,
    skip_steps: set[str] | None = None,
) -> ResearchCheckpoint:
```

When a step name is in `skip_steps`, the pipeline logs a skip message and advances `current_step` without executing the step function. This keeps the pipeline generic — it doesn't know about depth semantics.

---

## 7. Config Changes

### Remove
- `STARTING_ZONE` — no default zone; everything is job-driven.
- `RESEARCH_CYCLE_DELAY_MINUTES` — no polling.

### Keep
- `DAILY_TOKEN_BUDGET` — daily guardrail, shared across all jobs via the budget checkpoint.
- `PER_ZONE_TOKEN_BUDGET` (renamed from `PER_CYCLE_TOKEN_BUDGET`) — per-zone guardrail. The pipeline runs once per zone, so per-zone is the natural scope. Checked before each pipeline run; if the zone's token usage exceeds this limit, the zone fails with a budget error.
- `MAX_RESEARCH_VALIDATE_ITERATIONS` — validation loop cap.
- `RATE_LIMIT_REQUESTS_PER_MINUTE` — rate limiting.
- All MCP/RabbitMQ connection strings.
- `AGENT_ID`, `AGENT_ROLE`, `GAME_NAME`.

### Add
- `JOB_QUEUE` — defaults to `agent.world_lore_researcher.jobs`.
- `STATUS_QUEUE` — defaults to `agent.world_lore_researcher.status`.

---

## 8. Error Handling

- **Job-level failure**: If a zone pipeline fails after retries, publish `JOB_FAILED` with the error, nack the message (with requeue=false so it goes to DLQ if configured), and clean up the checkpoint.
- **Per-zone failure within a multi-zone job**: Log the failure, skip the zone, continue with remaining zones. If any zones failed, publish `JOB_PARTIAL_COMPLETED` (not `JOB_COMPLETED`) with `zones_failed` listing each failed zone and its error.
- **Budget exhaustion mid-job**: Publish `JOB_FAILED` with reason "daily token budget exhausted". The job can be retried after budget resets.
- **Crash recovery**: On restart, the daemon doesn't auto-resume old jobs. Unacked messages return to the queue (RabbitMQ handles this). On redelivery, the daemon scans for existing per-zone checkpoints to determine which zones are already completed (skipped) and which are partially done (resumed from last checkpointed step). See section 4 "Crash Recovery" for details.

---

## 9. Files Changed

| File | Change |
|------|--------|
| `src/models.py` | Add `ResearchJob`, `JobStatus`, `JobStatusUpdate`. Add `MessageType.RESEARCH_JOB`, `MessageType.JOB_STATUS_UPDATE`. Modify `ResearchCheckpoint` (remove autonomous fields, add `job_id`). |
| `src/daemon.py` | Rewrite — job consumer model replacing autonomous loop. |
| `src/config.py` | Remove `STARTING_ZONE`, `RESEARCH_CYCLE_DELAY_MINUTES`. Rename `PER_CYCLE_TOKEN_BUDGET` to `PER_ZONE_TOKEN_BUDGET`. Add `JOB_QUEUE`, `STATUS_QUEUE`. |
| `src/checkpoint.py` | Update checkpoint key format to `{agent_id}:{job_id}:{zone_name}`. Add `save_budget()`/`load_budget()` with `BudgetState` model. Add `list_checkpoints(prefix)` for crash recovery scanning. Update `delete_checkpoint()` to accept composite keys. |
| `src/pipeline.py` | Modify `step_discover_connected_zones` — remove filters against removed checkpoint fields, keep as pure discovery. Add `skip_steps` parameter to `run_pipeline`. |
| Tests | Update to reflect new daemon, models, and checkpoint key format. |

---

## 10. Future Work (Out of Scope)

- **Deduplication across manual job resubmissions**: If a job fails and a user submits a new job (new `job_id`) for the same zone, the daemon will re-research it. Crash recovery (section 4) handles in-flight failures by retaining checkpoints, but manual resubmissions are intentionally treated as fresh jobs. Acceptable for now — a future optimization could check Storage MCP for existing research packages before re-researching.
- **Move shared message schemas to `shared/`**: `MessageEnvelope`, `MessageType`, `ResearchJob`, `JobStatusUpdate`, and `ZoneFailure` are currently in agent-local `src/models.py`. CLAUDE.md says `shared/` should contain "Pydantic models for RabbitMQ message schemas." As other researchers (Quest Lore, Character, etc.) adopt the job queue pattern, these schemas should be extracted to `shared/` to avoid duplication. Not addressed here because the requirement scopes this to the World Lore Researcher only.
