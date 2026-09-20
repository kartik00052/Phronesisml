import { describe, expect, it } from "vitest";

import {
  formatBytes,
  formatDurationMs,
  formatNumber,
  formatPercent,
  formatScore,
} from "@/lib/format";

describe("formatNumbers", () => {
  it("formats byte sizes with binary units", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1024 * 1024)).toBe("1 MB");
  });

  it("formats counts with grouping separators", () => {
    expect(formatNumber(1000)).toBe("1,000");
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("respects digit precision for scores", () => {
    expect(formatScore(0.123456, 3)).toBe("0.123");
    expect(formatScore(0.98765, 2)).toBe("0.99");
    expect(formatScore(null)).toBe("—");
    expect(formatScore(undefined)).toBe("—");
  });

  it("formats percents", () => {
    expect(formatPercent(0.5)).toBe("50.0%");
    expect(formatPercent(0.1234, 2)).toBe("12.34%");
    expect(formatPercent(null)).toBe("—");
  });

  it("formats millisecond durations and falls back to em dash", () => {
    expect(formatDurationMs(1500)).toBe("2s");
    expect(formatDurationMs(90_000)).toBe("1m 30s");
    expect(formatDurationMs(null)).toBe("—");
  });
});
