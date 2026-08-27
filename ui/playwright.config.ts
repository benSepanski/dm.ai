import { defineConfig } from '@playwright/test';

// Each test spawns its own real server binary over a fresh data directory
// (see e2e/server.ts) — no webServer here, and no Node in the serving path.
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  workers: 1,
  use: {
    browserName: 'chromium',
  },
});
