# Agent Docker Conventions

How every agent is containerized and wired into docker-compose.

---

## Dockerfile

Build context is the **repo root** (not the agent folder), so `shared/` is accessible.

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY a_{agent_name}/pyproject.toml .
RUN uv pip install --system --no-cache .

COPY shared/ shared/
COPY a_{agent_name}/src/ src/
COPY a_{agent_name}/config/ config/
COPY a_{agent_name}/prompts/ prompts/

CMD ["python", "-m", "src.main"]
```

**Key decisions:**
- `uv` for fast dependency installation
- `--system` installs into system Python (no venv in container)
- `shared/` copied alongside agent code — importable as `shared.prompt_loader` etc.
- `config/` and `prompts/` copied as-is — agent code resolves them relative to `__file__`
- `CMD` names the agent's entry point module — could be `src.daemon`, `src.consumer`, `src.main`, etc. depending on invocation model

---

## docker-compose.yml

```yaml
  {agent-name}:
    build:
      context: .                              # Repo root — required for shared/
      dockerfile: a_{agent_name}/Dockerfile   # Agent-specific Dockerfile
    environment:
      AGENT_ID: {agent_name}
      # ... all env vars with defaults
    depends_on:
      mcp-storage:
        condition: service_healthy
      # ... other dependencies
    restart: unless-stopped
```

**Key decisions:**
- `context: .` (repo root) — not the agent folder. This is required because the Dockerfile needs to `COPY shared/`.
- `dockerfile:` points to the agent's specific Dockerfile
- All env vars are explicit in compose — no reliance on `.env` files in Docker
- `depends_on` with `service_healthy` — agents don't start until their MCP services are ready
- `restart: unless-stopped` — long-running agents should self-recover on crash

---

## Environment Variable Flow

```
docker-compose.yml env    →    overrides
.env.example defaults     →    fallback (for local dev only)
config.py os.getenv()     →    code default (final fallback)
```

In Docker, compose env vars are the source of truth. `.env.example` exists only for developer reference and local runs.

---

## Health Checks

Most agents don't expose HTTP endpoints. Health is inferred from:
- Container running + not restarting
- Log output (structured JSON to stdout)
- RabbitMQ message flow (messages being consumed/produced)

Agents that expose HTTP endpoints (e.g., on-demand agents with `api.py`) can add explicit health checks. MCP services and infrastructure services always have health checks (HTTP or command-based).
