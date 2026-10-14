import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: '/tmp/p142-gps-playwright-results',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:13000', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: [
    { command: 'python3 ../scripts/gps-e2e-server.py backend', url: 'http://127.0.0.1:18000/health', reuseExistingServer: false, timeout: 60_000 },
    { command: 'python3 ../scripts/gps-e2e-server.py frontend', url: 'http://127.0.0.1:13000/chat', reuseExistingServer: false, timeout: 240_000 },
  ],
});
