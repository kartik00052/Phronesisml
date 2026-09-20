import * as React from "react";

import { EChart, type EChartsCoreOption } from "@/components/charts/echart";
import { useChartTheme } from "@/config/chart";

export interface CorrelationMatrix {
  labels: string[];
  /** values[i][j] = correlation between labels[i] and labels[j] (range -1..1). */
  values: number[][];
}

export function CorrelationHeatmap({
  matrix,
  height = 360,
}: {
  matrix: CorrelationMatrix;
  height?: number;
}) {
  const base = useChartTheme();
  const { labels, values } = matrix;

  const option = React.useMemo<EChartsCoreOption>(() => {
    const data: [number, number, number][] = [];
    for (let y = 0; y < labels.length; y++) {
      for (let x = 0; x < labels.length; x++) {
        data.push([x, y, Number((values[y]?.[x] ?? 0).toFixed(3))]);
      }
    }
    return {
      backgroundColor: "transparent",
      tooltip: {
        position: "top",
        backgroundColor: base.tooltipBg,
        borderColor: base.tooltipBorder,
        textStyle: { color: base.text, fontSize: 12 },
        formatter: (p: { value: [number, number, number] }) =>
          `${labels[p.value[1]]} × ${labels[p.value[0]]}<br/><b>r = ${p.value[2].toFixed(3)}</b>`,
      },
      grid: { left: 8, right: 8, top: 8, bottom: 48, containLabel: true },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: base.axis } },
        axisTick: { show: false },
        axisLabel: { color: base.subtleText, fontSize: 10, interval: 0, rotate: 40 },
      },
      yAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: base.axis } },
        axisTick: { show: false },
        axisLabel: { color: base.subtleText, fontSize: 10, interval: 0 },
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        textStyle: { color: base.subtleText, fontSize: 10 },
        inRange: {
          color:
            base.theme === "dark"
              ? ["#7c9cff", "#1f2937", "#f87171"]
              : ["#3b5bdb", "#f1f5f9", "#dc2626"],
        },
      },
      series: [
        {
          type: "heatmap",
          data,
          label: { show: labels.length <= 8, fontSize: 9, color: base.text },
          itemStyle: { borderColor: base.tooltipBg, borderWidth: 1 },
        },
      ],
    };
  }, [base, labels, values]);

  return <EChart option={option} height={height} ariaLabel="Correlation heatmap" />;
}
