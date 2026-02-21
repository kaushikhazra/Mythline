"""MCP client helpers for calling remote MCP services via HTTP JSON-RPC."""

from __future__ import annotations

import json

import httpx

from src.config import MCP_WEB_SEARCH_URL, MCP_WEB_CRAWLER_URL


async def mcp_call(url: str, tool_name: str, arguments: dict, timeout: float = 60.0) -> dict | list | str | None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        text = _extract_text(result)
        if text is None:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text


async def web_search(query: str, max_results: int = 0) -> list[dict]:
    result = await mcp_call(MCP_WEB_SEARCH_URL, "search", {"query": query, "max_results": max_results})
    return result if isinstance(result, list) else []


async def web_search_news(query: str, max_results: int = 0, timelimit: str = "w") -> list[dict]:
    result = await mcp_call(MCP_WEB_SEARCH_URL, "search_news", {"query": query, "max_results": max_results, "timelimit": timelimit})
    return result if isinstance(result, list) else []


async def crawl_url(url: str, include_links: bool = True, include_tables: bool = True) -> dict:
    result = await mcp_call(MCP_WEB_CRAWLER_URL, "crawl_url", {"url": url, "include_links": include_links, "include_tables": include_tables})
    return result if isinstance(result, dict) else {"url": url, "content": None, "error": "Invalid response"}


async def crawl_urls(urls: list[str], include_links: bool = True) -> list[dict]:
    result = await mcp_call(MCP_WEB_CRAWLER_URL, "crawl_urls", {"urls": urls, "include_links": include_links})
    return result if isinstance(result, list) else []


def _extract_text(response_json: dict) -> str | None:
    result = response_json.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content, list):
        for item in content:
            if item.get("type") == "text":
                return item.get("text")
    return None
