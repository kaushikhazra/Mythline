FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY mcp_storage/pyproject.toml .
RUN uv pip install --system --no-cache .

COPY shared/ shared/
COPY mcp_storage/src/ src/

EXPOSE 8005

CMD ["python", "-m", "src.server"]
