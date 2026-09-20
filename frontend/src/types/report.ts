/**
 * Report types.
 * The backend produces a Markdown report (`report.md`) and a self-contained
 * HTML report (`report.html`) plus a JSON pipeline report (`pipeline.json`).
 */

export type ReportFormat = "markdown" | "html" | "json" | "pdf";

export interface ReportInfo {
  runId: string;
  format: ReportFormat;
  title: string;
  created: string;
  reportLength: number;
  reportLines: number;
  downloadUrl?: string;
  /** Rendered markdown (for preview). */
  markdown?: string;
  /** Self-contained HTML rendering of the report (for sandboxed preview). */
  html?: string;
  /** Structured pipeline JSON report. */
  json?: string;
  sections: string[];
}

/** Pipeline JSON report sections (backend `build_json_report`). */
export interface PipelineJsonReport {
  run: Record<string, unknown>;
  dataset: Record<string, unknown>;
  target: Record<string, unknown>;
  model: Record<string, unknown>;
  metrics: Record<string, unknown>;
  explanation: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  narrative: string;
}