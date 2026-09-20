/**
 * Pipeline stage types.
 *
 * Mirrors the backend's canonical 11-stage pipeline:
 * `phronesisml._stages._FULL_PIPELINE_STAGES`
 * (upload → etl → validation → eda → target_detection → feature_engineering →
 *  model_selection → evaluation → explainability → reporting → storage),
 * plus the observable execution statuses produced by the workflow layer.
 */

/** Canonical (ordered) pipeline stage ids — 1:1 with the backend. */
export type PipelineStageId =
  | "upload"
  | "etl"
  | "validation"
  | "eda"
  | "target_detection"
  | "feature_engineering"
  | "model_selection"
  | "evaluation"
  | "explainability"
  | "reporting"
  | "storage";

/** Observable status for a stage / run step. */
export type PipelineStageStatus =
  "idle" | "queued" | "running" | "completed" | "warning" | "failed" | "skipped" | "sampled";

/** A stage summary carries whatever the backend exposed at completion. */
export type StageSummary = Record<string, string | number | boolean | null>;

/** Event emitted when a stage transitions (Proposed backend contract). */
export interface StageEvent {
  run_id: string;
  stage: PipelineStageId | "node_sampling";
  status: PipelineStageStatus;
  summary?: StageSummary;
  ts: string;
}

/** Stage detail for the run workspace pipeline view. */
export interface StageDetail {
  id: PipelineStageId | "node_sampling";
  name: string;
  status: PipelineStageStatus;
  queuedAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  summary: StageSummary;
  logs: string[];
  error?: {
    type: string;
    message: string;
    context?: Record<string, string>;
  } | null;
}

/** Incremental execution progress for live runs. */
export interface PipelineProgress {
  runId: string;
  status: string;
  completedStages: PipelineStageId[];
  currentStage: PipelineStageId | null;
  currentStagesCompleted: number;
  totalStages: number;
  messages: string[];
}

/** Aggregated overview of a run's pipeline execution. */
export interface PipelineOverview {
  runId: string;
  mode: string;
  stagesRequested: PipelineStageId[];
  stagesExecuted: PipelineStageId[];
  sampling?: {
    was_sampled: boolean;
    sampling_method?: string;
    sampling_ratio?: number;
    original_rows?: number;
    sample_rows?: number;
    reason?: string;
  };
  totalDurationMs: number;
}
