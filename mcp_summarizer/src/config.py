"""Configuration loader for the MCP Summarizer service."""

import os

MCP_SUMMARIZER_PORT = int(os.getenv("MCP_SUMMARIZER_PORT", "8007"))
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_CHUNK_SIZE_TOKENS = int(os.getenv("DEFAULT_CHUNK_SIZE_TOKENS", "8000"))
DEFAULT_CHUNK_OVERLAP_TOKENS = int(os.getenv("DEFAULT_CHUNK_OVERLAP_TOKENS", "500"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "5000"))
