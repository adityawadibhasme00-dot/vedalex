import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        resp = await page.goto('http://localhost:3000/innovation-lab', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open(r'C:\Users\adity\AppData\Local\Temp\opencode\page_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'HTML saved. Length: {len(html)}')
        await browser.close()

asyncio.run(check())
