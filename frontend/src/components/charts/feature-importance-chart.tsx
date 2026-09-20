import * as React from "react";

import { EChart, type EChartsCoreOption } from "@/components/charts/echart";
import { axisStyle, useChartTheme } from "@/config/chart";
import { formatScore } from "@/lib/format";

const CHART_NEGATIVE = { light: "#e11d48", dark: "#fb7185" } as const;

export function FeatureImportanceChart({
  items,
  height = 340,
  maxFeatures = 20,
}: {
  items: { feature: string; value: number }[];
  height?: number;
  maxFeatures?: number;
}) {
  const base = useChartTheme();

  const top = React.useMemo(
    () =>
      [...items]
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, maxFeatures)
        .reverse(),
    [items, maxFeatures],
  );

  const option = React.useMemo<EChartsCoreOption>(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: base.tooltipBg,
      borderColor: base.tooltipBorder,
      textStyle: { color: base.text, fontSize: 12 },
      formatter: (p: { name: string; value: number }) =>
        `${p.name}<br/><b>${formatScore(p.value, 4)}</b>`,
    },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: base.subtleText, fontSize: 11 },
      splitLine: { lineStyle: { color: base.grid } },
    },
    yAxis: {
      type: "category",
      data: top.map((t) => t.feature),
      axisLine: { lineStyle: { color: base.axis } },
      axisTick: { show: false },
      axisLabel: { color: base.subtleText, fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: top.map((t) => ({
          value: t.value,
          itemStyle: {
            color: t.value >= 0 ? base.palette[0] : CHART_NEGATIVE[base.theme],
            borderRadius: 3,
          },
        })),
        barMaxWidth: 16,
        label: {
          show: true,
          position: "right",
          color: base.subtleText,
          fontSize: 10,
          formatter: (p: { value: number }) => formatScore(p.value, 3),
        },
      },
    ],
  }), [base, top]);

  return <EChart option={option} height={height} ariaLabel="Feature importance chart" />;
}

export function MetricBars({
  data,
  height = 300,
  maxBars = 12,
}: {
  data: { label: string; value: number }[];
  height?: number;
  maxBars?: number;
}) {
  const base = useChartTheme();
  const top = React.useMemo(() => data.slice(0, maxBars), [data, maxBars]);

  const option = React.useMemo<EChartsCoreOption>(() => ({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: base.tooltipBg,
      borderColor: base.tooltipBorder,
      textStyle: { color: base.text, fontSize: 12 },
    },
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: "category",
      data: top.map((d) => d.label),
      ...axisStyle(base),
      axisLabel: { color: base.subtleText, fontSize: 10, interval: 0, rotate: top.length > 6 ? 30 : 0 },
    },
    yAxis: { type: "value", ...axisStyle(base) },
    series: [
      {
        type: "bar",
        data: top.map((d) => d.value),
        itemStyle: { color: base.palette[0], borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 36,
      },
    ],
  }), [base, top]);

  return <EChart option={option} height={height} ariaLabel="Metric bar chart" />;
}
