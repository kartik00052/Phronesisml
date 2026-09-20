/** Deterministic color mapping for categorical series (charts + chips). */
import { ENGINE_LABELS } from "@/config/status";

export const ENGINE_COLORS: Record<string, string> = {
  pandas: "var(--info)",
  polars: "var(--primary)",
  spark: "var(--warning)",
};

export const TASK_COLORS: Record<string, string> = {
  classification: "var(--info)",
  regression: "var(--success)",
  clustering: "var(--warning)",
  anomaly_detection: "var(--danger)",
  ambiguous: "var(--muted-foreground)",
  analytics: "var(--accent)",
  unknown: "var(--muted-foreground)",
};

export const STAGE_PHASE_COLORS: Record<string, string> = {
  data: "var(--info)",
  insight: "var(--primary)",
  model: "var(--success)",
  delivery: "var(--warning)",
};

export function engineLabel(engine: string): string {
  return ENGINE_LABELS[engine] ?? engine;
}