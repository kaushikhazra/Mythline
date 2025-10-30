import asyncio
from dotenv import load_dotenv
from src.libs.web.crawl import crawl_content

load_dotenv()

async def main():
    content = await crawl_content('https://warcraft.wiki.gg/wiki/Krixel_Pinchwhistle')
    print(content)

if __name__ == '__main__':
    asyncio.run(main())