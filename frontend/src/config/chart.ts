import * as React from "react";

import type { ResolvedTheme } from "@/stores/theme";

/**
 * Chart design tokens.
 *
 * Canvas/SVG charts cannot consume CSS `var()` reliably across renderers, so
 * the palette is declared explicitly for both themes while still tracing the
 * semantic status colors used across the app.
 */

export const CHART_PALETTE: Record<ResolvedTheme, string[]> = {
  light: ["#3b5bdb", "#0ea5a4", "#f59e0b", "#e11d48", "#7c3aed", "#0ea5e9", "#65a30d", "#db2777"],
  dark: ["#7c9cff", "#2dd4bf", "#fbbf24", "#fb7185", "#a78bfa", "#38bdf8", "#a3e635", "#f472b6"],
};

export const CHART_STATUS_COLORS = {
  success: { light: "#0f9d58", dark: "#4ade80" },
  warning: { light: "#d97706", dark: "#fbbf24" },
  danger: { light: "#dc2626", dark: "#f87171" },
  info: { light: "#3b5bdb", dark: "#7c9cff" },
  muted: { light: "#94a3b8", dark: "#64748b" },
} as const;

export interface ChartBase {
  theme: ResolvedTheme;
  palette: string[];
  text: string;
  subtleText: string;
  grid: string;
  axis: string;
  tooltipBg: string;
  tooltipBorder: string;
}

const LIGHT_BASE: Omit<ChartBase, "theme" | "palette"> = {
  text: "#1f2937",
  subtleText: "#64748b",
  grid: "#e6e8ee",
  axis: "#cbd2dd",
  tooltipBg: "#ffffff",
  tooltipBorder: "#d7dce6",
};

const DARK_BASE: Omit<ChartBase, "theme" | "palette"> = {
  text: "#e2e8f0",
  subtleText: "#94a3b8",
  grid: "#2a3242",
  axis: "#3a4356",
  tooltipBg: "#1f2530",
  tooltipBorder: "#333c4d",
};

export function chartBase(theme: ResolvedTheme): ChartBase {
  return {
    theme,
    palette: CHART_PALETTE[theme],
    ...(theme === "dark" ? DARK_BASE : LIGHT_BASE),
  };
}

/** Re-renders charts whenever the resolved theme mutates. */
export function useChartTheme(): ChartBase {
  const [theme, setTheme] = React.useState<ResolvedTheme>(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("dark")
      ? "dark"
      : "light",
  );

  React.useEffect(() => {
    const el = document.documentElement;
    const sync = () => setTheme(el.classList.contains("dark") ? "dark" : "light");
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return React.useMemo(() => chartBase(theme), [theme]);
}

/** Shared axis/grid/tooltip styling for all analytical charts. */
export function baseOption(base: ChartBase) {
  return {
    backgroundColor: "transparent",
    textStyle: { fontFamily: "Inter Variable, Inter, system-ui, sans-serif", color: base.text },
    grid: { left: 8, right: 12, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "item" as const,
      backgroundColor: base.tooltipBg,
      borderColor: base.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: base.text, fontSize: 12 },
      extraCssText: "border-radius:6px;box-shadow:0 8px 24px -6px rgba(0,0,0,0.25);",
    },
  };
}

export function axisStyle(base: ChartBase) {
  return {
    axisLine: { lineStyle: { color: base.axis } },
    axisTick: { show: false },
    axisLabel: { color: base.subtleText, fontSize: 11 },
    splitLine: { lineStyle: { color: base.grid } },
  };
}
