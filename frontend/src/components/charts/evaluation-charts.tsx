import { AlertTriangle } from "lucide-react";

import { ChartCard } from "@/components/charts/chart-card";
import { ConfusionMatrix } from "@/components/charts/confusion-matrix";
import { PrecisionRecallCurve, RocCurve } from "@/components/charts/curves";
import { formatScore } from "@/lib/format";
import type {
  AnomalyMetrics,
  ClassificationMetrics,
  ClusteringMetrics,
  EvaluationReport,
  RegressionMetrics,
  TaskMetrics,
} from "@/types/model";

interface Tile {
  label: string;
  value: string;
}

function tilesFor(metrics: TaskMetrics): Tile[] {
  const t = metrics.task;
  if (t === "classification") {
    const m = metrics as ClassificationMetrics;
    return [
      { label: "Accuracy", value: formatScore(m.accuracy) },
      { label: "Precision (macro)", value: formatScore(m.precision_macro) },
      { label: "Recall (macro)", value: formatScore(m.recall_macro) },
      { label: "F1 (macro)", value: formatScore(m.f1_macro) },
      ...(m.roc_auc != null ? [{ label: "ROC AUC", value: formatScore(m.roc_auc) }] : []),
      ...(m.average_precision != null
        ? [{ label: "Avg precision", value: formatScore(m.average_precision) }]
        : []),
    ];
  }
  if (t === "regression") {
    const m = metrics as RegressionMetrics;
    return [
      { label: "RMSE", value: formatScore(m.rmse) },
      { label: "MAE", value: formatScore(m.mae) },
      { label: "R²", value: formatScore(m.r2) },
    ];
  }
  if (t === "clustering") {
    const m = metrics as ClusteringMetrics;
    return [
      { label: "Clusters", value: String(m.n_clusters) },
      { label: "Silhouette", value: formatScore(m.silhouette_score) },
      { label: "Davies–Bouldin", value: formatScore(m.davies_bouldin_score) },
      { label: "Calinski–Harabasz", value: formatScore(m.calinski_harabasz_score) },
    ];
  }
  if (t === "anomaly_detection") {
    const m = metrics as AnomalyMetrics;
    return [
      { label: "Anomalies", value: String(m.n_anomalies) },
      { label: "Total", value: String(m.n_total) },
      { label: "Detected contamination", value: formatScore(m.detected_contamination) },
      { label: "Expected contamination", value: formatScore(m.expected_contamination) },
    ];
  }
  return [];
}

export function EvaluationCharts({ evaluation }: { evaluation: EvaluationReport }) {
  const { metrics } = evaluation;
  const tiles = tilesFor(metrics);
  const classification = metrics.task === "classification" ? (metrics as ClassificationMetrics) : null;

  return (
    <div className="space-y-4">
      {tiles.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {tiles.map((tile) => (
            <div key={tile.label} className="rounded-md border border-border bg-card px-3 py-2">
              <p className="text-xs text-muted-foreground">{tile.label}</p>
              <p className="text-sm font-semibold tabular-nums">{tile.value}</p>
            </div>
          ))}
        </div>
      )}

      {evaluation.ambiguity_caveat && (
        <div className="flex gap-2 rounded-md border border-warning/40 bg-warning/5 p-3 text-xs text-warning">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          <span>{evaluation.ambiguity_caveat}</span>
        </div>
      )}

      {classification?.confusion_matrix && (
        <ChartCard
          title="Confusion matrix"
          description="Actual vs. predicted class counts on the held-out evaluation split."
        >
          <ConfusionMatrix matrix={classification.confusion_matrix} />
        </ChartCard>
      )}

      {classification && (classification.roc_curve?.length ?? 0) > 1 && (
        <ChartCard
          title="ROC curve"
          description={`True vs. false positive rate${
            classification.roc_auc != null ? ` · AUC ${classification.roc_auc.toFixed(3)}` : ""
          }.`}
        >
          <RocCurve curve={classification.roc_curve!} auc={classification.roc_auc} />
        </ChartCard>
      )}

      {classification && (classification.precision_recall_curve?.length ?? 0) > 1 && (
        <ChartCard
          title="Precision–recall curve"
          description="Precision against recall across decision thresholds."
        >
          <PrecisionRecallCurve
            curve={classification.precision_recall_curve!}
            averagePrecision={classification.average_precision}
          />
        </ChartCard>
      )}

      <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        Evaluated with <span className="font-medium text-foreground">{evaluation.model_info.model_type}</span> ·{" "}
        {evaluation.model_info.n_features} features · {evaluation.model_info.n_samples} samples
        {evaluation.mlflow_logged ? " · logged to MLflow" : ""}
      </div>
    </div>
  );
}
