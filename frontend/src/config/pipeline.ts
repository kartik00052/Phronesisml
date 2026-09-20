import type { PipelineStageId } from "@/types/pipeline";

/**
 * Canonical pipeline stage metadata.
 * Order and ids are 1:1 with `phronesisml._stages._FULL_PIPELINE_STAGES`.
 */
export const PIPELINE_STAGE_ORDER: PipelineStageId[] = [
  "upload",
  "etl",
  "validation",
  "eda",
  "target_detection",
  "feature_engineering",
  "model_selection",
  "evaluation",
  "explainability",
  "reporting",
  "storage",
];

export interface StageMeta {
  id: PipelineStageId;
  label: string;
  shortLabel: string;
  description: string;
  /** Stage slices from the backend — which public function runs up to here. */
  publicApi: string;
  phase: "data" | "insight" | "model" | "delivery";
}

export const STAGE_META: Record<PipelineStageId, StageMeta> = {
  upload: {
    id: "upload",
    label: "Upload",
    shortLabel: "Upload",
    description: "Load and detect the source dataset.",
    publicApi: "clean()",
    phase: "data",
  },
  etl: {
    id: "etl",
    label: "ETL",
    shortLabel: "ETL",
    description: "Clean raw data — nulls, types, categorical encoding.",
    publicApi: "clean()",
    phase: "data",
  },
  validation: {
    id: "validation",
    label: "Validation",
    shortLabel: "Validate",
    description: "Schema & data-quality checks on the processed frame.",
    publicApi: "validate()",
    phase: "data",
  },
  eda: {
    id: "eda",
    label: "EDA",
    shortLabel: "EDA",
    description: "Statistical profiling of the dataset.",
    publicApi: "analyze()",
    phase: "insight",
  },
  target_detection: {
    id: "target_detection",
    label: "Target Detection",
    shortLabel: "Target",
    description: "Detect target column and machine-learning task.",
    publicApi: "detect_target()",
    phase: "insight",
  },
  feature_engineering: {
    id: "feature_engineering",
    label: "Feature Engineering",
    shortLabel: "Features",
    description: "Build features and a reproducible transform recipe.",
    publicApi: "engineer()",
    phase: "insight",
  },
  model_selection: {
    id: "model_selection",
    label: "Model Selection",
    shortLabel: "Model Select",
    description: "AutoML search + hyperparameter optimization.",
    publicApi: "select_model()",
    phase: "model",
  },
  evaluation: {
    id: "evaluation",
    label: "Evaluation",
    shortLabel: "Evaluate",
    description: "Compute task-aware evaluation metrics.",
    publicApi: "evaluate()",
    phase: "model",
  },
  explainability: {
    id: "explainability",
    label: "Explainability",
    shortLabel: "Explain",
    description: "SHAP-based feature importance explanations.",
    publicApi: "explain()",
    phase: "model",
  },
  reporting: {
    id: "reporting",
    label: "Reporting",
    shortLabel: "Report",
    description: "Generate the Markdown/HTML pipeline report.",
    publicApi: "report()",
    phase: "delivery",
  },
  storage: {
    id: "storage",
    label: "Storage",
    shortLabel: "Store",
    description: "Persist the artifact suite.",
    publicApi: "train()",
    phase: "delivery",
  },
};

/** Stage slices (public API entry points) the wizard exposes. */
export interface StageSliceMeta {
  key: string;
  label: string;
  stages: PipelineStageId[];
  api: string;
}

export const STAGE_SLICES: StageSliceMeta[] = [
  { key: "clean", label: "Clean", stages: PIPELINE_STAGE_ORDER.slice(0, 2), api: "clean()" },
  {
    key: "validate",
    label: "Validate",
    stages: PIPELINE_STAGE_ORDER.slice(0, 3),
    api: "validate()",
  },
  {
    key: "analyze",
    label: "Analyze",
    stages: PIPELINE_STAGE_ORDER.slice(0, 4),
    api: "analyze()",
  },
  {
    key: "detect_target",
    label: "Target detection",
    stages: PIPELINE_STAGE_ORDER.slice(0, 5),
    api: "detect_target()",
  },
  {
    key: "engineer",
    label: "Feature engineering",
    stages: PIPELINE_STAGE_ORDER.slice(0, 6),
    api: "engineer()",
  },
  {
    key: "select_model",
    label: "Model selection",
    stages: PIPELINE_STAGE_ORDER.slice(0, 8),
    api: "select_model()",
  },
  {
    key: "explain",
    label: "Explain",
    stages: PIPELINE_STAGE_ORDER.slice(0, 9),
    api: "explain()",
  },
  {
    key: "report",
    label: "Report",
    stages: PIPELINE_STAGE_ORDER.slice(0, 10),
    api: "report()",
  },
  {
    key: "train",
    label: "Full pipeline",
    stages: PIPELINE_STAGE_ORDER,
    api: "train()",
  },
];

export const DEFAULT_RUN_STAGES: PipelineStageId[] = PIPELINE_STAGE_ORDER;