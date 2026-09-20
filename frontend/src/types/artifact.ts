/**
 * Artifact types.
 * 1:1 with the backend storage agent's 18-file artifact set
 * (`services/storage.py::save_artifacts`).
 */

export type ArtifactKind =
  | "model"
  | "report"
  | "metrics"
  | "training"
  | "evaluation"
  | "shap"
  | "config"
  | "feature_metadata"
  | "target_detection"
  | "eda"
  | "validation"
  | "resource_estimation"
  | "engine_selection"
  | "pipeline"
  | "run_metadata"
  | "logs"
  | "model_binary";

export type ArtifactFormat = "json" | "md" | "html" | "txt" | "joblib" | "csv";

export interface Artifact {
  name: string;
  kind: ArtifactKind;
  format: ArtifactFormat;
  sizeBytes: number;
  status: "available" | "unavailable";
  reason?: string;
  description: string;
  url?: string;
}

/** Artifact manifest for a run (`build_artifact_manifest`). */
export interface ArtifactManifest {
  runId: string;
  artifactCount: number;
  totalBytes: number;
  artifacts: Artifact[];
}

/** Dereferenced artifact content for preview/download. */
export interface ArtifactContent {
  name: string;
  kind: ArtifactKind;
  format: ArtifactFormat;
  sizeBytes: number;
  /** Text payload for json/txt/md/html; null for binary-only artifacts. */
  content: string | null;
  /** Presentational note for binary artifacts (e.g. model.joblib). */
  note?: string;
  /** True when the payload was clipped for shipping over the wire. */
  truncated?: boolean;
}

/** Saved-run info returned by `save()`/`restore()`. */
export interface SavedRunInfo {
  runId: string;
  artifactUri: string;
  savedFiles: string[];
  warnings: string[];
}