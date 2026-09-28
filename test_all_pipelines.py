import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})

        apis = [
            ('POST', '/api/v1/auth/signup', '{"email":"test@test.com","password":"test123","name":"Test"}'),
            ('POST', '/api/v1/auth/login', '{"email":"test@test.com","password":"test123"}'),
            ('GET', '/api/v1/auth/profile', None),
            ('POST', '/api/v1/passport/create', '{"case_title":"Test","product_form":"Tablet","dosage_form":"Oral","intended_use":"Test"}'),
            ('POST', '/api/v1/formulation/parse', '{"text":"हरिद्रा 50%, तुलसी 30%, आश्वगंधा 20%"}'),
            ('POST', '/api/v1/botanical/canonicalize', '{"name":"हरिद्रा"}'),
            ('POST', '/api/v1/chat/query', '{"query":"What are the patent requirements?"}'),
            ('POST', '/api/v1/fto/check', '{"formulation":"Test"}'),
            ('POST', '/api/v1/label/analyze', '{"label_text":"Test label"}'),
            ('GET', '/api/v1/analysis/readiness/test', None),
            ('GET', '/api/v1/roadmap/test', None),
            ('POST', '/api/v1/export/dossier', '{"passport_id":"test"}'),
            ('POST', '/api/v1/assessment/evaluate', '{"passport_id":"test"}'),
            ('POST', '/api/v1/what-if/simulate', '{"passport_id":"test","mutation":"test"}'),
            ('GET', '/api/v1/evidence/test', None),
        ]

        for method, path, body in apis:
            try:
                if method == 'GET':
                    resp = await page.request.get(f'http://localhost:8000{path}')
                else:
                    resp = await page.request.post(f'http://localhost:8000{path}', data=body or '{}')
                print(f'{method} {path} -> {resp.status}')
            except Exception as e:
                print(f'{method} {path} -> ERROR: {str(e)[:80]}')

        await browser.close()

asyncio.run(check())
