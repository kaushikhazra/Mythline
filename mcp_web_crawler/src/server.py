"""Web Crawler MCP Service — URL content extraction to markdown for Mythline."""

import asyncio
import os

import trafilatura
from mcp.server.fastmcp import FastMCP

MCP_WEB_CRAWLER_PORT = int(os.getenv("MCP_WEB_CRAWLER_PORT", "8007"))

server = FastMCP(name="Web Crawler Service", port=MCP_WEB_CRAWLER_PORT)


def _fetch_and_extract(url: str, include_links: bool, include_tables: bool) -> dict:
    """Fetch a URL and extract its content synchronously."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return {"url": url, "content": None, "error": "Failed to fetch URL"}

    content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_links=include_links,
        include_tables=include_tables,
        with_metadata=False,
    )

    metadata = trafilatura.extract(
        downloaded,
        output_format="json",
        with_metadata=True,
    )

    title = ""
    if metadata:
        import json
        try:
            meta = json.loads(metadata)
            title = meta.get("title", "")
        except (json.JSONDecodeError, TypeError):
            pass

    if not content:
        return {"url": url, "content": None, "error": "No extractable content found"}

    return {
        "url": url,
        "title": title,
        "content": content,
        "error": None,
    }


@server.tool()
async def crawl_url(url: str, include_links: bool = True, include_tables: bool = True) -> dict:
    """Fetch a URL and extract its main content as markdown.

    Uses trafilatura to extract the article/main content from a webpage,
    filtering out navigation, ads, and boilerplate.

    Args:
        url: The URL to crawl and extract content from.
        include_links: Whether to include hyperlinks in the markdown output.
        include_tables: Whether to include tables in the output.

    Returns:
        A dict with 'url', 'title', 'content' (markdown string), and 'error'.
    """
    if not url.strip():
        raise ValueError("URL must not be empty")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return await asyncio.to_thread(_fetch_and_extract, url, include_links, include_tables)


@server.tool()
async def crawl_urls(urls: list[str], include_links: bool = True) -> list[dict]:
    """Fetch multiple URLs and extract their content as markdown.

    Processes URLs concurrently for efficiency.

    Args:
        urls: List of URLs to crawl.
        include_links: Whether to include hyperlinks in the markdown output.

    Returns:
        A list of dicts, each with 'url', 'title', 'content', and 'error'.
    """
    if not urls:
        raise ValueError("URLs list must not be empty")

    tasks = [crawl_url(u, include_links=include_links) for u in urls]
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    server.run(transport="streamable-http")
