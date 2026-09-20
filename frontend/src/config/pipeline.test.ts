import { describe, expect, it } from "vitest";

import {
  DEFAULT_RUN_STAGES,
  PIPELINE_STAGE_ORDER,
  STAGE_META,
  STAGE_SLICES,
} from "@/config/pipeline";

describe("pipeline config", () => {
  it("defines the canonical 11-stage order", () => {
    expect(PIPELINE_STAGE_ORDER).toHaveLength(11);
    expect(PIPELINE_STAGE_ORDER).toEqual([
      "upload",
      "etl",
      "validation",
      "eda",
      "target_detection",
      "feature_engineering",
      "model_selection",
      "evaluation",
      "explainability",
      "reporting",
      "storage",
    ]);
  });

  it("has metadata for every stage with a label and phase", () => {
    for (const stage of PIPELINE_STAGE_ORDER) {
      expect(STAGE_META[stage]).toBeDefined();
      expect(STAGE_META[stage].label.length).toBeGreaterThan(0);
      expect(STAGE_META[stage].phase).toBeTruthy();
    }
  });

  it("grows pipeline slices monotonically", () => {
    expect(STAGE_SLICES.length).toBeGreaterThan(0);
    for (let i = 1; i < STAGE_SLICES.length; i++) {
      expect(STAGE_SLICES[i].stages.length).toBeGreaterThanOrEqual(
        STAGE_SLICES[i - 1].stages.length,
      );
    }
    expect(STAGE_SLICES.at(-1)?.stages).toEqual(PIPELINE_STAGE_ORDER);
  });

  it("exposes the full pipeline as the default run stages", () => {
    expect(DEFAULT_RUN_STAGES).toEqual(PIPELINE_STAGE_ORDER);
  });
});
