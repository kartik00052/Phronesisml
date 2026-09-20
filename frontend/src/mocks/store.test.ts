import { describe, expect, it } from "vitest";

import {
  cancelDemoRun,
  restoreDemoRun,
  deleteDemoRun,
  createDemoRun,
  type SyntheticRunInput,
} from "@/mocks/store";
import { demoUploadDataset, demoDeleteDataset, demoListDatasets } from "@/mocks/handlers";
import { registerDemoDataset, removeDemoDataset, DEMO_DATASETS } from "@/mocks/seed/datasets";
import { PIPELINE_STAGE_ORDER } from "@/config/pipeline";
import type { DatasetSummary } from "@/types/dataset";

const COMPLETED = "run_8f17d3c9f6ae4b2e8a1d5c3b7f0e9a21";

function freshRequest(): SyntheticRunInput {
  return {
    datasetId: "ds_iris",
    engine: "auto",
    nullStrategy: "flag",
    stages: PIPELINE_STAGE_ORDER,
    mode: "fast",
  };
}

describe("demo run lifecycle", () => {
  it("refuses to restore a non-terminal run with a not-active error", () => {
    const created = createDemoRun(freshRequest()).id;
    expect(restoreDemoRun(created)).toMatchObject({ ok: false, reason: "not-active" });
  });

  it("refuses to cancel a run that already finished", () => {
    expect(cancelDemoRun(COMPLETED)).toMatchObject({ ok: false, reason: "not-active" });
  });

  it("cancels an active run and skips unfinished stages", () => {
    const created = createDemoRun(freshRequest()).id;
    const result = cancelDemoRun(created);
    expect(result).toMatchObject({ ok: true });
    if (!result.ok) return;
    expect(result.record.run.status).toBe("cancelled");
    expect(result.record.stages.some((s) => s.status === "skipped")).toBe(true);
  });

  it("restores a completed run back to queued with reset stages", () => {
    const result = restoreDemoRun(COMPLETED);
    expect(result).toMatchObject({ ok: true });
    if (!result.ok) return;
    expect(result.record.run.status).toBe("queued");
    expect(result.record.stages.every((s) => s.status === "queued")).toBe(true);
  });

  it("deletes a run and then reports it as missing", () => {
    const created = createDemoRun(freshRequest()).id;
    expect(deleteDemoRun(created)).toMatchObject({ ok: true });
    expect(deleteDemoRun(created)).toMatchObject({ ok: false, reason: "not-found" });
  });
});

describe("demo dataset store", () => {
  function summary(id: string): DatasetSummary {
    return {
      id,
      name: `${id}.csv`,
      path: `uploads/${id}.csv`,
      format: "csv",
      sizeBytes: 1024,
      rows: 16,
      columns: 8,
      engine: "pandas",
      engineReason: "ok",
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 0,
      targetColumn: null,
      taskType: null,
      registeredAt: new Date().toISOString(),
      lastUsedRunId: null,
      sample: false,
    };
  }

  it("registers an uploaded dataset and surfaces it in the list", async () => {
    registerDemoDataset(summary("ds_fresh"));
    expect(DEMO_DATASETS["ds_fresh"]).toBeDefined();
    const page = await demoListDatasets({ page: 1, pageSize: 100 });
    expect(page.items.some((d) => d.id === "ds_fresh")).toBe(true);
  });

  it("removes a dataset and deletes it through the handler", async () => {
    registerDemoDataset(summary("ds_del"));
    await expect(demoDeleteDataset("ds_del")).resolves.toEqual({ deleted: true, id: "ds_del" });
    expect(DEMO_DATASETS["ds_del"]).toBeUndefined();
    await expect(demoDeleteDataset("ds_del")).rejects.toMatchObject({ kind: "NotFound" });
  });

  it("returns false when removing an unknown dataset", () => {
    expect(removeDemoDataset("ds_nope")).toBe(false);
  });
});

describe("demo upload", () => {
  it("uploads a file with progress and registers a simulated dataset", async () => {
    const progress: number[] = [];
    const result = await demoUploadDataset(
      new File(["a".repeat(256)], "prices.csv", { type: "text/csv" }),
      (pct) => progress.push(pct),
    );
    expect(progress.at(-1)).toBe(100);
    expect(result.dataset.summary.name).toBe("prices.csv");
    expect(result.dataset.summary.sample).toBe(false);
    expect(result.dataset.summary.engine).toBe("pandas");
    expect(DEMO_DATASETS[result.dataset.summary.id]).toBeDefined();
  });
});
