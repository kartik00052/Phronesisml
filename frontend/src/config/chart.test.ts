import { describe, expect, it } from "vitest";

import { axisStyle, baseOption, chartBase, CHART_PALETTE, CHART_STATUS_COLORS } from "@/config/chart";

describe("chart tokens", () => {
  it("provides a distinct palette per theme", () => {
    expect(CHART_PALETTE.light.length).toBeGreaterThanOrEqual(6);
    expect(CHART_PALETTE.dark.length).toBe(CHART_PALETTE.light.length);
    expect(CHART_PALETTE.light).not.toEqual(CHART_PALETTE.dark);
  });

  it("builds a base with the requested theme and its palette", () => {
    const base = chartBase("dark");
    expect(base.theme).toBe("dark");
    expect(base.palette).toBe(CHART_PALETTE.dark);
    expect(base.text).toBeTruthy();
  });

  it("exposes status colors for both themes", () => {
    for (const entry of Object.values(CHART_STATUS_COLORS)) {
      expect(entry.light).toMatch(/^#/);
      expect(entry.dark).toMatch(/^#/);
    }
  });

  it("produces shared tooltip and axis options", () => {
    const option = baseOption(chartBase("light"));
    expect(option.backgroundColor).toBe("transparent");
    expect(option.tooltip).toMatchObject({ borderWidth: 1 });
    const axis = axisStyle(chartBase("light"));
    expect(axis.axisTick).toEqual({ show: false });
    expect(axis.splitLine.lineStyle.color).toBeTruthy();
  });
});
