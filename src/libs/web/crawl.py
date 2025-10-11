from crawl4ai import AsyncWebCrawler

async def crawl_content(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        return result.markdown
