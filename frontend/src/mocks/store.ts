/**
 * Demo-mode store: in-memory run registry + live run simulator.
 *
 * Seeds from `./seed/*` are materialized into full `Run` / `StageDetail` /
 * leaderboard / evaluation / explainability / artifacts records. Runs created
 * through `createDemoRun` advance on wall-clock timers so the product demo
 * (and the Playwright happy path) can watch a pipeline complete.
 */
import type { Run, RunRequest, RunSummary } from "@/types/run";
import type { StageDetail, StageSummary, PipelineStageId } from "@/types/pipeline";
import type { ModelRankingRow, EvaluationReport } from "@/types/model";
import type {
  ExplainabilityView,
  ExplanationReport,
  ExplanationSample,
} from "@/types/explainability";
import type { ArtifactManifest } from "@/types/artifact";
import { PIPELINE_STAGE_ORDER, STAGE_META } from "@/config/pipeline";
import { primaryMetricFor } from "@/config/metrics";
import { formatNumber } from "@/lib/format";
import { engineFromBytes } from "@/config/engine-limits";
import { createRng } from "@/mocks";
import {
  buildArtifacts,
  buildLogs,
  buildRankingRows,
  buildReportMarkdown,
  generateBeeswarm,
  generatePRCurve,
  generateRocCurve,
} from "./seed/helpers";
import type { DemoRunSeed } from "./seed/runs";
import { DEMO_RUN_SEEDS } from "./seed/runs";
import { DEMO_DATASETS } from "./seed/datasets";

export interface DemoRunRecord {
  run: Run;
  stages: StageDetail[];
  datasetId: string | null;
  models: ModelRankingRow[];
  evaluation: EvaluationReport | null;
  explanation: ExplainabilityView | null;
  targetCandidates: { column: string; task_type: string; confidence: number }[];
  featureCount: number;
  reportMarkdown: string;
  artifacts: ArtifactManifest;
  logs: string[];
  createdAtMs: number;
}

export function hexId(len = 24): string {
  const bytes = crypto.getRandomValues(new Uint8Array(len));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/* ------------------------------------------------------------------ */
/* Stage assembly                                                     */
/* ------------------------------------------------------------------ */

/** Coerce a StageSummary value to a finite number (0 on missing). */
function num(v: string | number | boolean | null | undefined): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function stageLine(
  id: PipelineStageId,
  summary: StageSummary,
  ok: boolean,
  error?: string,
): string {
  if (!ok) return `  ✗ ${id} failed — ${error ?? "unknown error"}`;
  const detail = STAGE_LOG_DETAILS[id]?.(summary) ?? "";
  return `  ${detail ? `→ ${id} ${detail}` : `✓ ${id} completed`}`;
}

const STAGE_LOG_DETAILS: Partial<Record<PipelineStageId, (s: StageSummary) => string>> = {
  upload: (s) =>
    `Loaded ${formatNumber(num(s.rows))} rows × ${formatNumber(num(s.columns))} cols from '${String(s.name ?? "")}' (${String(s.engine ?? "")}).`,
  etl: (s) =>
    `Rows ${formatNumber(num(s.rows_before))} → ${formatNumber(num(s.rows_after))}; cleaned ${formatNumber(num(s.columns_affected))} column(s).`,
  validation: (s) =>
    s.passed
      ? `Validation passed (${formatNumber(num(s.duplicate_rows))} duplicate rows).`
      : "Validation failed.",
  eda: (s) =>
    `Profiled ${formatNumber(num(s.numeric_columns))} numeric / ${formatNumber(num(s.categorical_columns))} categorical columns.`,
  target_detection: (s) =>
    `Target='${String(s.target ?? "")}' → ${String(s.task ?? "")} (confidence ${String(s.confidence ?? "")}).`,
  feature_engineering: (s) =>
    `Engineered ${formatNumber(num(s.n_features))} features; recipe saved.`,
  model_selection: (s) =>
    `Tuned ${formatNumber(num(s.trials_used))} trial(s)${
      s.best ? `; best=${String(s.best)} (${String(s.score ?? "")})` : "."
    }${s.truncated ? " (truncated by time budget)" : ""}`,
  evaluation: (s) => `Test score: ${String(s.primary_metric ?? "")}=${String(s.score ?? "")}.`,
  explainability: (s) =>
    `Explainer=${String(s.explainer ?? "")} on ${formatNumber(num(s.samples))} samples.`,
  reporting: () => "Wrote report.md / report.html.",
  storage: (s) => `Persisted ${formatNumber(num(s.artifacts))} artifacts.`,
};

function summarize(id: PipelineStageId, seed: DemoRunSeed): StageSummary {
  const s = seed.summary;
  switch (id) {
    case "upload":
      return {
        rows: s.rows,
        columns: s.columns,
        format: s.fileFormat,
        name: s.datasetName,
        engine: s.engine,
      };
    case "etl":
      return {
        rows_before: s.rows,
        rows_after: s.rows,
        columns_affected: 0,
        null_strategy: seed.request.nullStrategy,
      };
    case "validation":
      return { passed: true, null_columns: 0, duplicate_rows: 0 };
    case "eda": {
      const ds = seed.datasetId ? DEMO_DATASETS[seed.datasetId] : null;
      return {
        numeric_columns: ds?.profile.numeric_columns.length ?? 0,
        categorical_columns: ds?.profile.categorical_columns.length ?? 0,
        memory_bytes: ds?.profile.memory_bytes ?? 0,
      };
    }
    case "target_detection": {
      const cand = seed.targetCandidates?.[0];
      return {
        target: cand?.column ?? null,
        task: cand?.task_type ?? s.taskType,
        confidence: cand?.confidence ?? 0,
        candidates: seed.targetCandidates?.length ?? 0,
      };
    }
    case "feature_engineering":
      return {
        n_features: Math.max(1, s.columns - 1),
        n_target_encoded: 0,
        transformer: "make_pipeline",
      };
    case "model_selection":
      return {
        trials_used: s.trialCount ?? 0,
        truncated: s.hpoTruncated ?? false,
        best: s.bestModelType ?? null,
        score: s.bestScore ?? null,
        max_trials: seed.request.maxTrials ?? null,
      };
    case "evaluation":
      return { primary_metric: s.primaryMetric, score: s.bestScore ?? null, task: s.taskType };
    case "explainability":
      return {
        explainer: seed.explanation?.explainer_type ?? "TreeExplainer",
        samples: seed.explanation?.n_samples_used ?? 100,
        sampled: seed.explanation?.sampled ?? false,
      };
    case "reporting":
      return { formats: "markdown,html,json" };
    case "storage":
      return { artifacts: 18, engine: s.engine };
  }
}

function assembleStages(seed: DemoRunSeed): StageDetail[] {
  const baseOrder: (PipelineStageId | "node_sampling")[] = [...seed.request.stages];
  if (seed.sampling?.was_sampled) {
    const idx = baseOrder.indexOf("model_selection");
    if (idx !== -1) baseOrder.splice(idx, 0, "node_sampling");
  }
  const createdAtMs = Date.parse(seed.summary.createdAt);
  let cursor = createdAtMs;
  return baseOrder.map((id) => {
    const override = seed.stageOverrides?.[id as PipelineStageId];
    const isSampling = id === "node_sampling";
    const status = override?.status ?? "completed";
    const summary = isSampling
      ? {
          method: seed.sampling?.sampling_method ?? null,
          ratio: seed.sampling?.sampling_ratio ?? null,
          original_rows: seed.sampling?.original_rows ?? null,
          sample_rows: seed.sampling?.sample_rows ?? null,
        }
      : (override?.summary ?? summarize(id as PipelineStageId, seed));
    const baseDuration = (STAGE_BASE_DURATIONS_MS[id as PipelineStageId] ?? 1.4) * 1000;

    const queuedAt = new Date(cursor).toISOString();
    let startedAt: string | null = null;
    let completedAt: string | null = null;
    let durationMs: number | null = null;
    if (status === "completed" || status === "warning" || status === "failed") {
      startedAt = new Date(cursor + 400).toISOString();
      completedAt = new Date(cursor + 400 + baseDuration).toISOString();
      durationMs = baseDuration;
      cursor += 400 + baseDuration;
    } else if (status === "running") {
      startedAt = new Date(cursor + 400).toISOString();
      cursor += 400;
    } else if (status === "skipped") {
      cursor += 120;
    }
    const ok = status === "completed" || status === "warning";
    const logs =
      override?.logs ??
      (isSampling
        ? [
            "[phronesisml] Running agent: node_sampling",
            `  → Sampling ${seed.sampling?.sampling_method ?? "stratified"} ${String(summary.ratio ?? "")} of rows for model selection.`,
            `[phronesisml] Agent 'node_sampling' completed.`,
          ]
        : [
            `[phronesisml] Running agent: ${id}`,
            stageLine(id as PipelineStageId, summary, ok, override?.error?.message),
          ]);
    return {
      id,
      name: isSampling ? "Node Sampling" : STAGE_META[id as PipelineStageId].label,
      status,
      queuedAt,
      startedAt,
      completedAt,
      durationMs,
      summary,
      logs,
      error: override?.error ?? null,
    };
  });
}

/** Base per-stage runtime used by the seed assembler. */
const STAGE_BASE_DURATIONS_MS: Partial<Record<PipelineStageId, number>> = {
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

/* ------------------------------------------------------------------ */
/* Views derived from a seed                                          */
/* ------------------------------------------------------------------ */

function buildExplainabilityView(seed: DemoRunSeed): ExplainabilityView | null {
  const report = seed.explanation;
  if (!report) return null;
  const importance = Object.entries(report.feature_importance)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => b.value - a.value);
  return {
    report,
    importance,
    beeswarm: generateBeeswarm(report.feature_importance, seed.explanationSeed ?? 1),
    baseValue: seed.explainBaseValue ?? 0.265,
    prediction: seed.explainPrediction ?? 0.87,
    predictionLabel: seed.explainPredictionLabel,
    sampleId: seed.explainSampleId ?? 42,
  };
}

function buildRunSeed(seed: DemoRunSeed): DemoRunRecord {
  const stages = assembleStages(seed);
  const executed = stages
    .filter((s) => s.status === "completed" || s.status === "warning")
    .map((s) => s.id as PipelineStageId);

  const artifacts = buildArtifacts(seed.summary.id, seed.summary.status, {
    model: seed.summary.bestModelType != null,
    explainability: seed.explanation != null,
    report: seed.summary.status === "completed" && seed.summary.bestModelType != null,
    truncatedFiles: seed.truncatedArtifacts,
  });

  const targetCandidates = seed.targetCandidates ?? [];
  const featureCount = Math.max(1, seed.summary.columns - 1);

  const reportMarkdown = buildReportMarkdown({
    summary: seed.summary,
    rows: seed.summary.rows,
    columns: seed.summary.columns,
    candidates: seed.models.map((m) => ({
      name: m.name,
      score: m.score,
      trials_used: m.trials_used,
      time_elapsed: m.time_elapsed,
    })),
    evaluation: seed.evaluation,
    explanation: seed.explanation ?? undefined,
    targetCandidates,
    featureCount,
    sampling: seed.sampling,
  });

  const run: Run = {
    id: seed.summary.id,
    status: seed.summary.status,
    request: seed.request,
    summary: seed.summary,
    sampling: seed.sampling,
    resourceReport: seed.resourceReport,
    warnings: seed.warnings,
    error: seed.error
      ? { type: seed.error.type, message: seed.error.message, context: seed.error.context }
      : null,
    logs: seed.logs,
    stagesRequested: seed.request.stages,
    stagesExecuted: executed,
    totalDurationMs: seed.summary.durationMs,
    createdAt: seed.summary.createdAt,
    updatedAt: seed.summary.updatedAt,
  };

  return {
    run,
    stages,
    datasetId: seed.datasetId,
    models: buildRankingRows(seed.models),
    evaluation: seed.evaluation,
    explanation: buildExplainabilityView(seed),
    targetCandidates,
    featureCount,
    reportMarkdown,
    artifacts,
    logs: seed.logs,
    createdAtMs: Date.parse(seed.summary.createdAt),
  };
}

/* ------------------------------------------------------------------ */
/* Registry                                                           */
/* ------------------------------------------------------------------ */

const records = new Map<string, DemoRunRecord>();
const TICK_MS = 550;

for (const seed of DEMO_RUN_SEEDS) {
  records.set(seed.summary.id, buildRunSeed(seed));
}

// Seed runs that are mid-flight also advance on the simulator clock so the
// demo never shows a pipeline frozen mid-run forever.
for (const record of records.values()) {
  if (record.run.status === "running" || record.run.status === "queued") {
    scheduleAdvance(record.run.id);
  }
}

export function getRecord(runId: string): DemoRunRecord | undefined {
  return records.get(runId);
}

export function allRecords(): DemoRunRecord[] {
  return [...records.values()].sort((a, b) => b.createdAtMs - a.createdAtMs);
}

/* ------------------------------------------------------------------ */
/* Created-run synthesis + simulator                                  */
/* ------------------------------------------------------------------ */

export interface SyntheticRunInput extends Omit<RunRequest, "dataPath"> {
  datasetId?: string;
  fileName?: string;
}

interface SyntheticModel {
  name: string;
  score: number;
  best?: boolean;
  trials_used: number;
  time_elapsed: number;
  cost: string;
  secondary: Record<string, number>;
  bestParams?: Record<string, unknown>;
  value: number;
}

function modelPool(taskType: string, rng: () => number): SyntheticModel[] {
  const jitter = (base: number) => Math.max(0.001, base + (rng() - 0.5) * 0.02);
  if (taskType === "clustering") {
    const m1 = {
      name: "kmeans",
      score: jitter(0.42),
      trials_used: 6,
      time_elapsed: 14.2,
      cost: "low",
      value: 0.42,
      secondary: { davies_bouldin_score: 0.58, calinski_harabasz_score: 2690 },
    };
    const m2 = {
      name: "agglomerative",
      score: jitter(0.39),
      trials_used: 4,
      time_elapsed: 9.6,
      cost: "low",
      secondary: { davies_bouldin_score: 0.63, calinski_harabasz_score: 2405 },
      value: 0.39,
    };
    return rng() > 0.5 ? [m2, m1] : [m1, m2];
  }
  if (taskType === "regression") {
    const pool: SyntheticModel[] = [
      {
        name: "linear_regression",
        score: jitter(0.6),
        trials_used: 10,
        time_elapsed: 4.2,
        cost: "low",
        value: 0.6,
        secondary: { rmse: 6400, mae: 3100 },
      },
      {
        name: "random_forest",
        score: jitter(0.82),
        trials_used: 26,
        time_elapsed: 34.6,
        cost: "medium",
        value: 0.82,
        secondary: { rmse: 4200, mae: 2100 },
      },
      {
        name: "gradient_boosting",
        score: jitter(0.89),
        trials_used: 31,
        time_elapsed: 44.1,
        cost: "high",
        value: 0.89,
        secondary: { rmse: 3300, mae: 1700 },
        bestParams: { learning_rate: 0.05, max_depth: 4, n_estimators: 300 },
      },
    ];
    return pool;
  }
  const pool: SyntheticModel[] = [
    {
      name: "logistic_regression",
      score: jitter(0.71),
      trials_used: 14,
      time_elapsed: 4.8,
      cost: "low",
      value: 0.71,
      secondary: { f1_macro: 0.68, roc_auc: 0.75 },
    },
    {
      name: "random_forest",
      score: jitter(0.9),
      trials_used: 34,
      time_elapsed: 38.2,
      cost: "medium",
      value: 0.9,
      secondary: { f1_macro: 0.88, roc_auc: 0.93, precision_macro: 0.87, recall_macro: 0.86 },
      bestParams: { n_estimators: 200, max_depth: 16, min_samples_split: 4 },
    },
    {
      name: "gradient_boosting",
      score: jitter(0.87),
      trials_used: 28,
      time_elapsed: 51.3,
      cost: "high",
      value: 0.87,
      secondary: { f1_macro: 0.85, roc_auc: 0.9, precision_macro: 0.86, recall_macro: 0.84 },
    },
  ];
  return pool;
}

function buildSyntheticRun(request: SyntheticRunInput): DemoRunRecord {
  const dataset = request.datasetId ? DEMO_DATASETS[request.datasetId] : null;
  const summary = dataset?.summary;
  const taskType = (request.taskOverride ?? summary?.taskType ?? "classification") as NonNullable<
    RunSummary["taskType"]
  >;
  const target = request.targetOverride ?? summary?.targetColumn ?? null;
  const runId = `run_${hexId(24)}`;
  const createdAtMs = Date.now();

  const order = request.stages.length ? request.stages : PIPELINE_STAGE_ORDER;
  const sampling = null as Run["sampling"];
  const totalRows = summary?.rows ?? 5000;
  const fileFormat = summary?.format ?? "csv";

  const stageList: StageDetail[] = order.map((stageId) => ({
    id: stageId,
    name: STAGE_META[stageId].label,
    status: "queued",
    queuedAt: null,
    startedAt: null,
    completedAt: null,
    durationMs: null,
    summary: {},
    logs: [`[phronesisml] Running agent: ${stageId}`],
    error: null,
  }));

  const requestWith: RunRequest = {
    ...request,
    nullStrategy: request.nullStrategy ?? "drop",
    stages: order,
    mode: request.mode ?? "balanced",
  };

  const run: Run = {
    id: runId,
    status: "queued",
    request: requestWith,
    summary: {
      id: runId,
      datasetName: summary?.name ?? request.fileName ?? "uploaded.csv",
      datasetPath: summary?.path ?? request.fileName ?? "",
      fileFormat,
      rows: summary?.rows ?? totalRows,
      columns: summary?.columns ?? 10,
      fileSizeBytes: summary?.sizeBytes ?? 1_000_000,
      taskType,
      targetColumn: target,
      engine: "pandas" as RunSummary["engine"],
      engineReason: "Engine will be selected after upload.",
      bestModelType: null,
      bestScore: null,
      primaryMetric: primaryMetricFor(taskType),
      status: "queued",
      mode: requestWith.mode,
      createdAt: new Date(createdAtMs).toISOString(),
      updatedAt: new Date(createdAtMs).toISOString(),
      durationMs: null,
      stagesRequested: order,
    },
    sampling,
    resourceReport: null,
    warnings: [],
    error: null,
    logs: [],
    stagesRequested: order,
    stagesExecuted: [],
    totalDurationMs: null,
    createdAt: new Date(createdAtMs).toISOString(),
    updatedAt: new Date(createdAtMs).toISOString(),
  };

  const record: DemoRunRecord = {
    run,
    stages: stageList,
    datasetId: request.datasetId ?? null,
    models: [],
    evaluation: null,
    explanation: null,
    targetCandidates: [],
    featureCount: Math.max(1, (summary?.columns ?? 10) - 1),
    reportMarkdown: "",
    artifacts: buildArtifacts(runId, "queued", {
      model: false,
      explainability: taskType !== "clustering",
      report: false,
    }),
    logs: [],
    createdAtMs,
  };
  records.set(runId, record);
  return record;
}

function seedFromString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0;
  return h >>> 0;
}

function scheduleAdvance(runId: string) {
  setTimeout(() => advance(runId, Date.now()), TICK_MS);
}

/** Advance simulation by one step: finish running stage / start next. */
function advance(runId: string, nowMs: number) {
  const record = records.get(runId);
  if (!record) return;
  const { run, stages } = record;
  if (run.status !== "running" && run.status !== "queued") return;

  const activeIdx = stages.findIndex((s) => s.status === "running");
  if (activeIdx !== -1) {
    finalizeStage(record, activeIdx, nowMs);
    const next = stages.findIndex((s, i) => i > activeIdx && s.status === "queued");
    if (next === -1) {
      completeRun(record, nowMs);
      return;
    }
    startStage(stages[next], nowMs);
    run.status = "running";
    run.updatedAt = new Date(nowMs).toISOString();
    scheduleAdvance(runId);
    return;
  }

  const firstQueued = stages.findIndex((s) => s.status === "queued" || s.status === "idle");
  if (firstQueued === -1) {
    completeRun(record, nowMs);
    return;
  }
  if (run.status === "queued") {
    run.status = "running";
  }
  startStage(stages[firstQueued], nowMs);
  run.updatedAt = new Date(nowMs).toISOString();
  scheduleAdvance(runId);
}

function startStage(stage: StageDetail, nowMs: number) {
  stage.status = "running";
  stage.startedAt = new Date(nowMs).toISOString();
  stage.queuedAt = stage.queuedAt ?? new Date(nowMs - 120).toISOString();
  stage.logs = [`[phronesisml] Running agent: ${stage.id}`];
}

function finalizeStage(record: DemoRunRecord, idx: number, nowMs: number) {
  const stage = record.stages[idx];
  const durationMs = TICK_MS;
  stage.status = "completed";
  stage.completedAt = new Date(nowMs).toISOString();
  stage.durationMs = durationMs;
  const summary = syntheticSummary(stage.id, record, idx);
  stage.summary = summary;
  stage.logs = [
    `[phronesisml] Running agent: ${stage.id}`,
    stageDetailLine(stage.id, summary),
    `[phronesisml] Agent '${stage.id}' completed successfully.`,
  ];
}

function stageDetailLine(id: string, summary: StageSummary): string {
  switch (id) {
    case "upload":
      return `  → Loaded ${formatNumber(num(summary.rows))} rows × ${formatNumber(num(summary.columns))} cols.`;
    case "etl":
      return `  → Cleaned nulls (${String(summary.null_strategy ?? "")}); reduced ${formatNumber(num(summary.rows_before))} → ${formatNumber(num(summary.rows_after))} rows.`;
    case "validation":
      return `  → Validation passed (${formatNumber(num(summary.duplicate_rows))} duplicate rows).`;
    case "eda":
      return `  → Profiled ${formatNumber(num(summary.numeric_columns))} numeric / ${formatNumber(num(summary.categorical_columns))} categorical.`;
    case "target_detection":
      return `  → Target=${summary.target ?? "—"} (${summary.task ?? "—"}, confidence ${String(summary.confidence ?? "")}).`;
    case "feature_engineering":
      return `  → Engineered ${formatNumber(num(summary.n_features))} features.`;
    case "model_selection":
      return `  → Best: ${String(summary.best ?? "")} ${String(summary.score ?? "")} after ${formatNumber(num(summary.trials_used))} trials.`;
    case "evaluation":
      return `  → Test ${String(summary.primary_metric ?? "")}: ${String(summary.score ?? "")}.`;
    case "explainability":
      return `  → ${String(summary.explainer ?? "TreeExplainer")} on ${formatNumber(num(summary.samples))} samples.`;
    case "reporting":
      return "  → Wrote report.md / report.html.";
    case "storage":
      return `  → Persisted ${formatNumber(num(summary.artifacts))} artifacts.`;
    case "node_sampling":
      return `  → Sampling ${String(summary.ratio ?? "")} of rows for model selection.`;
    default:
      return "  → done.";
  }
}

function syntheticSummary(id: string, record: DemoRunRecord, idx: number): StageSummary {
  const run = record.run;
  const taskType = run.summary.taskType;
  const rng = createRng(seedFromString(run.id) + idx * 7 + 1);
  const rows = run.summary.rows;
  const cols = run.summary.columns;
  const ds = record.datasetId ? DEMO_DATASETS[record.datasetId] : null;
  switch (id) {
    case "upload":
      return { rows, columns: cols, format: run.summary.fileFormat, engine: run.summary.engine };
    case "etl":
      return {
        rows_before: rows,
        rows_after: rows,
        columns_affected: 1 + Math.floor(rng() * 3),
        null_strategy: run.request.nullStrategy,
      };
    case "validation":
      return { passed: true, duplicate_rows: Math.floor(rng() * 40), null_columns: 0 };
    case "eda":
      return {
        numeric_columns: ds?.profile.numeric_columns.length ?? Math.floor(cols * 0.6),
        categorical_columns: ds?.profile.categorical_columns.length ?? Math.ceil(cols * 0.4),
      };
    case "target_detection":
      return { target: run.summary.targetColumn, task: taskType, confidence: 0.6 + rng() * 0.35 };
    case "feature_engineering":
      return { n_features: Math.max(1, cols - 1), strategy: run.request.nullStrategy };
    case "model_selection":
      return { trials_used: 0, best: "…", score: "" };
    case "evaluation":
      return { primary_metric: run.summary.primaryMetric, score: "" };
    case "explainability":
      return { explainer: "TreeExplainer", samples: 100, sampled: true };
    case "reporting":
      return { formats: "markdown,html,json" };
    case "storage":
      return { artifacts: 18 };
    default:
      return {};
  }
}

function completeRun(record: DemoRunRecord, nowMs: number) {
  const { run } = record;
  run.status = "completed";
  run.updatedAt = new Date(nowMs).toISOString();
  run.summary.status = "completed";
  run.summary.updatedAt = run.updatedAt;
  run.summary.durationMs = nowMs - record.createdAtMs;

  const taskType = run.summary.taskType;
  const rng = createRng(seedFromString(run.id));
  const pool = modelPool(taskType, rng)
    .slice()
    .sort((a, b) => b.score - a.score)
    .map<SyntheticModel>((m, i) => ({ ...m, best: i === 0 }));

  const best = pool[0];
  run.summary.bestModelType = bestPoolName(best.name);
  run.summary.bestScore = Number(best.score.toFixed(4));
  run.summary.trialCount = pool.reduce((a, m) => a + m.trials_used, 0);
  run.summary.engine = inferEngine(run.summary.fileSizeBytes);

  record.models = pool.map((m, i) => ({
    rank: i + 1,
    model_type: m.name,
    primary_score: Number(m.score.toFixed(4)),
    secondary_metrics: m.secondary,
    trials_used: m.trials_used,
    time_elapsed: m.time_elapsed,
    truncated: false,
    estimated_training_cost: m.cost,
    best: m.best ?? false,
    status: "ready" as const,
  }));
  record.evaluation = buildSyntheticEvaluation(record, pool, rng);
  record.explanation = taskType === "clustering" ? null : buildSyntheticExplanation(record);
  const targetCandidates = buildTargetCandidates(record, rng);
  record.targetCandidates = targetCandidates;
  record.reportMarkdown = buildReportMarkdown({
    summary: run.summary,
    rows: run.summary.rows,
    columns: run.summary.columns,
    candidates: pool.map((m) => ({
      name: m.name,
      score: Number(m.score.toFixed(4)),
      trials_used: m.trials_used,
      time_elapsed: m.time_elapsed,
    })),
    evaluation: record.evaluation,
    explanation: record.explanation?.report,
    targetCandidates,
    featureCount: record.featureCount,
    sampling: record.run.sampling,
  });
  record.artifacts = buildArtifacts(run.id, "completed", {
    model: true,
    explainability: taskType !== "clustering",
    report: true,
  });
  record.logs = buildLogs(run.id, run.stagesRequested);

  // enrich stage summaries with final results
  const modelStage = record.stages.find((s) => s.id === "model_selection");
  if (modelStage) {
    modelStage.summary = {
      trials_used: run.summary.trialCount,
      truncated: false,
      best: run.summary.bestModelType,
      score: run.summary.bestScore,
    };
    modelStage.logs = [
      `[phronesisml] Running agent: model_selection`,
      `  → Best: ${run.summary.bestModelType} ${run.summary.bestScore} after ${formatNumber(run.summary.trialCount ?? 0)} trials.`,
      `[phronesisml] Agent 'model_selection' completed successfully.`,
    ];
  }
  const evalStage = record.stages.find((s) => s.id === "evaluation");
  if (evalStage) {
    evalStage.summary = { primary_metric: run.summary.primaryMetric, score: run.summary.bestScore };
    evalStage.logs = [
      `[phronesisml] Running agent: evaluation`,
      `  → Test ${run.summary.primaryMetric}: ${run.summary.bestScore}.`,
      `[phronesisml] Agent 'evaluation' completed successfully.`,
    ];
  }
}

/** Map internal model names to backend-friendly class names. */
export function bestPoolName(name: string): string {
  return name
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join("");
}

function inferEngine(bytes: number): RunSummary["engine"] {
  return engineFromBytes(bytes);
}

function buildSyntheticEvaluation(
  record: DemoRunRecord,
  pool: SyntheticModel[],
  rng: () => number,
): EvaluationReport | null {
  const best = pool[0];
  const taskType = record.run.summary.taskType;
  const base = taskType === "clustering" ? 4 : 2;
  const nSamples = record.run.sampling?.sample_rows ?? record.run.summary.rows;
  const sampleN = Math.max(100, Math.min(nSamples, 2000));
  if (taskType === "clustering") {
    return {
      task_type: "clustering",
      metrics: {
        task: "clustering",
        n_clusters: 4,
        silhouette_score: Number(best.value.toFixed(4)),
        davies_bouldin_score: 0.61,
        calinski_harabasz_score: 2684,
      },
      model_info: {
        model_type: bestPoolName(best.name),
        model_module: "sklearn.cluster",
        best_params: { n_clusters: 4, n_init: 10, random_state: 42 },
        n_features: record.featureCount,
        n_samples: sampleN,
      },
      ambiguity_caveat: null,
      mlflow_logged: false,
    };
  }
  if (taskType === "regression") {
    const r2 = best.value;
    return {
      task_type: "regression",
      metrics: {
        task: "regression",
        rmse: Math.round(3200 + rng() * 900),
        mae: Math.round(1700 + rng() * 500),
        r2: Number(r2.toFixed(4)),
      },
      model_info: {
        model_type: bestPoolName(best.name),
        model_module:
          best.name === "linear_regression"
            ? "sklearn.linear_model"
            : best.name === "random_forest"
              ? "sklearn.ensemble"
              : "sklearn.ensemble",
        best_params: best.bestParams ?? {},
        n_features: record.featureCount,
        n_samples: sampleN,
      },
      ambiguity_caveat: null,
      mlflow_logged: false,
    };
  }
  const c0 = Math.round(sampleN * base * 0.18);
  const c1 = Math.round(sampleN * base * 0.1);
  return {
    task_type: "classification",
    metrics: {
      task: "classification",
      accuracy: Number(best.value.toFixed(4)),
      precision_macro: Number((best.value - 0.02).toFixed(4)),
      recall_macro: Number((best.value - 0.03).toFixed(4)),
      f1_macro: Number((best.value - 0.01).toFixed(4)),
      confusion_matrix: [
        [c0, Math.round(c0 * 0.2)],
        [Math.round(c1 * 0.25), c1],
      ],
      roc_curve: generateRocCurve(Math.round(rng() * 1000), Number((best.value + 0.04).toFixed(3))),
      roc_auc: Number((best.value + 0.04).toFixed(4)),
      precision_recall_curve: generatePRCurve(Math.round(rng() * 1000) + 1, best.value - 0.04),
      average_precision: Number((best.value - 0.04).toFixed(4)),
    },
    model_info: {
      model_type: bestPoolName(best.name),
      model_module:
        best.name === "logistic_regression" ? "sklearn.linear_model" : "sklearn.ensemble",
      best_params: best.bestParams ?? {},
      n_features: record.featureCount,
      n_samples: sampleN,
    },
    ambiguity_caveat: null,
    mlflow_logged: false,
  };
}

function buildSyntheticExplanation(record: DemoRunRecord): ExplainabilityView | null {
  const ds = record.datasetId ? DEMO_DATASETS[record.datasetId] : null;
  const numeric = ds?.profile.numeric_columns ?? [];
  const categorical = ds?.profile.categorical_columns ?? [];
  const columns = [...numeric.slice(0, 5), ...categorical.slice(0, 5)];
  if (!columns.length) return null;
  const raw: Record<string, number> = {};
  columns.forEach((f, i) => {
    raw[f] = Number((0.5 - i * 0.045 + (i % 3) * 0.02).toFixed(4));
  });
  const report: ExplanationReport = {
    feature_importance: raw,
    explainer_type: "TreeExplainer",
    sampled: true,
    n_samples_used: 100,
    n_features_used: columns.length,
    max_samples: 100,
  };
  const importance = Object.entries(raw)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => b.value - a.value);
  const seed = seedFromString(record.run.id);

  // Derive a handful of synthetic background samples so the sample stepper
  // can drill into per-row attributions without extra API calls.
  const samples: ExplanationSample[] = Array.from({ length: 12 }, (_, k) => {
    const rng = createRng(seed ^ ((k + 1) * 2654435761));
    const perSample: Record<string, number> = {};
    for (const [feature, mag] of Object.entries(raw)) {
      perSample[feature] = Number(Math.max(0.005, mag * (0.75 + rng() * 0.5)).toFixed(4));
    }
    const sampleImportance = Object.entries(perSample)
      .map(([feature, value]) => ({ feature, value }))
      .sort((a, b) => b.value - a.value);
    const base = Number((0.2 + rng() * 0.15).toFixed(3));
    const prediction = Number(Math.min(1, Math.max(0, base + rng() * 0.25 + 0.4)).toFixed(3));
    return {
      sampleId: k,
      baseValue: base,
      prediction,
      importance: sampleImportance,
      beeswarm: generateBeeswarm(perSample, seed ^ ((k + 3) * 40503)),
    };
  });

  return {
    report,
    importance,
    beeswarm: generateBeeswarm(raw, seed),
    baseValue: samples[0].baseValue,
    prediction: samples[0].prediction,
    sampleId: 0,
    samples,
  };
}

function buildTargetCandidates(
  record: DemoRunRecord,
  rng: () => number,
): { column: string; task_type: string; confidence: number }[] {
  const target = record.run.summary.targetColumn;
  if (!target) return [];
  const cand: { column: string; task_type: string; confidence: number }[] = [];
  if (record.run.summary.taskType !== "clustering") {
    cand.push({
      column: target,
      task_type: record.run.summary.taskType,
      confidence: Number((0.6 + rng() * 0.35).toFixed(2)),
    });
    cand.push({ column: "id", task_type: "excluded", confidence: 0 });
  }
  return cand;
}

/** Create a synthetic run (queued) and start its simulated execution. */
export function createDemoRun(request: SyntheticRunInput): Run {
  const record = buildSyntheticRun(request);
  scheduleAdvance(record.run.id);
  return record.run;
}

/** Force a created run through to completion synchronously (tests). */
export function finishCreatedRun(runId: string): void {
  const record = records.get(runId);
  if (!record || record.run.status === "completed") return;
  const now = Date.now();
  for (let i = 0; i < record.stages.length; i++) {
    const stage = record.stages[i];
    if (stage.status === "running" || stage.status === "queued" || stage.status === "idle") {
      stage.status = "completed";
      stage.startedAt = new Date(now).toISOString();
      stage.completedAt = new Date(now + 100).toISOString();
      stage.durationMs = 100;
      stage.summary = syntheticSummary(stage.id, record, i);
      stage.logs = [
        `[phronesisml] Running agent: ${stage.id}`,
        stageDetailLine(stage.id, stage.summary),
        `[phronesisml] Agent '${stage.id}' completed successfully.`,
      ];
    }
  }
  completeRun(record, now + 200);
}

/* ------------------------------------------------------------------ */
/* Lifecycle mutations (cancel / restore / delete demo parity)        */
/* ------------------------------------------------------------------ */

export type LifecycleResult =
  | { ok: true; record: DemoRunRecord }
  | { ok: false; reason: "not-found" | "not-active"; message: string };

const TERMINAL_STATUSES = new Set<Run["status"]>(["completed", "failed", "cancelled"]);

function stamp(record: DemoRunRecord, status: Run["status"]): void {
  const now = new Date().toISOString();
  record.run.status = status;
  record.run.summary.status = status;
  record.run.updatedAt = now;
  record.run.summary.updatedAt = now;
}

/** Cancel an active run (queued/running) — mirrors backend `cancel_run`. */
export function cancelDemoRun(runId: string): LifecycleResult {
  const record = records.get(runId);
  if (!record) return { ok: false, reason: "not-found", message: `Run '${runId}' was not found` };
  if (TERMINAL_STATUSES.has(record.run.status)) {
    return {
      ok: false,
      reason: "not-active",
      message: `Cannot cancel a run that has finished (${record.run.status}).`,
    };
  }
  for (const stage of record.stages) {
    if (stage.status === "running" || stage.status === "queued" || stage.status === "idle") {
      stage.status = "skipped";
      stage.completedAt = stage.startedAt ?? new Date().toISOString();
      stage.logs = [...stage.logs, `  ✗ Cancelled by user before this stage finished.`];
    }
  }
  record.run.stagesExecuted = record.stages
    .filter((s) => s.status === "completed" || s.status === "warning")
    .map((s) => s.id as PipelineStageId);
  stamp(record, "cancelled");
  return { ok: true, record };
}

/** Re-queue a terminal run with its original request — mirrors `restore_run`. */
export function restoreDemoRun(runId: string): LifecycleResult {
  const record = records.get(runId);
  if (!record) return { ok: false, reason: "not-found", message: `Run '${runId}' was not found` };
  if (!TERMINAL_STATUSES.has(record.run.status)) {
    return {
      ok: false,
      reason: "not-active",
      message: "Only finished runs can be restored.",
    };
  }
  const nowMs = Date.now();
  const isoNow = new Date(nowMs).toISOString();
  record.run.status = "queued";
  record.run.summary.status = "queued";
  record.run.updatedAt = isoNow;
  record.run.summary.updatedAt = isoNow;
  record.run.summary.durationMs = null;
  record.run.error = null;
  record.run.warnings = [];
  record.run.stagesExecuted = [];
  record.stages = record.run.stagesRequested.map((stageId) => ({
    id: stageId,
    name: STAGE_META[stageId].label,
    status: "queued",
    queuedAt: null,
    startedAt: null,
    completedAt: null,
    durationMs: null,
    summary: {},
    logs: [`[phronesisml] Running agent: ${stageId}`],
    error: null,
  }));
  record.models = [];
  record.evaluation = null;
  record.explanation = null;
  record.targetCandidates = [];
  record.reportMarkdown = "";
  record.artifacts = buildArtifacts(runId, "queued", {
    model: false,
    explainability: record.run.summary.taskType !== "clustering",
    report: false,
  });
  record.logs = [];
  scheduleAdvance(runId);
  return { ok: true, record };
}

/** Remove a run from the demo registry — mirrors `delete_run`. */
export function deleteDemoRun(runId: string): LifecycleResult {
  const record = records.get(runId);
  if (!record) return { ok: false, reason: "not-found", message: `Run '${runId}' was not found` };
  records.delete(runId);
  return { ok: true, record };
}
