/**
 * Demo-mode API handlers.
 *
 * These mirror the documented REST contract (see project_docs
 * frontend_ui_ux_design_blueprint §11) against the in-memory demo store, so a
 * future real adapter can replace them without reshaping the UI.
 */
import type { Page, ListQuery } from "@/types/api";
import { ApiError } from "@/types/api";
import type { Run, RunSummary, DashboardStats, RecentRunActivity } from "@/types/run";
import type { PipelineOverview, PipelineProgress, StageDetail } from "@/types/pipeline";
import type {
  Dataset,
  DatasetSummary,
  DatasetUploadResult,
  EngineRecommendation,
} from "@/types/dataset";
import type { ModelRankingRow, ModelDetail } from "@/types/model";
import type { ExplainabilityView } from "@/types/explainability";
import type { ReportInfo } from "@/types/report";
import type { ArtifactContent, ArtifactManifest, Artifact } from "@/types/artifact";
import type { HealthReport, CapabilitiesReport } from "@/types/health";
import { PIPELINE_STAGE_ORDER } from "@/config/pipeline";
import { PANDAS_MAX_BYTES, engineFromBytes, engineReason } from "@/config/engine-limits";
import { DEMO_VERSION } from "./seed/helpers";
import {
  DATASET_SEEDS,
  DEMO_DATASETS,
  registerDemoDataset,
  removeDemoDataset,
} from "./seed/datasets";
import {
  allRecords,
  getRecord,
  createDemoRun,
  bestPoolName,
  cancelDemoRun,
  restoreDemoRun,
  deleteDemoRun,
  hexId,
  type SyntheticRunInput,
} from "./store";

const LATENCY_MS = 120;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requireRecord(runId: string) {
  const record = getRecord(runId);
  if (!record) throw new ApiError(`Run '${runId}' was not found`, "NotFound", 404);
  return record;
}

function paginate<T>(items: T[], query: ListQuery): Page<T> {
  const page = query.page ?? 1;
  const pageSize = query.pageSize ?? 20;
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    pageSize,
    hasMore: start + pageSize < items.length,
  };
}

function sortBy<T>(items: T[], key: keyof T & string, order: "asc" | "desc"): T[] {
  return items.slice().sort((a, b) => {
    const av = a[key] as number | string | null | undefined;
    const bv = b[key] as number | string | null | undefined;
    if (av == null && bv == null) return 0;
    if (av == null) return order === "desc" ? 1 : -1;
    if (bv == null) return order === "desc" ? -1 : 1;
    if (av === bv) return 0;
    const cmp = av > bv ? 1 : -1;
    return order === "desc" ? -cmp : cmp;
  });
}

/* ------------------------------------------------------------------ */
/* Health / capabilities                                              */
/* ------------------------------------------------------------------ */

export async function demoHealth(): Promise<HealthReport> {
  await wait(90);
  return {
    status: "ok",
    version: DEMO_VERSION,
    python: "3.12",
    dependencies: {
      polars: { installed: true, version: "1.17" },
      pandas: { installed: true, version: "2.2" },
      scikit_learn: { installed: true, version: "1.5" },
      shap: { installed: true },
      pyspark: { installed: false, optional: true },
      matplotlib: { installed: true },
    },
    missing_core: [],
    database: { reachable: true },
    storage: {
      writable: true,
      paths: ["<demo-data-dir>", "<demo-runs-dir>"],
    },
  };
}

export async function demoCapabilities(): Promise<CapabilitiesReport> {
  await wait(90);
  return {
    name: "PhronesisML",
    version: DEMO_VERSION,
    offline: false,
    deterministic: true,
    task_types: ["classification", "regression", "clustering", "anomaly_detection", "ambiguous"],
    engines: ["pandas", "polars", "spark"],
    explainers: ["TreeExplainer", "PermutationExplainer", "KernelExplainer", "LinearExplainer"],
    pipeline_stages: PIPELINE_STAGE_ORDER,
    sdk_methods: [
      "analyze",
      "clean",
      "validate",
      "detect_target",
      "engineer",
      "select_model",
      "evaluate",
      "explain",
      "train",
      "predict",
      "save",
      "restore",
      "run_pipeline",
    ],
    cli_commands: [
      "phronesisml run",
      "phronesisml analyze",
      "phronesisml clean",
      "phronesisml train",
      "phronesisml serve",
    ],
    extras: ["mlflow"],
    optional_models: [
      { name: "xgboost", installed: true, version: "2.1.0", optional: true, reason: null },
      { name: "lightgbm", installed: true, version: "4.5.0", optional: true, reason: null },
      { name: "catboost", installed: false, optional: true, reason: "pip install catboost" },
    ],
  };
}

/* ------------------------------------------------------------------ */
/* Datasets                                                           */
/* ------------------------------------------------------------------ */

export async function demoListDatasets(query: ListQuery = {}): Promise<Page<DatasetSummary>> {
  await wait(LATENCY_MS);
  let items = DATASET_SEEDS.map((s) => s.summary);
  if (query.search) {
    const q = query.search.toLowerCase();
    items = items.filter((d) => d.name.toLowerCase().includes(q));
  }
  if (query.sort) items = sortBy(items, query.sort as keyof DatasetSummary, query.order ?? "desc");
  return paginate(items, query);
}

export async function demoGetDataset(id: string): Promise<Dataset> {
  await wait(LATENCY_MS);
  const dataset = DEMO_DATASETS[id];
  if (!dataset) throw new ApiError(`Dataset '${id}' was not found`, "NotFound", 404);
  return dataset;
}

export async function demoGetRunDataset(runId: string): Promise<Dataset | null> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  if (!record.datasetId) return null;
  const dataset = DEMO_DATASETS[record.datasetId];
  return dataset ?? null;
}

/** Register an uploaded file as a synthetic demo dataset (upload parity). */
export async function demoUploadDataset(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DatasetUploadResult> {
  const name = file.name || "uploaded.csv";
  const format = /\.(xlsx?)$/i.test(name) ? "excel" : "csv";
  const fileSizeBytes = file.size;
  const columns = 8;
  const rows = format === "excel" ? 0 : Math.max(1, Math.min(100_000, Math.floor(file.size / 64)));
  for (const pct of [12, 34, 57, 78, 100]) {
    await wait(70);
    onProgress?.(pct);
  }
  const routing = await demoRecommendEngine({ bytes: fileSizeBytes, rows, cols: columns });
  const id = `ds_${hexId(8)}`;
  const summary: DatasetSummary = {
    id,
    name,
    path: `uploads/${name}`,
    format,
    sizeBytes: fileSizeBytes,
    rows,
    columns,
    engine: routing.engine,
    engineReason: routing.reason,
    validationPassed: true,
    missingCells: 0,
    duplicateRows: 0,
    targetColumn: null,
    taskType: null,
    registeredAt: new Date().toISOString(),
    lastUsedRunId: null,
    sample: false,
  };
  const dataset = registerDemoDataset(summary);
  return {
    dataset,
    warnings: [
      `Demo mode: '${name}' (${fileSizeBytes.toLocaleString()} bytes) was registered with a simulated profile.`,
    ],
  };
}

/** Remove a dataset from the demo store (delete parity). */
export async function demoDeleteDataset(id: string): Promise<{ deleted: boolean; id?: string }> {
  await wait(LATENCY_MS);
  if (!removeDemoDataset(id)) {
    throw new ApiError(`Dataset '${id}' was not found`, "NotFound", 404);
  }
  return { deleted: true, id };
}

/** Engine heuristic from the backend `recommend_engine` (pandas <2MB, polars ≤500MB, spark). */
export async function demoRecommendEngine(input: {
  bytes: number;
  rows?: number;
  cols?: number;
}): Promise<EngineRecommendation> {
  await wait(70);
  const bytes = input.bytes;
  return {
    engine: engineFromBytes(bytes),
    reason: engineReason(bytes),
    routing: {
      n_rows: input.rows ?? 0,
      n_cols: input.cols ?? 0,
      memory_bytes: bytes,
      pandas_max_bytes: PANDAS_MAX_BYTES,
    },
  };
}

/* ------------------------------------------------------------------ */
/* Runs                                                               */
/* ------------------------------------------------------------------ */

export async function demoListRuns(query: ListQuery = {}): Promise<Page<RunSummary>> {
  await wait(LATENCY_MS);
  let items = allRecords().map((r) => r.run.summary);
  if (query.status) items = items.filter((r) => r.status === query.status);
  if (query.taskType) items = items.filter((r) => r.taskType === query.taskType);
  if (query.search) {
    const q = query.search.toLowerCase();
    items = items.filter(
      (r) => r.datasetName.toLowerCase().includes(q) || r.id.toLowerCase().includes(q),
    );
  }
  if (query.dateFrom) {
    const from = Date.parse(query.dateFrom);
    items = items.filter((r) => Date.parse(r.createdAt) >= from);
  }
  if (query.dateTo) {
    const to = Date.parse(query.dateTo);
    items = items.filter((r) => Date.parse(r.createdAt) <= to);
  }
  if (query.sort) items = sortBy(items, query.sort as keyof RunSummary, query.order ?? "desc");
  else items = sortBy(items, "createdAt", "desc");
  return paginate(items, query);
}

export async function demoGetRun(runId: string): Promise<Run> {
  await wait(LATENCY_MS);
  return requireRecord(runId).run;
}

export async function demoGetRunLogs(runId: string): Promise<string[]> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  const stageLines = record.stages.filter((s) => s.logs.length).flatMap((s) => s.logs);
  return [...record.logs, ...stageLines];
}

export async function demoCreateRun(request: SyntheticRunInput): Promise<Run> {
  await wait(LATENCY_MS + 60);
  return createDemoRun(request);
}

export async function demoCancelRun(runId: string): Promise<Run> {
  await wait(LATENCY_MS);
  const result = cancelDemoRun(runId);
  if (!result.ok) return raiseLifecycleError(result, "RunNotActive");
  return result.record.run;
}

export async function demoRestoreRun(runId: string): Promise<Run> {
  await wait(LATENCY_MS);
  const result = restoreDemoRun(runId);
  if (!result.ok) return raiseLifecycleError(result, "RunNotActive");
  return result.record.run;
}

export async function demoDeleteRun(runId: string): Promise<{ deleted: boolean; id?: string }> {
  await wait(LATENCY_MS);
  const result = deleteDemoRun(runId);
  if (!result.ok) return raiseLifecycleError(result, "NotFound");
  return { deleted: true, id: result.record.run.id };
}

function raiseLifecycleError(
  result: { ok: false; reason: "not-found" | "not-active"; message: string },
  activeCode: "RunNotActive" | "NotFound",
): never {
  const code = result.reason === "not-found" ? "NotFound" : activeCode;
  const status = result.reason === "not-found" ? 404 : 409;
  throw new ApiError(result.message, code, status);
}

export async function demoDashboardStats(): Promise<DashboardStats> {
  await wait(LATENCY_MS);
  const records = allRecords();
  const completed = records.filter((r) => r.run.summary.status === "completed");
  const scores = completed
    .map((r) => r.run.summary.bestScore)
    .filter((s): s is number => s != null);
  const engineBreakdown: DashboardStats["engineBreakdown"] = { pandas: 0, polars: 0, spark: 0 };
  const taskBreakdown: DashboardStats["taskBreakdown"] = {
    classification: 0,
    regression: 0,
    clustering: 0,
    anomaly_detection: 0,
    ambiguous: 0,
    analytics: 0,
    unknown: 0,
  };
  for (const r of records) {
    engineBreakdown[r.run.summary.engine] += 1;
    taskBreakdown[r.run.summary.taskType] += 1;
  }
  return {
    totalRuns: records.length,
    activeRuns: records.filter(
      (r) => r.run.summary.status === "running" || r.run.summary.status === "queued",
    ).length,
    completedRuns: completed.length,
    failedRuns: records.filter((r) => r.run.summary.status === "failed").length,
    totalDatasets: DATASET_SEEDS.length,
    totalModels: completed.reduce((acc, r) => acc + r.models.length, 0),
    avgBestScore: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
    totalArtifacts: records.reduce((acc, r) => acc + r.artifacts.artifactCount, 0),
    engineBreakdown,
    taskBreakdown,
  };
}

export async function demoRecentRuns(): Promise<RecentRunActivity[]> {
  await wait(LATENCY_MS);
  return allRecords()
    .slice(0, 8)
    .map((r) => {
      const s = r.run.summary;
      return {
        id: s.id,
        datasetName: s.datasetName,
        status: s.status,
        taskType: s.taskType,
        bestModelType: s.bestModelType,
        bestScore: s.bestScore,
        createdAt: s.createdAt,
        durationMs: s.durationMs,
      };
    });
}

/* ------------------------------------------------------------------ */
/* Pipeline                                                           */
/* ------------------------------------------------------------------ */

export async function demoPipelineOverview(runId: string): Promise<PipelineOverview> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  return {
    runId,
    mode: record.run.summary.mode,
    stagesRequested: record.run.stagesRequested,
    stagesExecuted: record.stages
      .filter((s) => s.status === "completed" || s.status === "warning")
      .map((s) => s.id) as PipelineOverview["stagesExecuted"],
    totalDurationMs: record.run.summary.durationMs ?? 0,
  };
}

export async function demoPipelineStages(runId: string): Promise<StageDetail[]> {
  await wait(LATENCY_MS);
  return requireRecord(runId).stages;
}

export async function demoPipelineProgress(runId: string): Promise<PipelineProgress> {
  await wait(LATENCY_MS / 2);
  const record = requireRecord(runId);
  const completed = record.stages
    .filter((s) => s.status === "completed" || s.status === "warning")
    .map((s) => s.id) as PipelineProgress["completedStages"];
  const current = record.stages.find((s) => s.status === "running");
  return {
    runId,
    status: record.run.summary.status,
    completedStages: completed,
    currentStage: (current?.id ?? null) as PipelineProgress["currentStage"],
    currentStagesCompleted: completed.length,
    totalStages: record.run.stagesRequested.length,
    messages: record.run.error ? [record.run.error.message] : [],
  };
}

/* ------------------------------------------------------------------ */
/* Models                                                             */
/* ------------------------------------------------------------------ */

export async function demoListModels(runId: string): Promise<ModelRankingRow[]> {
  await wait(LATENCY_MS);
  return requireRecord(runId).models;
}

export async function demoGetModelDetail(runId: string, modelType: string): Promise<ModelDetail> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  const row = record.models.find((m) => m.model_type === modelType);
  if (!row)
    throw new ApiError(`Model '${modelType}' was not found in run '${runId}'`, "NotFound", 404);
  const target = record.run.summary.targetColumn;
  return {
    model_type: row.model_type,
    model_class: bestPoolName(row.model_type),
    best_params: row.model_type.includes("kmeans")
      ? { n_clusters: 4, init: "k-means++", n_init: 10, random_state: 42 }
      : row.model_type.includes("forest")
        ? { n_estimators: 200, max_depth: 16, min_samples_split: 4, random_state: 42 }
        : { solver: "lbfgs", C: 1.0, max_iter: 1000 },
    score: row.primary_score,
    trials_used: row.trials_used,
    time_elapsed: row.time_elapsed,
    truncated: row.truncated,
    estimated_training_cost: row.estimated_training_cost,
    taskType: record.run.summary.taskType,
    targetColumn: target,
    nFeatures: record.featureCount,
    nSamples: record.run.sampling?.sample_rows ?? record.run.summary.rows,
    evaluation: record.evaluation,
    rank: row.rank,
    best: row.best,
  };
}

/* ------------------------------------------------------------------ */
/* Explainability                                                     */
/* ------------------------------------------------------------------ */

export async function demoExplainability(runId: string): Promise<ExplainabilityView | null> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  if (!record.explanation) {
    if (record.run.summary.taskType === "clustering") {
      throw new ApiError(
        "Explainability is not available for clustering runs (explainability + storage stages are excluded from the clustering pipeline).",
        "ExplainabilityUnavailable",
        null,
      );
    }
    throw new ApiError(
      "Explainability has not been computed yet for this run.",
      "ExplainabilityPending",
      null,
    );
  }
  return record.explanation;
}

/* ------------------------------------------------------------------ */
/* Reports                                                            */
/* ------------------------------------------------------------------ */

export async function demoReport(runId: string, format: ReportInfo["format"]): Promise<ReportInfo> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  const markdown = record.reportMarkdown;
  const lines = markdown.split("\n");
  const sections = lines.filter((l) => l.startsWith("## ")).map((l) => l.replace(/^##\s+/, ""));

  const s = record.run.summary;
  const pipelineJson = {
    run: {
      id: s.id,
      dataset_name: s.datasetName,
      status: s.status,
      engine: s.engine,
      mode: s.mode,
      created_at: s.createdAt,
      duration_ms: s.durationMs,
    },
    dataset: {
      path: s.datasetPath,
      rows: s.rows,
      columns: s.columns,
      file_size_bytes: s.fileSizeBytes,
    },
    target: {
      column: s.targetColumn,
      task_type: s.taskType,
      candidates: record.targetCandidates,
    },
    model: {
      best_model_type: s.bestModelType,
      best_score: s.bestScore,
      primary_metric: s.primaryMetric,
      trial_count: s.trialCount ?? 0,
      truncated: s.hpoTruncated ?? false,
      leaderboard: record.models.map((m) => ({
        rank: m.rank,
        model_type: m.model_type,
        primary_score: m.primary_score,
        trials_used: m.trials_used,
        time_elapsed: m.time_elapsed,
        cost: m.estimated_training_cost,
        best: m.best,
      })),
    },
    metrics: record.evaluation?.metrics ?? {},
    explanation: record.explanation?.report ?? null,
    warnings: record.run.warnings,
    errors: record.run.error ? [record.run.error.message] : [],
    narrative: markdown,
  };

  return {
    runId,
    format,
    title: `Phronesis Pipeline Report — ${record.run.summary.datasetName}`,
    created: record.run.summary.updatedAt,
    reportLength: markdown.length,
    reportLines: lines.length,
    markdown,
    sections,
    html: demoReportHtml(record.run.summary, markdown),
    json: JSON.stringify(pipelineJson, null, 2),
  };
}

/** Minimal self-contained HTML rendering of the generated markdown report. */
function demoReportHtml(s: RunSummary, markdown: string): string {
  const esc = (t: string) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const body: string[] = [
    `<p class="meta">${esc(s.datasetName)} · ${esc(s.id)} · ${esc(s.status)}</p>`,
  ];
  let inTable = false;
  let inList = false;
  const closeTable = () => {
    if (inTable) {
      body.push("</table>");
      inTable = false;
    }
  };
  const closeList = () => {
    if (inList) {
      body.push("</ul>");
      inList = false;
    }
  };
  for (const raw of markdown.split("\n")) {
    const line = raw.trim();
    if (!line) {
      closeTable();
      closeList();
      continue;
    }
    if (line.startsWith("### ")) {
      closeTable();
      closeList();
      body.push(`<h3>${esc(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      closeTable();
      closeList();
      body.push(`<h2>${esc(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      closeTable();
      closeList();
      body.push(`<h1>${esc(line.slice(2))}</h1>`);
    } else if (line.startsWith("|")) {
      closeList();
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      if (cells.every((c) => /^-+$/.test(c))) continue;
      if (!inTable) {
        body.push("<table>");
        inTable = true;
      }
      body.push(`<tr>${cells.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`);
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      closeTable();
      if (!inList) {
        body.push("<ul>");
        inList = true;
      }
      body.push(`<li>${esc(line.slice(2))}</li>`);
    } else if (line.startsWith("> ")) {
      closeTable();
      closeList();
      body.push(`<blockquote>${esc(line.slice(2))}</blockquote>`);
    } else {
      closeTable();
      closeList();
      body.push(`<p>${esc(line)}</p>`);
    }
  }
  closeTable();
  closeList();
  const style = `
    :root { color-scheme: light dark; }
    body { font-family: system-ui, sans-serif; line-height: 1.6; margin: 0 auto; max-width: 820px; padding: 2rem; }
    h1 { font-size: 1.25rem; } h2 { font-size: 1.05rem; margin-top: 1.5rem; }
    h3 { font-size: 0.95rem; } .meta { color: #6b7280; font-size: 0.8rem; }
    table { border-collapse: collapse; width: 100%; font-family: ui-monospace, monospace; font-size: 0.8rem; }
    td, th { border: 1px solid rgba(128,128,128,.3); padding: 4px 8px; text-align: left; }
    blockquote { border-left: 3px solid rgba(128,128,128,.4); margin-left: 0; padding-left: 0.75rem; color: #6b7280; }
    code { font-family: ui-monospace, monospace; }
  `;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"/><title>${esc(s.datasetName)} — report</title><style>${style}</style></head><body>${body.join("\n")}</body></html>`;
}

/* ------------------------------------------------------------------ */
/* Artifact content                                                   */
/* ------------------------------------------------------------------ */

function artifactContent(
  artifact: Artifact,
  content: string | null,
  note?: string,
): ArtifactContent {
  return {
    name: artifact.name,
    kind: artifact.kind,
    format: artifact.format,
    sizeBytes: artifact.sizeBytes,
    content,
    note,
  };
}

function artifactJson(artifact: Artifact, data: unknown): ArtifactContent {
  return artifactContent(artifact, JSON.stringify(data, null, 2));
}

export async function demoArtifactContent(runId: string, name: string): Promise<ArtifactContent> {
  await wait(LATENCY_MS);
  const record = requireRecord(runId);
  const artifact = record.artifacts.artifacts.find((a) => a.name === name);
  if (!artifact)
    throw new ApiError(`Artifact '${name}' not found in run '${runId}'`, "NotFound", 404);
  if (artifact.status === "unavailable") {
    return artifactContent(artifact, null, artifact.reason ?? "Not persisted for this run.");
  }

  const s = record.run.summary;
  const ds = record.datasetId ? DEMO_DATASETS[record.datasetId] : null;

  switch (name) {
    case "config.json":
      return artifactJson(artifact, {
        ...record.run.request,
        datasetId: record.datasetId,
        targetOverride: s.targetColumn,
        taskOverride: s.taskType,
      });
    case "run_metadata.json":
      return artifactJson(artifact, {
        id: s.id,
        status: s.status,
        datasetName: s.datasetName,
        datasetPath: s.datasetPath,
        fileFormat: s.fileFormat,
        rows: s.rows,
        columns: s.columns,
        engine: s.engine,
        taskType: s.taskType,
        targetColumn: s.targetColumn,
        mode: s.mode,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        durationMs: s.durationMs,
        sampling: record.run.sampling,
        resourceReport: record.run.resourceReport,
      });
    case "engine_selection.json":
      return artifactJson(artifact, {
        engine: s.engine,
        reason: s.engineReason,
        requestMode: record.run.request.engine,
        routing: { n_rows: s.rows, n_cols: s.columns, memory_bytes: s.fileSizeBytes },
      });
    case "target_detection.json":
      return artifactJson(artifact, {
        target: s.targetColumn,
        task: s.taskType,
        confidence: record.targetCandidates[0]?.confidence ?? null,
        candidates: record.targetCandidates,
      });
    case "validation.json":
      return artifactJson(artifact, {
        shape: { rows: s.rows, columns: s.columns },
        passed: true,
        duplicate_rows: 0,
        null_columns: 0,
        columns_checked: ds?.profile.column_names ?? [],
      });
    case "eda.json":
      return artifactJson(artifact, {
        shape: { rows: s.rows, columns: s.columns },
        column_names: ds?.profile.column_names ?? [],
        dtypes: ds?.profile.dtypes ?? {},
        numeric_columns: ds?.profile.numeric_columns ?? [],
        categorical_columns: ds?.profile.categorical_columns ?? [],
        memory_bytes: ds?.profile.memory_bytes ?? s.fileSizeBytes,
      });
    case "feature_metadata.json":
      return artifactJson(artifact, {
        n_features: record.featureCount,
        feature_names: (ds?.profile.column_names ?? []).slice(0, record.featureCount),
        transformer: "make_pipeline",
        encoding: s.targetColumn ? { target_encoded: 0 } : {},
      });
    case "resource_estimation.json":
      return artifactJson(artifact, record.run.resourceReport ?? {});
    case "pipeline.json":
      return artifactJson(artifact, {
        run: s,
        stagesRequested: record.run.stagesRequested,
        stagesExecuted: record.run.stagesExecuted,
        evaluation: record.evaluation,
        explanation: record.explanation?.report ?? null,
      });
    case "metrics.json":
      return artifactJson(artifact, record.evaluation?.metrics ?? {});
    case "evaluation.json":
      return artifactJson(artifact, record.evaluation ?? {});
    case "model.json":
    case "training.json":
      return artifactJson(artifact, {
        best_model_type: s.bestModelType,
        best_score: s.bestScore,
        primary_metric: s.primaryMetric,
        trial_count: s.trialCount ?? 0,
        hpo_truncated: s.hpoTruncated ?? false,
        model_info: record.evaluation?.model_info ?? {},
        leaderboard: record.models,
      });
    case "shap.json":
      return artifactJson(artifact, record.explanation?.report ?? { feature_importance: {} });
    case "report.md":
      return artifactContent(artifact, record.reportMarkdown);
    case "report.html":
      return artifactContent(artifact, demoReportHtml(s, record.reportMarkdown));
    case "logs.txt":
      return artifactContent(artifact, (await demoGetRunLogs(runId)).join("\n"));
    case "model.joblib":
      return artifactContent(
        artifact,
        null,
        "Serialized trained model binary. Download and restore with joblib.load().",
      );
    default:
      return artifactJson(artifact, {
        name,
        runId,
        description: artifact.description,
        status: artifact.status,
      });
  }
}

export async function demoArtifacts(runId: string): Promise<ArtifactManifest> {
  await wait(LATENCY_MS);
  return requireRecord(runId).artifacts;
}
