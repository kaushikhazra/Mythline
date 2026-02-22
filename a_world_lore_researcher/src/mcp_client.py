"""MCP client helpers — dual transport support.

StreamableHTTP for Storage and Web Search MCPs.
REST API for crawl4ai (its built-in MCP SSE endpoint has a Starlette
middleware bug, but its REST API works perfectly).

Each MCP call creates a fresh session (initialize -> tool call -> close).
The per-call overhead is negligible for a daemon running every 5 minutes.
"""

from __future__ import annotations

import json
import logging

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from src.config import MCP_WEB_CRAWLER_URL

logger = logging.getLogger(__name__)


async def mcp_call(
    url: str,
    tool_name: str,
    arguments: dict,
    timeout: float = 30.0,
    sse_read_timeout: float = 300.0,
) -> dict | list | str | None:
    """Call a tool on a remote MCP service via StreamableHTTP.

    Establishes a fresh session, initializes the MCP handshake, calls the
    tool, and tears down cleanly.
    """
    async with streamablehttp_client(url, timeout=timeout, sse_read_timeout=sse_read_timeout) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(tool_name, arguments)

            if result.isError:
                error_text = _extract_all_text(result)
                logger.error("MCP tool %s error: %s", tool_name, error_text)
                return None

            return _parse_result(result)


# ---------------------------------------------------------------------------
# Web Crawler helpers (crawl4ai REST API)
# ---------------------------------------------------------------------------

async def crawl_url(url: str, include_links: bool = True, include_tables: bool = True) -> dict:
    """Crawl a single URL via crawl4ai's REST API and return markdown content.

    Uses the /md endpoint. include_links/include_tables kept for interface
    compatibility but crawl4ai handles content extraction holistically.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{MCP_WEB_CRAWLER_URL}/md",
                json={"url": url, "f": "raw", "c": "0"},
            )

            if response.status_code != 200:
                logger.warning("crawl4ai returned %s for %s", response.status_code, url)
                return {"url": url, "title": "", "content": None, "error": f"HTTP {response.status_code}"}

            data = response.json()
            markdown = data.get("markdown", "")

            if not markdown:
                return {"url": url, "title": "", "content": None, "error": "No content extracted"}

            return {"url": url, "title": "", "content": markdown, "error": None}

    except httpx.HTTPError as exc:
        logger.warning("crawl4ai HTTP error for %s: %s", url, exc)
        return {"url": url, "title": "", "content": None, "error": str(exc)}
    except Exception as exc:
        logger.error("crawl4ai unexpected error for %s: %s", url, exc, exc_info=True)
        return {"url": url, "title": "", "content": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Result parsing (for MCP calls)
# ---------------------------------------------------------------------------

def _parse_result(result) -> dict | list | str | None:
    """Parse a CallToolResult into Python objects.

    FastMCP serializes list[dict] returns as multiple TextContent blocks
    (one per item). Single-value returns use a single block. This function
    handles both cases:
    - Multiple blocks -> collect, parse each, return as list
    - Single block -> parse and return the value directly
    """
    texts = [block.text for block in result.content if isinstance(block, TextContent)]

    if not texts:
        return None

    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except (json.JSONDecodeError, TypeError):
            return texts[0]

    # Multiple blocks — each is a separate JSON value (FastMCP list[dict] behavior)
    parsed = []
    for text in texts:
        try:
            parsed.append(json.loads(text))
        except (json.JSONDecodeError, TypeError):
            parsed.append(text)
    return parsed


def _extract_all_text(result) -> str:
    """Concatenate all text content blocks for error messages."""
    return " ".join(block.text for block in result.content if isinstance(block, TextContent))
