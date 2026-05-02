import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const configDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = configDir;
const repoRoot = path.resolve(configDir, "..", "..");
const baseUrl = process.env.AISS_WEB_BASE_URL || "http://127.0.0.1:4173";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: baseUrl,
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "PYTHONPATH=src python -m aiss serve --host 127.0.0.1 --port 8765",
      url: "http://127.0.0.1:8765/api/health",
      cwd: repoRoot,
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "python3 -m http.server 4173 --bind 127.0.0.1",
      url: "http://127.0.0.1:4173",
      cwd: webRoot,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
