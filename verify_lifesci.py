import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        await page.goto('http://localhost:3000/innovation-lab', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        text = await page.inner_text('body')
        print('Life Sciences visible:', 'Life Sciences' in text)
        print('Engineering visible:', 'Engineering' in text)
        print('Intellectual Property visible:', 'Intellectual Property' in text)
        print('Materials visible:', 'Materials' in text)
        await browser.close()

asyncio.run(check())
