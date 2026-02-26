FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY s_wiki_crawler/pyproject.toml .
RUN uv pip install --system --no-cache .

COPY shared/ shared/
COPY s_wiki_crawler/src/ src/
COPY s_wiki_crawler/config/ config/

CMD ["python", "-m", "src.daemon"]
