import * as React from "react";

import { EChart, type EChartsCoreOption } from "@/components/charts/echart";
import { useChartTheme } from "@/config/chart";

export function ConfusionMatrix({
  matrix,
  labels,
  height = 300,
}: {
  matrix: number[][];
  labels?: string[];
  height?: number;
}) {
  const base = useChartTheme();
  const n = matrix.length;
  const classLabels = labels ?? Array.from({ length: n }, (_, i) => `C${i}`);
  const max = Math.max(1, ...matrix.flat());

  const option = React.useMemo<EChartsCoreOption>(() => {
    const data: [number, number, number][] = [];
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        data.push([x, y, matrix[y]?.[x] ?? 0]);
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
          `Actual ${classLabels[p.value[1]]} → Predicted ${classLabels[p.value[0]]}<br/><b>${p.value[2]}</b>`,
      },
      grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
      xAxis: {
        type: "category",
        data: classLabels,
        name: "Predicted",
        nameLocation: "middle",
        nameGap: 26,
        nameTextStyle: { color: base.subtleText, fontSize: 11 },
        axisLine: { lineStyle: { color: base.axis } },
        axisTick: { show: false },
        axisLabel: { color: base.subtleText, fontSize: 10, interval: 0, rotate: classLabels.length > 6 ? 45 : 0 },
      },
      yAxis: {
        type: "category",
        data: classLabels,
        name: "Actual",
        nameLocation: "middle",
        nameGap: 40,
        nameTextStyle: { color: base.subtleText, fontSize: 11 },
        axisLine: { lineStyle: { color: base.axis } },
        axisTick: { show: false },
        axisLabel: { color: base.subtleText, fontSize: 10, interval: 0 },
      },
      visualMap: {
        min: 0,
        max,
        calculable: false,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        show: false,
        inRange: { color: base.theme === "dark" ? ["#1f2937", "#2563eb", "#93c5fd"] : ["#eef2ff", "#3b5bdb", "#1e3a8a"] },
      },
      series: [
        {
          type: "heatmap",
          data,
          label: {
            show: n <= 8,
            color: base.text,
            fontSize: 11,
            formatter: (p: { value: [number, number, number] }) => String(p.value[2]),
          },
          emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,0.3)" } },
          itemStyle: { borderColor: base.tooltipBg, borderWidth: 1 },
        },
      ],
    };
  }, [base, matrix, classLabels, n, max]);

  return <EChart option={option} height={height} ariaLabel="Confusion matrix heatmap" />;
}
