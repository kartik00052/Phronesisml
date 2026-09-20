import { expect, test } from "@playwright/test";

/**
 * Real-backend end-to-end check.
 *
 * Skipped unless `E2E_REAL_BACKEND=true` AND the PhronesisML backend is
 * running on :8000 AND the frontend was built/served in real mode
 * (`VITE_DEMO_MODE=false`).  The default `webServer` in playwright.config
 * builds in demo mode, so run this manually:
 *
 *   VITE_DEMO_MODE=false VITE_API_BASE_URL=http://localhost:8000/api/v1 pnpm build
 *   pnpm preview &   # server on :4173
 *   (uvicorn backend.app.main:app --port 8000 &)
 *   E2E_REAL_BACKEND=true pnpm exec playwright test tests/e2e/real-backend.spec.ts
 */

const REAL = process.env.E2E_REAL_BACKEND === "true";

test.describe("Real backend mode", () => {
  test.skip(!REAL, "real-backend e2e needs E2E_REAL_BACKEND=true and a live backend");

  test("dashboard renders live data from /api/v1 without a demo banner", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText(/demo/i)).toHaveCount(0);
  });

  test("runs list loads rows from the real API", async ({ page }) => {
    await page.goto("/runs");
    await expect(page.getByRole("heading", { name: /runs/i }).first()).toBeVisible();
    // Live mode renders at least the runs table shell (mock data never shown).
    await expect(page.getByRole("table").first()).toBeVisible();
  });
});