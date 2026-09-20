import type {
  StageDetail,
  PipelineStageId,
} from "@/types/pipeline";
import type { RunSummary, SamplingInfo } from "@/types/run";
import type {
  Artifact,
  ArtifactFormat,
  ArtifactKind,
  ArtifactManifest,
} from "@/types/artifact";
import type { EvaluationReport, ModelRankingRow } from "@/types/model";
import type { ExplanationReport, ShapPoint } from "@/types/explainability";
import type { CurvePoint } from "@/types/model";
import { createRng } from "@/mocks";
import { STAGE_META, PIPELINE_STAGE_ORDER } from "@/config/pipeline";
import { TASK_LABELS } from "@/config/status";
import { formatNumber, formatPercent } from "@/lib/format";

/** Fixed backend version reported in demo mode. */
export const DEMO_VERSION = "0.3.1";

const STAGE_DURATIONS_SEC: Record<PipelineStageId, number> = {
  upload: 1.4,
  etl: 2.2,
  validation: 1.1,
  eda: 3.6,
  target_detection: 1.8,
  feature_engineering: 4.2,
  model_selection: 14.6,
  evaluation: 2.9,
  explainability: 4.1,
  reporting: 1.2,
  storage: 1.6,
};

/** Build the ordered stage list for a run from per-stage overrides. */
export function buildStages(
  _runId: string,
  createdAtMs: number,
  overrides: Partial<Record<PipelineStageId, Omit<StageDetail, "id" | "name">>> = {},
): StageDetail[] {
  let cursor = createdAtMs;
  return PIPELINE_STAGE_ORDER.map((id) => {
    const override = overrides[id];
    const baseDuration = (STAGE_DURATIONS_SEC[id] * 1000) as number;
    const startedAt = override ? null : new Date(cursor + 400).toISOString();
    const durationMs = override ? null : baseDuration;
    const completedAt =
      override === undefined
        ? new Date(cursor + 400 + baseDuration).toISOString()
        : null;
    if (override === undefined) cursor += 400 + baseDuration;
    return {
      id,
      name: STAGE_META[id].label,
      status: override?.status ?? "completed",
      queuedAt: new Date(cursor).toISOString(),
      startedAt,
      completedAt,
      durationMs,
      summary: override?.summary ?? {},
      logs: override?.logs ?? [
        `[phronesisml] Running agent: ${id}`,
        `[phronesisml] Agent '${id}' completed successfully.`,
      ],
      error: override?.error ?? null,
    };
  });
}

/** Standard deterministic runtime logs for a completed run. */
export function buildLogs(runId: string, stages: PipelineStageId[], extra: string[] = []): string[] {
  const version = DEMO_VERSION;
  const out = [
    `phronesisml v${version} — run ${runId}`,
    `status: completed`,
  ];
  for (const stage of stages) {
    out.push(`Running agent: ${stage}`);
    out.push(`  ✓ ${stage} completed`);
  }
  out.push("run complete", ...extra);
  return out;
}

/** Smooth ROC-style curve given an AUC target (single-class demo data). */
export function generateRocCurve(seed: number, auc: number, points = 24): CurvePoint[] {
  const rng = createRng(seed);
  const curve: CurvePoint[] = [{ x: 0, y: 0 }];
  for (let i = 1; i <= points; i++) {
    const t = i / points;
    const x = t;
    // logistic-ish monotone curve tuned to hit the target AUC at t=1.
    const base = Math.pow(x, 1 / Math.max(0.2, auc * 2.4));
    const noise = (rng() - 0.5) * 0.012 * t;
    let y = base + noise;
    y = Math.max(0, Math.min(1, y));
    if (y < curve[curve.length - 1].y) y = curve[curve.length - 1].y;
    curve.push({ x, y });
  }
  curve.push({ x: 1, y: 1 });
  return curve;
}

/** Generate a Precision-Recall curve from a target average precision. */
export function generatePRCurve(seed: number, ap: number, points = 24): CurvePoint[] {
  const rng = createRng(seed);
  const curve: CurvePoint[] = [];
  for (let i = 0; i <= points; i++) {
    const recall = i / points;
    const precision = ap + (1 - ap) * Math.exp(-recall * 6) + (rng() - 0.5) * 0.02;
    curve.push({ x: recall, y: Math.max(0, Math.min(1, precision)) });
  }
  return curve;
}

/** Deterministic beeswarm points from per-feature magnitudes. */
export function generateBeeswarm(
  importance: Record<string, number>,
  seed: number,
  pointsPerFeature = 48,
): ShapPoint[] {
  const rng = createRng(seed);
  const out: ShapPoint[] = [];
  for (const [feature, magnitude] of Object.entries(importance)) {
    for (let i = 0; i < pointsPerFeature; i++) {
      const direction = rng() < 0.5 ? -1 : 1;
      const dist = Math.pow(rng(), 1.6) * magnitude * 1.6;
      out.push({
        feature,
        shapValue: Number((direction * dist).toFixed(4)),
        featureValue: Number((rng() * 2 - 1).toFixed(3)),
      });
    }
  }
  return out;
}

/** Build the 18-file artifact set for a run. */
export function buildArtifacts(
  runId: string,
  runStatus: string,
  options: {
    model?: boolean;
    explainability?: boolean;
    report?: boolean;
    truncatedFiles?: string[];
  } = {},
): ArtifactManifest {
  const { model = true, explainability = true, report = true, truncatedFiles = [] } = options;

  const file = (
    name: string,
    kind: ArtifactKind,
    format: ArtifactFormat,
    bytes: number,
    description: string,
  ): Artifact => ({
    name,
    kind,
    format,
    sizeBytes: bytes,
    status: truncatedFiles.includes(name) ? "unavailable" : "available",
    reason: truncatedFiles.includes(name)
      ? `Not persisted — stage did not complete (status=${runStatus}).`
      : undefined,
    description,
  });

  const artifacts: Artifact[] = [
    file("config.json", "config", "json", 1840, "Configuration snapshot (PhronesisConfig)."),
    file("eda.json", "eda", "json", 4120, "Exploratory data analysis profile."),
    file("engine_selection.json", "engine_selection", "json", 980, "Engine selection & routing rationale."),
    file("evaluation.json", "evaluation", "json", 2310, "Full model evaluation report."),
    file("feature_metadata.json", "feature_metadata", "json", 2660, "Engineered feature names & transform recipe."),
    file("logs.txt", "logs", "txt", 18440, "Deterministic run log."),
    file("metrics.json", "metrics", "json", 1240, "Task-aware evaluation metrics."),
    file("model.json", "training", "json", 990, "Best pipeline / training summary."),
    file("pipeline.json", "pipeline", "json", 5140, "JSON pipeline report."),
    file("resource_estimation.json", "resource_estimation", "json", 1480, "Pre-flight resource estimate & sampling."),
    file("run_metadata.json", "run_metadata", "json", 1220, "Run metadata (id, status, engine, target)."),
    file("shap.json", "shap", "json", 840, "SHAP feature importance report."),
    file("target_detection.json", "target_detection", "json", 760, "Detected target & task with confidence."),
    file("training.json", "training", "json", 1720, "AutoML training / HPO summary."),
    file("validation.json", "validation", "json", 890, "Dataset validation report."),
  ];

  if (model)
    artifacts.push(file("model.joblib", "model_binary", "joblib", 782340, "Serialized trained model."));
  if (report) {
    artifacts.push(
      file("report.md", "report", "md", 8420, "Markdown pipeline report."),
      file("report.html", "report", "html", 29840, "Self-contained HTML pipeline report."),
    );
  }
  if (!explainability) {
    const shap = artifacts.find((a) => a.name === "shap.json");
    if (shap && !truncatedFiles.includes("shap.json")) {
      shap.status = "unavailable";
      shap.reason = `Not computed — explainability stage was skipped for this run (status=${runStatus}).`;
    }
  }

  const totalBytes = artifacts.reduce((acc, a) => acc + a.sizeBytes, 0);
  return { runId, artifactCount: artifacts.length, totalBytes, artifacts };
}

/** Extract the primary metric display value for a ranking row. */
export function buildRankingRows(
  modelSeeds: {
    name: string;
    score: number;
    best?: boolean;
    truncated?: boolean;
    trials_used: number;
    time_elapsed: number;
    cost: string;
    secondary?: Record<string, number>;
  }[],
): ModelRankingRow[] {
  return modelSeeds
    .slice()
    .sort((a, b) => b.score - a.score)
    .map((m, i) => ({
      rank: i + 1,
      model_type: m.name,
      primary_score: m.score,
      secondary_metrics: m.secondary ?? {},
      trials_used: m.trials_used,
      time_elapsed: m.time_elapsed,
      truncated: m.truncated ?? false,
      estimated_training_cost: m.cost,
      best: m.best ?? i === 0,
      status: "ready" as const,
    }));
}

/** Build a truthful-looking Markdown pipeline report from run data. */
export function buildReportMarkdown(input: {
  summary: RunSummary;
  rows: number;
  columns: number;
  candidates: { name: string; score: number; trials_used: number; time_elapsed: number }[] | null;
  evaluation?: EvaluationReport | null;
  explanation?: ExplanationReport | null;
  targetCandidates?: { column: string; task_type: string; confidence: number }[];
  validationPassed?: boolean;
  nullColumns?: string[];
  duplicateRows?: number;
  featureCount?: number;
  sampling?: SamplingInfo | null;
  ambiguityReason?: string | null;
}): string {
  const s = input.summary;
  const lines: string[] = [];
  lines.push(`# Phronesis Pipeline Report`, "");
  lines.push(`- **Run ID:** \`${s.id}\``);
  lines.push(`- **Status:** ${s.status}`);
  lines.push(`- **Dataset:** \`${s.datasetPath}\``);
  lines.push(`- **Rows:** ${formatNumber(input.rows)}`);
  lines.push(`- **Columns:** ${formatNumber(input.columns)}`);
  lines.push("", "## Summary", "");
  lines.push(
    `PhronesisML analyzed \`${s.datasetName}\` (${formatNumber(s.rows)} rows × ${formatNumber(
      s.columns,
    )} columns) with the **${s.engine}** engine. The best model was **${
      s.bestModelType ?? "—"
    }** with ${s.primaryMetric} = **${s.bestScore?.toFixed(4) ?? "—"}**.`,
  );
  lines.push(
    `Detected task: **${TASK_LABELS[s.taskType] ?? s.taskType}**${
      s.targetColumn ? `, target \`${s.targetColumn}\`` : ""
    }.`,
  );
  if (input.sampling?.was_sampled) {
    lines.push(
      "",
      "> **Sampled:** the pipeline sampled rows for expensive stages " +
        `(${formatNumber(input.sampling.original_rows ?? 0)} → ${formatNumber(
          input.sampling.sample_rows ?? 0,
        )} rows, method \`${input.sampling.sampling_method ?? "random"}\`).`,
    );
  }
  lines.push("", "## Data Validation", "");
  lines.push(
    input.validationPassed === false
      ? "- Validation reported issues."
      : "- Validation passed (schema and quality checks).",
  );
  if (input.nullColumns?.length) lines.push(`- Columns with missing values: \`${input.nullColumns.join("`, `")}\`.`);
  if (input.duplicateRows) lines.push(`- Duplicate rows found: ${formatNumber(input.duplicateRows)}.`);
  lines.push("", "## Exploratory Data Analysis", "");
  lines.push(`| | |`);
  lines.push(`|---|---|`);
  lines.push(`| Rows | ${formatNumber(input.rows)} |`);
  lines.push(`| Columns | ${formatNumber(input.columns)} |`);
  lines.push(`| Engine | ${s.engine} |`);
  lines.push("", "## Target Detection", "");
  if (s.targetColumn) {
    lines.push(
      `Target column \`${s.targetColumn}\` detected as **${TASK_LABELS[s.taskType] ?? s.taskType}**.`,
    );
    lines.push(`| Candidate | Task | Confidence |`);
    lines.push(`|---|---|---|`);
    for (const c of input.targetCandidates ?? []) {
      lines.push(`| \`${c.column}\` | ${c.task_type} | ${formatPercent(c.confidence)} |`);
    }
    if (input.ambiguityReason) lines.push("", `> ⚠ ${input.ambiguityReason}`);
  } else {
    lines.push("- No viable target column detected.");
  }
  lines.push("", "## Feature Engineering", "");
  lines.push(`- Engineered feature count: ${formatNumber(input.featureCount ?? 0)}.`);
  lines.push(
    "  Feature selection used variance > 0.01 and correlation to target > 0.05 (min features = 1).",
  );
  lines.push("", "## Model Selection", "");
  if (input.candidates?.length) {
    lines.push(`| Model | ${s.primaryMetric} | Trials | Time |`);
    lines.push(`|---|---|---|---|`);
    for (const c of input.candidates) {
      lines.push(
        `| ${c.name} | ${c.score.toFixed(4)} | ${c.trials_used} | ${c.time_elapsed.toFixed(1)}s |`,
      );
    }
  }
  lines.push("", "## Model Evaluation", "");
  if (input.evaluation) {
    const metrics = input.evaluation.metrics as unknown as Record<string, number | null | undefined>;
    const rows = Object.entries(metrics)
      .filter(([, v]) => typeof v === "number")
      .map(([k, v]) => `| ${k} | ${(v as number).toFixed(4)} |`);
    lines.push("| Metric | Value |", "|---|---|", ...rows);
  }
  lines.push("", "## Model Explainability", "");
  if (input.explanation) {
    const importance = Object.entries(input.explanation.feature_importance)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
    lines.push(`Explainer: **${input.explanation.explainer_type}**`, "");
    lines.push(`| Feature | Mean \\|SHAP\\| |`, `|---|---|`);
    for (const [f, v] of importance) lines.push(`| ${f} | ${v.toFixed(4)} |`);
  } else {
    lines.push("- Explainability was not computed for this run.");
  }
  lines.push("", "## Notes", "");
  lines.push(
    "- Scores are computed on a held-out test split (default 20%, random state 42).",
    "- `estimated_training_cost` reflects the heuristic rows × features × candidate complexity.",
  );
  return lines.join("\n");
}

/** Build target-detection candidate list for a run. */
export function buildTargetCandidates(
  target: string,
  taskType: string,
  confidence: number,
): { column: string; task_type: string; confidence: number }[] {
  return [
    { column: target, task_type: taskType, confidence },
    { column: "CustomerID", task_type: "excluded", confidence: 0 },
    { column: "TotalCharges", task_type: "regression", confidence: 0.31 },
  ];
}