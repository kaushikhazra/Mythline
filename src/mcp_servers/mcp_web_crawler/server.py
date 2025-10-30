import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_CRAWLER_PORT', 8001))
server = FastMCP(name="Web Crawler MCP", port=port)

@server.tool()
async def crawl(url: str) -> str:
    """Crawls content from a given URL and returns it as markdown.
    Args:
        url (str): The URL to crawl content from
    Return:
        (str): The crawled content in markdown format
    """

    print(f"Crawling content from: {url}")

    content = await crawl_content(url)
    content_trimmed = content[:3000]

    print(f"Crawled {len(content)} characters from {url}")

    return content_trimmed

if __name__=='__main__':
    server.run(transport='streamable-http')
