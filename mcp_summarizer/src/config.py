"""Configuration loader for the MCP Summarizer service."""

import os

MCP_SUMMARIZER_PORT = int(os.getenv("MCP_SUMMARIZER_PORT", "8007"))
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter:openai/gpt-4o-mini")
DEFAULT_CHUNK_SIZE_TOKENS = int(os.getenv("DEFAULT_CHUNK_SIZE_TOKENS", "8000"))
DEFAULT_CHUNK_OVERLAP_TOKENS = int(os.getenv("DEFAULT_CHUNK_OVERLAP_TOKENS", "500"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "5000"))
