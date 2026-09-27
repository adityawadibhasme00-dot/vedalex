import { existsSync } from 'fs';
import path from 'path';
import { defineConfig, devices } from '@playwright/test';

const frontendURL = 'http://127.0.0.1:13000';
const backendURL = 'http://127.0.0.1:18000';
const localPython = [
  path.resolve(__dirname, '../backend/venv/Scripts/python.exe'),
  path.resolve(__dirname, '../backend/venv/bin/python')
].find(existsSync);
const python = process.env.PYTHON ?? localPython ?? 'python';
const pythonCommand = python.includes(' ') ? `"${python}"` : python;

const edgeProject = process.platform === 'win32'
  ? [
      {
        name: 'edge-desktop',
        use: {
          ...devices['Desktop Chrome'],
          channel: 'msedge',
          viewport: { width: 1920, height: 1080 }
        }
      }
    ]
  : [];

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }]
  ],
  use: {
    baseURL: frontendURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'chrome-desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1920, height: 1080 } }
    },
    {
      name: 'firefox-desktop',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1920, height: 1080 } }
    },
    {
      name: 'safari-webkit',
      use: { ...devices['Desktop Safari'], viewport: { width: 1920, height: 1080 } }
    },
    ...edgeProject,
    {
      name: 'tablet-768x1024',
      use: { ...devices['iPad (gen 7)'], viewport: { width: 768, height: 1024 } }
    },
    {
      name: 'mobile-375x667',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 375, height: 667 },
        isMobile: true,
        hasTouch: true
      }
    }
  ],
  webServer: [
    {
      command: `${pythonCommand} scripts/run_e2e_server.py`,
      cwd: path.resolve(__dirname, '../backend'),
      url: `${backendURL}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 180000
    },
    {
      command: 'npx next dev -p 13000',
      cwd: __dirname,
      url: frontendURL,
      env: {
        BACKEND_URL: backendURL,
        NEXT_PUBLIC_API_BASE_URL: '/api/v1',
        NEXT_TELEMETRY_DISABLED: '1'
      },
      reuseExistingServer: false,
      timeout: 180000
    }
  ]
});
