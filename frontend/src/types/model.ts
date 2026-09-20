/**
 * Model / evaluation types.
 * 1:1 with backend AutoML + evaluation outputs:
 * `candidate_models`, `best_pipeline`, `evaluation_report`,
 * `ml/evaluation/metrics.py`.
 */

/** Candidate descriptor from `candidate_models` (auto_selector). */
export interface CandidateModelDescriptor {
  name: string;
  estimator_path: string;
  param_space: Record<string, unknown>;
  tags: Record<string, boolean>;
}

/** Best pipeline object (`best_pipeline`). Prefer `best_params`. */
export interface BestPipeline {
  model_type: string;
  params: Record<string, unknown>;
  best_params: Record<string, unknown>;
  score: number;
  trials_used: number;
  time_elapsed: number;
  truncated: boolean;
  estimated_training_cost: "low" | "medium" | "high" | "unknown";
}

/** One sample of a curve (ROC / PR). */
export interface CurvePoint {
  x: number;
  y: number;
}

/** Classification evaluation metrics. */
export interface ClassificationMetrics {
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  confusion_matrix: number[][];
  roc_curve?: CurvePoint[] | null;
  roc_auc?: number | null;
  precision_recall_curve?: CurvePoint[] | null;
  average_precision?: number | null;
}

/** Regression evaluation metrics. */
export interface RegressionMetrics {
  rmse: number;
  mae: number;
  r2: number;
}

/** Clustering evaluation metrics. */
export interface ClusteringMetrics {
  n_clusters: number;
  silhouette_score: number | null;
  davies_bouldin_score: number | null;
  calinski_harabasz_score: number | null;
}

/** Anomaly detection evaluation metrics. */
export interface AnomalyMetrics {
  n_anomalies: number;
  n_total: number;
  detected_contamination: number;
  expected_contamination: number;
}

export type TaskMetrics =
  | (ClassificationMetrics & { task: "classification" })
  | (RegressionMetrics & { task: "regression" })
  | (ClusteringMetrics & { task: "clustering" })
  | (AnomalyMetrics & { task: "anomaly_detection" })
  | ({ task: "ambiguous" } & Partial<ClassificationMetrics> & Partial<RegressionMetrics>);

/** `evaluation_report` from the evaluation agent. */
export interface EvaluationReport {
  task_type: string;
  metrics: TaskMetrics;
  model_info: {
    model_type: string;
    model_module: string;
    best_params: Record<string, unknown>;
    n_features: number;
    n_samples: number;
  };
  ambiguity_caveat: string | null;
  mlflow_logged: boolean;
}

/** Leaderboard row — a model trained for a run. */
export interface ModelRankingRow {
  rank: number;
  model_type: string;
  primary_score: number;
  secondary_metrics: Record<string, number | undefined>;
  trials_used: number;
  time_elapsed: number;
  truncated: boolean;
  estimated_training_cost: string;
  best: boolean;
  status: "ready" | "running" | "failed";
}

/** Model detail (leaderboard + evaluation + params). */
export interface ModelDetail {
  model_type: string;
  model_class: string;
  best_params: Record<string, unknown>;
  score: number;
  trials_used: number;
  time_elapsed: number;
  truncated: boolean;
  estimated_training_cost: string;
  taskType: string;
  targetColumn: string | null;
  nFeatures: number;
  nSamples: number;
  evaluation: EvaluationReport | null;
  rank: number;
  best: boolean;
}

/** Metrics metadata: labels + whether higher is better. */
export interface MetricDescriptor {
  key: string;
  label: string;
  higherIsBetter: boolean;
  precision?: number;
}