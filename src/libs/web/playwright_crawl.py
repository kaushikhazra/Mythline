import re
import asyncio
from playwright.async_api import async_playwright


async def crawl_content(url: str, headless: bool = False, wait_for_cloudflare: bool = True) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        await page.goto(url)

        if wait_for_cloudflare:
            await _wait_for_cloudflare(page)

        content = await page.content()
        markdown = _html_to_markdown(content)
        cleaned = _clean_markdown(markdown)

        await browser.close()

        return cleaned


async def _wait_for_cloudflare(page, timeout: int = 60):
    for i in range(timeout):
        title = await page.title()
        if "just a moment" not in title.lower() and "cloudflare" not in title.lower():
            await asyncio.sleep(1)
            return

        if i == 3:
            await _try_click_turnstile(page)

        await asyncio.sleep(1)

    raise TimeoutError("Cloudflare challenge did not resolve")


async def _try_click_turnstile(page):
    try:
        await page.mouse.move(500, 400)
        await asyncio.sleep(0.5)

        iframe_selectors = [
            "iframe[src*='challenges.cloudflare.com']",
            "iframe[src*='turnstile']",
            "iframe[title*='cloudflare']",
            "iframe[title*='Cloudflare']",
            "#turnstile-wrapper iframe",
            ".cf-turnstile iframe"
        ]

        for selector in iframe_selectors:
            try:
                frame = page.frame_locator(selector)
                box = await frame.locator("body").bounding_box()
                if box:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    await page.mouse.move(center_x, center_y)
                    await asyncio.sleep(0.3)
                    await page.mouse.click(center_x, center_y)
                    print(f"[*] Clicked Turnstile iframe: {selector}")
                    return
            except Exception:
                continue

        turnstile_div = page.locator("[class*='turnstile']").first
        if await turnstile_div.count() > 0:
            await turnstile_div.click()
            print("[*] Clicked Turnstile div")
            return

        verify_box = page.locator("text=Verify you are human").first
        if await verify_box.count() > 0:
            box = await verify_box.bounding_box()
            if box:
                await page.mouse.click(box['x'] + 20, box['y'] + box['height'] / 2)
                print("[*] Clicked near verify text")

    except Exception as e:
        print(f"[!] Turnstile click failed: {e}")


def _html_to_markdown(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript']):
        tag.decompose()

    main_content = soup.find('main') or soup.find('article') or soup.find('div', {'id': 'content'}) or soup.find('div', {'id': 'mw-content-text'}) or soup.body

    if not main_content:
        return ""

    lines = []
    _extract_text(main_content, lines)

    return '\n'.join(lines)


def _extract_text(element, lines, depth=0):
    from bs4 import NavigableString, Tag

    if isinstance(element, NavigableString):
        text = str(element).strip()
        if text:
            lines.append(text)
        return

    if not isinstance(element, Tag):
        return

    tag_name = element.name

    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag_name[1])
        text = element.get_text(strip=True)
        if text:
            lines.append(f"\n{'#' * level} {text}\n")
        return

    if tag_name == 'p':
        text = element.get_text(strip=True)
        if text:
            lines.append(f"{text}\n")
        return

    if tag_name == 'li':
        text = element.get_text(strip=True)
        if text:
            lines.append(f"- {text}")
        return

    if tag_name in ['ul', 'ol']:
        for child in element.children:
            _extract_text(child, lines, depth + 1)
        lines.append("")
        return

    if tag_name == 'br':
        lines.append("")
        return

    if tag_name in ['table']:
        text = element.get_text(separator=' | ', strip=True)
        if text:
            lines.append(f"{text}\n")
        return

    for child in element.children:
        _extract_text(child, lines, depth)


def _clean_markdown(markdown: str) -> str:
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', markdown)
    cleaned = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', cleaned)
    cleaned = re.sub(r'https?://[^\s\)]+', '', cleaned)
    cleaned = re.sub(r'^\[[^\]]+\]:\s+.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()

    return cleaned
