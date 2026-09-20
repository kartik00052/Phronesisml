import { expect, test } from "@playwright/test";

test.describe("PhronesisML demo mode", () => {
  test("dashboard loads with demo data", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText(/demo/i).first()).toBeVisible();
  });

  test("primary navigation reaches every workspace page", async ({ page }) => {
    const routes: [string, RegExp][] = [
      ["/runs", /runs/i],
      ["/datasets", /datasets/i],
      ["/models", /models/i],
      ["/explainability", /explainability/i],
      ["/reports", /reports/i],
      ["/artifacts", /artifacts/i],
      ["/settings", /settings/i],
    ];

    await page.goto("/");
    for (const [path, heading] of routes) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
    }
  });

  test("new run wizard creates a run and lands on the workspace", async ({ page }) => {
    await page.goto("/runs/new");
    await expect(page.getByRole("heading", { name: "New Run" })).toBeVisible();

    // Step 1 — Dataset: pick the first registered dataset.
    const datasetCard = page.getByRole("button").filter({ hasText: /Valid|Warnings/ }).first();
    await expect(datasetCard).toBeVisible();
    await datasetCard.click();
    await page.getByRole("button", { name: /continue/i }).click();

    // Step 2 — Target & Task: accept the auto-detected target.
    await expect(page.getByText(/target/i).first()).toBeVisible();
    await page.getByRole("button", { name: /continue/i }).click();

    // Step 3 — Engine: accept the recommended engine.
    await expect(page.getByText(/engine/i).first()).toBeVisible();
    await page.getByRole("button", { name: /continue/i }).click();

    // Step 4 — Pipeline: accept the default configuration.
    await expect(page.getByText(/pipeline depth/i).first()).toBeVisible();
    await page.getByRole("button", { name: /continue/i }).click();

    // Step 5 — Review & launch.
    await expect(page.getByRole("button", { name: /launch run/i })).toBeVisible();
    await page.getByRole("button", { name: /launch run/i }).click();

    await expect(page).toHaveURL(/\/runs\/[^/]+$/);
    await expect(page.getByText(/run/i).first()).toBeVisible();
  });

  test("run workspace exposes every section tab", async ({ page }) => {
    await page.goto("/runs");
    const firstRun = page.locator('tbody a[href^="/runs/"]').first();
    await expect(firstRun).toBeVisible();
    await firstRun.click();
    await expect(page).toHaveURL(/\/runs\/[^/]+/);

    const nav = page.getByRole("navigation", { name: "Run workspace sections" });
    for (const label of ["Overview", "Pipeline", "Data", "Models", "Explainability", "Reports", "Artifacts", "Logs"]) {
      await expect(nav.getByRole("link", { name: label })).toBeVisible();
    }
    await nav.getByRole("link", { name: "Logs" }).click();
    await expect(page).toHaveURL(/\/logs$/);
    await expect(page.getByText(/lines/i).first()).toBeVisible();
  });

  test("run comparison page renders with the differences-only toggle", async ({ page }) => {
    await page.goto("/runs/compare");
    await expect(page.getByRole("heading", { name: "Compare runs" })).toBeVisible();
    await expect(page.getByLabel("Differences only")).toBeVisible();
    await expect(page.getByText(/Select runs/i)).toBeVisible();
  });
});
