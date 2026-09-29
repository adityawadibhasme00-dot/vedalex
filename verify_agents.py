import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        resp = await page.request.get('http://localhost:8000/api/v1/innolab/agents')
        data = await resp.json()
        print('Total agents:', data['count'])
        print('Phases:', data['phases'])
        for a in data['agents']:
            print('  ', a['slug'], '->', a['label'])
        await browser.close()

asyncio.run(check())
