import { describe, expect, it } from "vitest";

import {
  optionalNumber,
  wizardDefaults,
  wizardSchema,
  wizardToRequest,
  type WizardValues,
} from "@/components/new-run/form";
import { PIPELINE_STAGE_ORDER } from "@/config/pipeline";

function values(overrides: Partial<WizardValues> = {}): WizardValues {
  return { ...wizardDefaults, datasetId: "ds-1", ...overrides };
}

describe("wizardSchema", () => {
  it("requires a dataset", () => {
    const result = wizardSchema.safeParse(wizardDefaults);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toBe("Select a dataset to continue");
    }
  });

  it("accepts the default configuration once a dataset is chosen", () => {
    expect(wizardSchema.safeParse(values()).success).toBe(true);
  });

  it("bounds CV folds, trials, and thresholds", () => {
    expect(wizardSchema.safeParse(values({ cv: "1" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ cv: "21" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ cv: "10" })).success).toBe(true);
    expect(wizardSchema.safeParse(values({ maxTrials: "0" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ maxTrials: "501" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ maxTrials: "50" })).success).toBe(true);
    expect(wizardSchema.safeParse(values({ varianceThreshold: "1.5" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ correlationThreshold: "-0.1" })).success).toBe(false);
    expect(wizardSchema.safeParse(values({ minFeatures: "0" })).success).toBe(false);
  });
});

describe("optionalNumber", () => {
  it("returns null for blanks and parses numbers otherwise", () => {
    expect(optionalNumber("")).toBeNull();
    expect(optionalNumber("   ")).toBeNull();
    expect(optionalNumber("abc")).toBeNull();
    expect(optionalNumber("0.42")).toBe(0.42);
  });
});

describe("wizardToRequest", () => {
  it("resolves the engine when set to auto", () => {
    expect(wizardToRequest(values({ engine: "auto" }), "polars").engine).toBe("polars");
    expect(wizardToRequest(values({ engine: "spark" }), "polars").engine).toBe("spark");
  });

  it("maps the selected pipeline depth to stages", () => {
    const request = wizardToRequest(values({ pipelineDepth: "validate" }), "pandas");
    expect(request.stages).toEqual(PIPELINE_STAGE_ORDER.slice(0, 3));
  });

  it("falls back to the full pipeline for an unknown depth", () => {
    const request = wizardToRequest(values({ pipelineDepth: "does-not-exist" }), "pandas");
    expect(request.stages).toEqual(PIPELINE_STAGE_ORDER);
  });

  it("trims overrides and treats blanks as null / undefined", () => {
    const request = wizardToRequest(
      values({
        targetOverride: "  price ",
        taskOverride: "regression",
        modelType: "",
        samplingStrategy: "auto",
        cv: "",
        maxTrials: "",
      }),
      "pandas",
    );
    expect(request.targetOverride).toBe("price");
    expect(request.taskOverride).toBe("regression");
    expect(request.modelType).toBeNull();
    expect(request.samplingStrategy).toBeUndefined();
    expect(request.cv).toBeNull();
    expect(request.maxTrials).toBeNull();
  });

  it("forwards explicit thresholds and advanced numbers", () => {
    const request = wizardToRequest(
      values({
        varianceThreshold: "0.05",
        correlationThreshold: "0.9",
        minFeatures: "3",
        samplingStrategy: "random",
        maxTrials: "25",
      }),
      "pandas",
    );
    expect(request.varianceThreshold).toBe(0.05);
    expect(request.correlationThreshold).toBe(0.9);
    expect(request.minFeatures).toBe(3);
    expect(request.samplingStrategy).toBe("random");
    expect(request.maxTrials).toBe(25);
  });
});
