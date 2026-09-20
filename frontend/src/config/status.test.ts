import { describe, expect, it } from "vitest";

import { ENGINE_LABELS, RUN_STATUS_META, STAGE_STATUS_META, TASK_LABELS } from "@/config/status";

const STAGE_STATUSES = [
  "idle",
  "queued",
  "running",
  "completed",
  "warning",
  "failed",
  "skipped",
  "sampled",
] as const;

describe("status config", () => {
  it("maps every stage status to a label, tone, and icon", () => {
    for (const status of STAGE_STATUSES) {
      const meta = STAGE_STATUS_META[status];
      expect(meta).toBeDefined();
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.icon).toBeTruthy();
      expect(meta.tone).toMatch(/muted|info|success|warning|danger/);
    }
  });

  it("maps run statuses and keeps failed as danger", () => {
    expect(Object.keys(RUN_STATUS_META).sort()).toEqual([
      "cancelled",
      "completed",
      "failed",
      "queued",
      "running",
    ]);
    expect(RUN_STATUS_META.failed.tone).toBe("danger");
    expect(RUN_STATUS_META.running.tone).toBe("info");
    expect(RUN_STATUS_META.completed.tone).toBe("success");
    expect(RUN_STATUS_META.cancelled.tone).toBe("warning");
  });

  it("humanizes task and engine labels", () => {
    expect(TASK_LABELS.anomaly_detection).toBe("Anomaly Detection");
    expect(TASK_LABELS.classification).toBe("Classification");
    expect(ENGINE_LABELS.spark).toBe("Spark");
  });
});
