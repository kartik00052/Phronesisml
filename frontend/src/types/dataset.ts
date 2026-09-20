/**
 * Dataset types.
 * 1:1 with backend profile/validation/ETL outputs:
 * `results.DatasetProfile`, `ml.profilers.stats.profile_dataset`,
 * `data/validators/checks.py` validation_report, ETL `transform_log`.
 */

export interface Shape {
  rows: number;
  columns: number;
}

export interface NumericColumnSummary {
  count: number;
  mean: number;
  std: number;
  min: number;
  "25%": number;
  "50%": number;
  "75%": number;
  max: number;
  null_count: number;
}

export interface CategoricalColumnSummary {
  cardinality: number;
  null_count: number;
  top_values: Record<string, number>;
}

/** The `data_profile` dict produced by the EDA agent. */
export interface DataProfile {
  shape: Shape;
  column_names: string[];
  dtypes: Record<string, string>;
  numeric_columns: string[];
  categorical_columns: string[];
  numeric_summary: Record<string, NumericColumnSummary>;
  categorical_summary: Record<string, CategoricalColumnSummary>;
  memory_bytes: number;
}

/** Column-level row used in the Schema tab / dataset preview. */
export interface ColumnInfo {
  name: string;
  dtype: string;
  numeric: boolean;
  categorical: boolean;
  nullCount: number;
  nullPercent: number;
  cardinality?: number;
  stats?: NumericColumnSummary;
  topValues?: Record<string, number>;
}

/** Validation report (`validation_report` from the backend). */
export interface ValidationReport {
  shape: Shape;
  dtypes: Record<string, string>;
  column_names: string[];
  null_counts: Record<string, number>;
  null_columns: string[];
  empty_columns: string[];
  duplicate_rows: number;
  passed: boolean;
}

/** ETL transform log entry (`transform_log`). */
export interface TransformEntry {
  action: string;
  [key: string]: unknown;
}

/** Row-level preview for a dataset. */
export interface DatasetPreview {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  maxRows: number;
}

/** Upload-metadata summary for a dataset (sheet list for Excel). */
export interface SheetInfo {
  name: string;
  index: number;
  rows: number;
  cols: number;
}

/** Dataset list row. */
export interface DatasetSummary {
  id: string;
  name: string;
  path: string;
  format: string;
  sizeBytes: number;
  rows: number;
  columns: number;
  engine: string;
  engineReason: string;
  validationPassed: boolean;
  missingCells: number;
  duplicateRows: number;
  targetColumn: string | null;
  taskType: string | null;
  registeredAt: string;
  lastUsedRunId: string | null;
  /** True for bundled sample datasets offered in the workspace (e.g. Iris). */
  sample?: boolean;
}

/** Full dataset detail for the dataset workspace. */
export interface Dataset {
  summary: DatasetSummary;
  profile: DataProfile;
  columns: ColumnInfo[];
  validation: ValidationReport;
  transformLog: TransformEntry[];
  preview: DatasetPreview;
  sheets: SheetInfo[];
}

/** Upload response envelope — wraps the created dataset. */
export interface DatasetUploadResult {
  dataset: Dataset;
  warnings?: string[];
}

/** Engine recommendation heuristic (backend `recommend_engine`). */
export interface EngineRecommendation {
  engine: string;
  reason: string;
  routing: {
    n_rows: number;
    n_cols: number;
    memory_bytes: number;
    pandas_max_bytes: number;
  };
}
