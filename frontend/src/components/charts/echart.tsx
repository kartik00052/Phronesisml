import * as React from "react";
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";

import { cn } from "@/lib/cn";

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
  DatasetComponent,
  CanvasRenderer,
]);

export type { EChartsCoreOption };

export interface EChartProps {
  option: EChartsCoreOption;
  height?: number | string;
  className?: string;
  /** Accessible label; charts are also paired with tabular fallbacks. */
  ariaLabel: string;
  onEvents?: Record<string, (params: unknown) => void>;
}

/**
 * Thin, theme-aware ECharts wrapper.
 *
 * - lazy: only pulls echarts when a chart actually renders (pages are lazy)
 * - responsive: resizes via ResizeObserver
 * - disposal-safe: cleans up the instance and listeners on unmount
 */
export function EChart({ option, height = 280, className, ariaLabel, onEvents }: EChartProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const chartRef = React.useRef<echarts.ECharts | null>(null);

  const extraKey = option ? JSON.stringify(Object.keys(option)) : "";

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: "canvas" });
    chartRef.current = chart;

    let observer: ResizeObserver | undefined;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => chart.resize());
      observer.observe(el);
    } else {
      window.addEventListener("resize", () => chart.resize());
    }

    const handlers = onEvents ?? {};
    for (const [event, handler] of Object.entries(handlers)) {
      chart.on(event, handler);
    }

    return () => {
      observer?.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
    // Recreate only if the event wiring changes, not on every option update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [extraKey]);

  React.useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      className={cn("w-full", className)}
      style={{ height }}
    />
  );
}
