import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  forbidOnly: !!process.env.CI,
  outputDir: '../.test-runs/playwright-artifacts',
  reporter: [['list'], ['html', { outputFolder: '../.test-runs/playwright-report', open: 'never' }]],
  use: { baseURL: process.env.QA_BASE_URL || 'http://localhost:3001',
    trace: 'retain-on-failure', screenshot: 'only-on-failure', video: 'off' },
  projects: [375, 768, 1440].map(width => ({ name: `width-${width}`, use: {viewport: {width, height: 960}} })),
});
