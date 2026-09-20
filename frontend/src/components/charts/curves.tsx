import * as React from "react";

import { EChart, type EChartsCoreOption } from "@/components/charts/echart";
import { axisStyle, baseOption, useChartTheme } from "@/config/chart";
import type { CurvePoint } from "@/types/model";

export function RocCurve({
  curve,
  auc,
  height = 300,
}: {
  curve: CurvePoint[];
  auc?: number | null;
  height?: number;
}) {
  const base = useChartTheme();

  const option = React.useMemo<EChartsCoreOption>(() => ({
    ...baseOption(base),
    tooltip: { ...baseOption(base).tooltip, trigger: "axis" },
    legend: { show: false },
    xAxis: {
      type: "value",
      name: "False positive rate",
      min: 0,
      max: 1,
      nameTextStyle: { color: base.subtleText, fontSize: 11 },
      ...axisStyle(base),
    },
    yAxis: {
      type: "value",
      name: "True positive rate",
      min: 0,
      max: 1,
      nameTextStyle: { color: base.subtleText, fontSize: 11 },
      ...axisStyle(base),
    },
    series: [
      {
        type: "line",
        data: curve.map((p) => [p.x, p.y]),
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 2.5, color: base.palette[0] },
        areaStyle: { opacity: 0.08, color: base.palette[0] },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", color: base.subtleText, width: 1 },
          data: [{ xAxis: 0, yAxis: 0 }, { xAxis: 1, yAxis: 1 }],
          label: { show: false },
        },
      },
    ],
  }), [base, curve]);

  return (
    <EChart
      option={option}
      height={height}
      ariaLabel={`ROC curve${auc != null ? `, AUC ${auc.toFixed(3)}` : ""}`}
    />
  );
}

export function PrecisionRecallCurve({
  curve,
  averagePrecision,
  baseline,
  height = 300,
}: {
  curve: CurvePoint[];
  averagePrecision?: number | null;
  baseline?: number;
  height?: number;
}) {
  const base = useChartTheme();

  const option = React.useMemo<EChartsCoreOption>(() => ({
    ...baseOption(base),
    tooltip: { ...baseOption(base).tooltip, trigger: "axis" },
    xAxis: {
      type: "value",
      name: "Recall",
      min: 0,
      max: 1,
      nameTextStyle: { color: base.subtleText, fontSize: 11 },
      ...axisStyle(base),
    },
    yAxis: {
      type: "value",
      name: "Precision",
      min: 0,
      max: 1,
      nameTextStyle: { color: base.subtleText, fontSize: 11 },
      ...axisStyle(base),
    },
    series: [
      {
        type: "line",
        data: curve.map((p) => [p.x, p.y]),
        showSymbol: false,
        lineStyle: { width: 2.5, color: base.palette[1] },
        areaStyle: { opacity: 0.08, color: base.palette[1] },
        markLine:
          baseline != null
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: base.subtleText, width: 1 },
                data: [{ yAxis: baseline }],
                label: {
                  formatter: `baseline ${baseline.toFixed(2)}`,
                  color: base.subtleText,
                  fontSize: 10,
                },
              }
            : undefined,
      },
    ],
  }), [base, curve, baseline]);

  return (
    <EChart
      option={option}
      height={height}
      ariaLabel={`Precision-recall curve${
        averagePrecision != null ? `, average precision ${averagePrecision.toFixed(3)}` : ""
      }`}
    />
  );
}
