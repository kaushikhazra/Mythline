"""Web Search MCP Service — DuckDuckGo search integration for Mythline."""

import asyncio
import os

from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

MCP_WEB_SEARCH_PORT = int(os.getenv("MCP_WEB_SEARCH_PORT", "8006"))
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "10"))

server = FastMCP(name="Web Search Service", port=MCP_WEB_SEARCH_PORT)


def _search_sync(query: str, max_results: int) -> list[dict]:
    """Run DuckDuckGo text search synchronously."""
    results = DDGS().text(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in results
    ]


def _search_news_sync(query: str, max_results: int, timelimit: str) -> list[dict]:
    """Run DuckDuckGo news search synchronously."""
    results = DDGS().news(query, max_results=max_results, timelimit=timelimit)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("body", ""),
            "date": r.get("date", ""),
            "source": r.get("source", ""),
        }
        for r in results
    ]


@server.tool()
async def search(query: str, max_results: int = 0) -> list[dict]:
    """Search the web using DuckDuckGo and return results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return. Defaults to
                     SEARCH_MAX_RESULTS env var (default 10).

    Returns:
        A list of search results, each with 'title', 'url', and 'snippet' fields.
    """
    if not query.strip():
        raise ValueError("Query must not be empty")

    limit = max_results if max_results > 0 else SEARCH_MAX_RESULTS
    return await asyncio.to_thread(_search_sync, query, limit)


@server.tool()
async def search_news(query: str, max_results: int = 0, timelimit: str = "w") -> list[dict]:
    """Search for recent news articles using DuckDuckGo.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        timelimit: Time filter - "d" (day), "w" (week), "m" (month).

    Returns:
        A list of news results with 'title', 'url', 'snippet', 'date', and 'source'.
    """
    if not query.strip():
        raise ValueError("Query must not be empty")

    limit = max_results if max_results > 0 else SEARCH_MAX_RESULTS
    return await asyncio.to_thread(_search_news_sync, query, limit, timelimit)


if __name__ == "__main__":
    server.run(transport="streamable-http")
