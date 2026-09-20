/**
 * Explainability types.
 * 1:1 with backend `explanation_report` (`ml/explainability/service.py`).
 */

export type ExplainerType =
  | "TreeExplainer"
  | "LinearExplainer"
  | "PermutationExplainer"
  | "KernelExplainer"
  | "none";

export interface FeatureImportanceItem {
  feature: string;
  value: number;
}

/** `explanation_report` from the explainability agent (stored in shap.json). */
export interface ExplanationReport {
  feature_importance: Record<string, number>;
  explainer_type: ExplainerType;
  sampled: boolean;
  n_samples_used: number;
  n_features_used: number;
  max_samples: number;
}

/** Normalized, client-generated beeswarm point (demo render only). */
export interface ShapPoint {
  feature: string;
  shapValue: number;
  featureValue: number;
}

/** Per-row attribution breakdown (demo render only — real backend serves per-request). */
export interface ExplanationSample {
  sampleId: number;
  baseValue: number;
  prediction: number;
  predictionLabel?: string;
  importance: FeatureImportanceItem[];
  beeswarm: ShapPoint[];
}

/** Derived explainability view model. */
export interface ExplainabilityView {
  report: ExplanationReport;
  importance: FeatureImportanceItem[];
  beeswarm: ShapPoint[];
  baseValue: number;
  prediction: number;
  predictionLabel?: string;
  sampleId: number;
  /** Per-sample breakdowns for the sample stepper. */
  samples?: ExplanationSample[];
}