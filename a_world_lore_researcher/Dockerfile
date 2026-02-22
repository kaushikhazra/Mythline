FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY a_world_lore_researcher/pyproject.toml .
RUN uv pip install --system --no-cache .

COPY shared/ shared/
COPY a_world_lore_researcher/src/ src/
COPY a_world_lore_researcher/config/ config/
COPY a_world_lore_researcher/prompts/ prompts/

CMD ["python", "-m", "src.daemon"]
