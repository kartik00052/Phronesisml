import { describe, expect, it } from "vitest";

import {
  TASK_METRIC_DESCRIPTORS,
  metricDescriptorsFor,
  metricValue,
  primaryMetricFor,
} from "@/config/metrics";

describe("metrics config", () => {
  it("selects a task-aware primary metric", () => {
    expect(primaryMetricFor("classification")).toBe("accuracy");
    expect(primaryMetricFor("regression")).toBe("r2");
    expect(primaryMetricFor("clustering")).toBe("silhouette_score");
    expect(primaryMetricFor("anomaly_detection")).toBe("n_anomalies");
  });

  it("falls back for unknown / nullish tasks", () => {
    expect(primaryMetricFor(null)).toBe("accuracy");
    expect(primaryMetricFor(undefined)).toBe("accuracy");
    expect(primaryMetricFor("mystery")).toBe("accuracy");
  });

  it("returns descriptors for known tasks and a fallback otherwise", () => {
    const classification = metricDescriptorsFor("classification");
    expect(classification.length).toBeGreaterThan(0);
    expect(classification[0].key).toBe("accuracy");
    expect(metricDescriptorsFor("mystery")).toEqual(TASK_METRIC_DESCRIPTORS.classification);
  });

  it("reads metric values defensively", () => {
    expect(metricValue({ accuracy: 0.9 }, "accuracy")).toBe(0.9);
    expect(metricValue({ accuracy: Number.NaN }, "accuracy")).toBeUndefined();
    expect(metricValue({ accuracy: "0.9" }, "accuracy")).toBeUndefined();
    expect(metricValue(null, "accuracy")).toBeUndefined();
  });
});
