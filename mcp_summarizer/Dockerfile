FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY mcp_summarizer/pyproject.toml .
RUN uv pip install --system --no-cache .

# Pre-download tiktoken encoding data to avoid cold-start delay on first request
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

COPY shared/ shared/
COPY mcp_summarizer/prompts/ prompts/
COPY mcp_summarizer/src/ src/

EXPOSE 8007

CMD ["python", "-m", "src.server"]
