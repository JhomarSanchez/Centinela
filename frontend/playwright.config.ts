import { defineConfig, devices } from "@playwright/test";

const python =
  process.env.PYTHON ??
  (process.platform === "win32" ? ".venv\\Scripts\\python.exe" : "python");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8080",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} -m uvicorn tests.e2e_app:app --host 127.0.0.1 --port 8000`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        APP_ENV: "test",
        API_KEY: "e2e-key",
        APP_SECRET_KEY: "e2e-secret-key",
        DATABASE_URL: "sqlite:///./centinela-e2e.db",
        SCHEDULER_ENABLED: "false",
        OLLAMA_ENABLED: "false",
      },
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      url: "http://127.0.0.1:8080",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
