/**
 * Run / experiment types.
 *
 * Field names intentionally mirror the backend contract
 * (`results.py`, `WorkflowState`, artifact JSON files) so a real adapter
 * can be dropped in without reshaping the UI.
 */

import type { PipelineStageId } from "./pipeline";

export type RunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type TaskType =
  | "classification"
  | "regression"
  | "clustering"
  | "anomaly_detection"
  | "ambiguous"
  | "analytics"
  | "unknown";

export type EngineName = "pandas" | "polars" | "spark";

export type NullStrategy = "drop" | "fill" | "flag";

export type RunMode = "fast" | "balanced" | "full";

/** User-supplied run configuration (new-run wizard payload). */
export interface RunRequest {
  dataPath?: string;
  fileName?: string;
  datasetId?: string;
  engine?: EngineName | "auto";
  nullStrategy: NullStrategy;
  stages: PipelineStageId[];
  mode: RunMode;
  targetOverride?: string | null;
  taskOverride?: TaskType | null;
  cv?: number | null;
  modelType?: string | null;
  maxTrials?: number | null;
  maxTimeSeconds?: number | null;
  varianceThreshold?: number;
  correlationThreshold?: number;
  minFeatures?: number;
  samplingStrategy?: string;
}

/** Run list row (equivalent of `run_metadata.json`). */
export interface RunSummary {
  id: string;
  datasetName: string;
  datasetPath: string;
  fileFormat: string;
  rows: number;
  columns: number;
  fileSizeBytes: number;
  taskType: TaskType;
  targetColumn: string | null;
  engine: EngineName;
  engineReason: string;
  bestModelType: string | null;
  bestScore: number | null;
  primaryMetric: string;
  status: RunStatus;
  mode: RunMode;
  createdAt: string;
  updatedAt: string;
  durationMs: number | null;
  trialCount?: number;
  hpoTruncated?: boolean;
  stagesRequested?: PipelineStageId[];
  error?: string | null;
}

/** Sampling metadata (1:1 with backend `sampling_metadata`). */
export interface SamplingInfo {
  was_sampled: boolean;
  sampling_method?: string;
  sampling_ratio?: number;
  original_rows?: number;
  sample_rows?: number;
  random_state?: number | null;
  reason?: string;
}

/** Resource estimation report (1:1 with backend `resource_report`). */
export interface ResourceReport {
  n_rows: number;
  n_cols: number;
  total_cells: number;
  estimated_memory_mb: number;
  estimated_encoded_features: number;
  estimated_encoded_memory_mb: number;
  estimated_train_test_memory_mb: number;
  estimated_shap_memory_mb: number;
  estimated_runtime_seconds: number;
  requires_sampling: boolean;
  recommended_sample_size: number;
  recommended_sample_fraction: number;
  sampling_reason: string;
  auto_sample_size: number;
  available_memory_gb: number;
}

/** Full run detail assembled from the run's artifacts. */
export interface Run {
  id: string;
  status: RunStatus;
  request: RunRequest;
  summary: RunSummary;
  sampling: SamplingInfo | null;
  resourceReport: ResourceReport | null;
  warnings: string[];
  error: {
    type: string;
    message: string;
    context?: Record<string, string>;
  } | null;
  logs: string[];
  stagesRequested: PipelineStageId[];
  stagesExecuted: PipelineStageId[];
  totalDurationMs: number | null;
  createdAt: string;
  updatedAt: string;
}

/** Aggregated dashboard statistics. */
export interface DashboardStats {
  totalRuns: number;
  activeRuns: number;
  completedRuns: number;
  failedRuns: number;
  totalDatasets: number;
  totalModels: number;
  avgBestScore: number | null;
  totalArtifacts: number;
  engineBreakdown: Record<EngineName, number>;
  taskBreakdown: Record<TaskType, number>;
}

/** Recent activity item shown on the dashboard. */
export interface RecentRunActivity {
  id: string;
  datasetName: string;
  status: RunStatus;
  taskType: TaskType;
  bestModelType: string | null;
  bestScore: number | null;
  createdAt: string;
  durationMs: number | null;
}
