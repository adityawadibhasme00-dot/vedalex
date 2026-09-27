import { expect, test } from '@playwright/test';

const backendURL = 'http://127.0.0.1:18000';

test('backend health endpoint is available', async ({ request }) => {
  const response = await request.get(`${backendURL}/api/v1/health`);
  expect(response.status()).toBe(200);
  const payload = await response.json();
  expect(payload).toEqual(expect.objectContaining({ status: 'healthy' }));
});

test('landing and login application shells render', async ({ page }) => {
  const landing = await page.goto('/');
  expect(landing?.status()).toBe(200);
  await expect(page).toHaveTitle(/IP-SAKTI/);
  await expect(page.locator('body')).toBeVisible();

  const login = await page.goto('/login');
  expect(login?.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'IP-SAKTI' })).toBeVisible();
});
