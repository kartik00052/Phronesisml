import * as React from "react";

import { EChart, type EChartsCoreOption } from "@/components/charts/echart";
import { axisStyle, useChartTheme } from "@/config/chart";
import { formatNumber } from "@/lib/format";

function bin(values: number[], binCount: number): { label: string; count: number }[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return [{ label: min.toFixed(2), count: values.length }];
  const width = (max - min) / binCount;
  const buckets = new Array(binCount).fill(0) as number[];
  for (const v of values) {
    const idx = Math.min(binCount - 1, Math.floor((v - min) / width));
    buckets[idx] += 1;
  }
  return buckets.map((count, i) => ({
    label: `${(min + i * width).toFixed(1)}`,
    count,
  }));
}

export function HistogramChart({
  values,
  binCount = 24,
  height = 240,
}: {
  values: number[];
  binCount?: number;
  height?: number;
}) {
  const base = useChartTheme();
  const data = React.useMemo(() => bin(values, binCount), [values, binCount]);

  const option = React.useMemo<EChartsCoreOption>(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: base.tooltipBg,
      borderColor: base.tooltipBorder,
      textStyle: { color: base.text, fontSize: 12 },
      formatter: (p: { name: string; value: number }[]) =>
        `≥ ${p[0].name}<br/><b>${formatNumber(p[0].value)}</b> rows`,
    },
    grid: { left: 8, right: 12, top: 12, bottom: 8, containLabel: true },
    xAxis: {
      type: "category",
      data: data.map((d) => d.label),
      ...axisStyle(base),
      axisLabel: { color: base.subtleText, fontSize: 10, hideOverlap: true },
    },
    yAxis: { type: "value", ...axisStyle(base) },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.count),
        itemStyle: { color: base.palette[0], borderRadius: [3, 3, 0, 0] },
        barCategoryGap: "10%",
      },
    ],
  }), [base, data]);

  return <EChart option={option} height={height} ariaLabel="Distribution histogram" />;
}

export function CategoryBarChart({
  values,
  height = 240,
  maxBars = 10,
}: {
  values: Record<string, number>;
  height?: number;
  maxBars?: number;
}) {
  const base = useChartTheme();
  const data = React.useMemo(
    () =>
      Object.entries(values)
        .sort((a, b) => b[1] - a[1])
        .slice(0, maxBars),
    [values, maxBars],
  );

  const option = React.useMemo<EChartsCoreOption>(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: base.tooltipBg,
      borderColor: base.tooltipBorder,
      textStyle: { color: base.text, fontSize: 12 },
    },
    grid: { left: 8, right: 12, top: 12, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      ...axisStyle(base),
    },
    yAxis: {
      type: "category",
      data: data.map(([k]) => k),
      ...axisStyle(base),
      axisLabel: { color: base.subtleText, fontSize: 11 },
      splitLine: { show: false },
    },
    series: [
      {
        type: "bar",
        data: data.map(([, v]) => v),
        itemStyle: { color: base.palette[1], borderRadius: 3 },
        barMaxWidth: 18,
      },
    ],
  }), [base, data]);

  return <EChart option={option} height={height} ariaLabel="Category distribution chart" />;
}
