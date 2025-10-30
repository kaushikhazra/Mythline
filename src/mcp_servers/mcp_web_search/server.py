import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.duck_duck_go import search
from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
server = FastMCP(name="Web Search MCP", port=port)

@server.tool()
async def web_search(query: str) -> str:
    """Searches the web using DuckDuckGo and crawls the top results to fetch their content.
    Args:
        query (str): The search query to look for
    Return:
        (str): Combined content from the top search results
    """

    print(f"Searching for : {query}")

    content = ""
    search_results = search(query)
    for result in search_results:
        page_content = await crawl_content(result['href'])
        content += f"{result['href']} \n\n {page_content} \n\n"
        print(f"{result['href']} \n\n {page_content} \n\n","...")

    return content

if __name__=='__main__':
    server.run(transport='streamable-http')
