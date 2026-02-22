# Research Job Queue — Requirements

## Overview

Replace the autonomous daemon loop in the World Lore Researcher with a job-based model. The researcher waits for structured job messages on a RabbitMQ queue, executes exactly the requested scope, and stops. No self-driven zone crawling.

This pattern will apply to all knowledge acquisition agents (not just World Lore), but World Lore Researcher is the first implementation.

---

## User Stories

### US-1: Submit a Research Job

**As a** user interacting with the Mythline UI,
**I want to** say "Research Elwynn Forest, depth 2" in natural language,
**so that** the system researches Elwynn Forest and its directly connected zones (one level of neighbors).

**Acceptance Criteria:**
- The user's natural language request is parsed upstream (UI/backend — out of scope here) into a structured job message.
- The structured job message arrives on a RabbitMQ queue that the researcher consumes.
- The researcher processes the root zone, then discovers and processes connected zones up to the requested depth.
- Depth 0 = root zone only. Depth 1 = root + its immediate neighbors. Depth 2 = root + neighbors + their neighbors.
- The researcher stops after completing the requested scope. It does not autonomously continue.

### US-2: Job Isolation

**As a** system operator,
**I want** each research job to be self-contained,
**so that** one job's failure doesn't corrupt another job's state.

**Acceptance Criteria:**
- Each job has its own checkpoint state, keyed by job ID.
- A failed job can be retried without affecting other jobs.
- Completed jobs clean up their checkpoint state.

### US-3: Job Status Reporting

**As a** user,
**I want to** know what the researcher is doing,
**so that** I can see progress in the UI.

**Acceptance Criteria:**
- The researcher publishes status updates to RabbitMQ as it progresses through a job.
- Status messages include: job accepted, zone research started, pipeline step progress, zone completed, job completed, job failed.
- Status messages include the job ID for correlation.

### US-4: Graceful Idle

**As a** system operator,
**I want** the researcher to idle cleanly when there are no jobs,
**so that** it doesn't consume resources or spam logs.

**Acceptance Criteria:**
- When no jobs are queued, the researcher blocks on the RabbitMQ consumer (no polling, no sleep loops).
- The daemon remains responsive to shutdown signals while idle.

### US-5: Sequential Job Processing

**As a** system operator,
**I want** jobs processed one at a time,
**so that** resource usage (LLM tokens, crawling) is predictable.

**Acceptance Criteria:**
- The researcher processes one job at a time. It does not prefetch or parallelize jobs.
- RabbitMQ prefetch count is set to 1.
- If multiple jobs are queued, they execute in FIFO order.

---

## Out of Scope

- Natural language parsing of user requests (handled by UI/backend layer).
- Job prioritization or reordering (FIFO is sufficient for now).
- Multiple concurrent researchers (single instance per domain).
- UI implementation (this spec covers the researcher's queue consumer and job execution).
