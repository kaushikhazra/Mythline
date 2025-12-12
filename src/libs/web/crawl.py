import re
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, LLMConfig
from crawl4ai.content_filter_strategy import LLMContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def crawl_content(url: str) -> str:

    md_generator = DefaultMarkdownGenerator()

    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        excluded_tags=["nav", "header", "footer", "aside"],
        simulate_user=True
    )

    browser_conf = BrowserConfig( 
        browser_type="chromium",
        headless=True,
        text_mode=True
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(url, config=config)
        markdown_content = result.markdown
        # Remove markdown links [text](url) -> text
        # This regex matches [any text](any url) and replaces with just the text
        cleaned_markdown = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', markdown_content)
        
        # Also remove reference-style links [text][ref] -> text
        cleaned_markdown = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', cleaned_markdown)
        
        # Remove standalone URLs (optional - remove if you want to keep bare URLs)
        # This removes URLs that start with http:// or https://
        cleaned_markdown = re.sub(r'https?://[^\s\)]+', '', cleaned_markdown)
        
        # Clean up any reference definitions at the bottom [ref]: url
        cleaned_markdown = re.sub(r'^\[[^\]]+\]:\s+.*$', '', cleaned_markdown, flags=re.MULTILINE)
        
        # Clean up extra whitespace that might be left
        cleaned_markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_markdown)
        
        return cleaned_markdown
