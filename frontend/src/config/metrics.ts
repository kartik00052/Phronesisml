import type { MetricDescriptor } from "@/types/model";
import type { TaskType } from "@/types/run";

/** Task-aware primary metric + secondary descriptors (backend `metrics.py`). */
export const TASK_METRIC_DESCRIPTORS: Record<string, MetricDescriptor[]> = {
  classification: [
    { key: "accuracy", label: "Accuracy", higherIsBetter: true, precision: 4 },
    { key: "f1_macro", label: "F1 (macro)", higherIsBetter: true, precision: 4 },
    { key: "roc_auc", label: "ROC AUC", higherIsBetter: true, precision: 4 },
    { key: "precision_macro", label: "Precision (macro)", higherIsBetter: true, precision: 4 },
    { key: "recall_macro", label: "Recall (macro)", higherIsBetter: true, precision: 4 },
  ],
  regression: [
    { key: "r2", label: "R²", higherIsBetter: true, precision: 4 },
    { key: "rmse", label: "RMSE", higherIsBetter: false, precision: 3 },
    { key: "mae", label: "MAE", higherIsBetter: false, precision: 3 },
  ],
  clustering: [
    { key: "silhouette_score", label: "Silhouette", higherIsBetter: true, precision: 4 },
    { key: "davies_bouldin_score", label: "Davies–Bouldin", higherIsBetter: false, precision: 4 },
    { key: "calinski_harabasz_score", label: "Calinski–Harabasz", higherIsBetter: true, precision: 2 },
  ],
  anomaly_detection: [
    { key: "n_anomalies", label: "Anomalies found", higherIsBetter: false, precision: 0 },
    { key: "detected_contamination", label: "Contamination", higherIsBetter: false, precision: 4 },
  ],
};

export const DEFAULT_PRIMARY_METRIC: Record<string, string> = {
  classification: "accuracy",
  regression: "r2",
  clustering: "silhouette_score",
  anomaly_detection: "n_anomalies",
};

export function primaryMetricFor(taskType: TaskType | string | null | undefined): string {
  if (!taskType) return "accuracy";
  if (taskType === "ambiguous") return "accuracy";
  return DEFAULT_PRIMARY_METRIC[taskType] ?? "accuracy";
}

export function metricDescriptorsFor(taskType: string): MetricDescriptor[] {
  if (taskType === "ambiguous") return TASK_METRIC_DESCRIPTORS.classification;
  return TASK_METRIC_DESCRIPTORS[taskType] ?? TASK_METRIC_DESCRIPTORS.classification;
}

/** Read a metrics dict by key, tolerating absent keys. */
export function metricValue(
  metrics: Record<string, unknown> | null | undefined,
  key: string,
): number | undefined {
  if (!metrics) return undefined;
  const value = metrics[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return undefined;
}