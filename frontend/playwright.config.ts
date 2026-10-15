import { defineConfig, devices } from '@playwright/test';

const backendPort = process.env.GPS_E2E_BACKEND_PORT || '18000';
const frontendPort = process.env.GPS_E2E_FRONTEND_PORT || '13000';

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: process.env.GPS_E2E_OUTPUT_DIR || '/tmp/p142-gps-playwright-results',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: 'list',
  use: { baseURL: `http://127.0.0.1:${frontendPort}`, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: [
    { command: 'python3 ../scripts/gps-e2e-server.py backend', url: `http://127.0.0.1:${backendPort}/health`, reuseExistingServer: false, timeout: 60_000 },
    { command: 'python3 ../scripts/gps-e2e-server.py frontend', url: `http://127.0.0.1:${frontendPort}/chat`, reuseExistingServer: false, timeout: 240_000 },
  ],
});
