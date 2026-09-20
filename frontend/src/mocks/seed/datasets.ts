import type {
  CategoricalColumnSummary,
  ColumnInfo,
  DataProfile,
  Dataset,
  DatasetPreview,
  DatasetSummary,
  NumericColumnSummary,
  TransformEntry,
  ValidationReport,
} from "@/types/dataset";
import { createRng } from "@/mocks";
import { engineReason } from "@/config/engine-limits";

/** Compact column definition used to author demo datasets. */
export interface ColDef {
  name: string;
  dtype: string;
  numeric: boolean;
  nullCount: number;
  cardinality?: number;
  mean?: number;
  std?: number;
  min?: number;
  q1?: number;
  median?: number;
  q3?: number;
  max?: number;
  top?: [string, number][];
}

export interface DatasetSeed {
  summary: DatasetSummary;
  columns: ColDef[];
  validationAssertions?: {
    nullColumns?: string[];
    emptyColumns?: string[];
    duplicateRows?: number;
    passed?: boolean;
    issues?: string[];
  };
  transformLog?: TransformEntry[];
}

function numericSummary(c: ColDef): NumericColumnSummary {
  return {
    count: 0,
    mean: c.mean ?? 0,
    std: c.std ?? 0,
    min: c.min ?? 0,
    "25%": c.q1 ?? c.min ?? 0,
    "50%": c.median ?? c.mean ?? 0,
    "75%": c.q3 ?? c.max ?? 0,
    max: c.max ?? 0,
    null_count: c.nullCount,
  };
}

function categoricalSummary(c: ColDef): CategoricalColumnSummary {
  return {
    cardinality: c.cardinality ?? c.top?.length ?? 0,
    null_count: c.nullCount,
    top_values: Object.fromEntries(c.top ?? []),
  };
}

/** Build a full Dataset view-model from a compact seed. */
export function buildDataset(seed: DatasetSeed): Dataset {
  const { summary } = seed;
  const totalCells = summary.rows * summary.columns;

  const numeric = seed.columns.filter((c) => c.numeric);
  const categorical = seed.columns.filter((c) => !c.numeric);

  const numericSummaryMap: Record<string, NumericColumnSummary> = {};
  for (const c of numeric) {
    const s = numericSummary(c);
    s.count = summary.rows - c.nullCount;
    numericSummaryMap[c.name] = s;
  }

  const categoricalSummaryMap: Record<string, CategoricalColumnSummary> = {};
  for (const c of categorical) {
    const s = categoricalSummary(c);
    if (s.cardinality === 0)
      s.cardinality = Math.min(summary.rows, Math.max(2, c.name.length * 3 + 2));
    categoricalSummaryMap[c.name] = s;
  }

  const duplicateRows = seed.validationAssertions?.duplicateRows ?? 0;

  const profile: DataProfile = {
    shape: { rows: summary.rows, columns: summary.columns },
    column_names: seed.columns.map((c) => c.name),
    dtypes: Object.fromEntries(seed.columns.map((c) => [c.name, c.dtype])),
    numeric_columns: numeric.map((c) => c.name),
    categorical_columns: categorical.map((c) => c.name),
    numeric_summary: numericSummaryMap,
    categorical_summary: categoricalSummaryMap,
    memory_bytes: Math.round(totalCells * 8 * 1.25),
  };

  const columns: ColumnInfo[] = seed.columns.map((c) => {
    const base = {
      name: c.name,
      dtype: c.dtype,
      numeric: c.numeric,
      categorical: !c.numeric,
      nullCount: c.nullCount,
      nullPercent: c.nullCount / Math.max(1, summary.rows),
    };
    if (c.numeric) return { ...base, stats: numericSummaryMap[c.name] };
    return {
      ...base,
      cardinality: c.cardinality ?? c.top?.length ?? 0,
      topValues: categoricalSummaryMap[c.name].top_values,
    };
  });

  const nullColumns =
    seed.validationAssertions?.nullColumns ??
    seed.columns.filter((c) => c.nullCount > 0).map((c) => c.name);

  const validation: ValidationReport = {
    shape: { rows: summary.rows, columns: summary.columns },
    dtypes: profile.dtypes,
    column_names: profile.column_names,
    null_counts: Object.fromEntries(seed.columns.map((c) => [c.name, c.nullCount])),
    null_columns: nullColumns,
    empty_columns: seed.validationAssertions?.emptyColumns ?? [],
    duplicate_rows: duplicateRows,
    passed: seed.validationAssertions?.passed ?? true,
  };

  const transformLog: TransformEntry[] = seed.transformLog ?? [
    { action: "handle_nulls", strategy: "drop", columns_affected: 0 },
    { action: "encode_categoricals", strategy: "label", columns_encoded: 0 },
  ];

  const preview = makePreview(seed);

  return {
    summary,
    profile,
    columns,
    validation,
    transformLog,
    preview,
    sheets:
      summary.format === "excel"
        ? [{ name: "Sheet1", index: 0, rows: summary.rows, cols: summary.columns }]
        : [],
  };
}

/** Deterministic preview rows derived from column definitions. */
function makePreview(seed: DatasetSeed): DatasetPreview {
  const rng = createRng(seed.summary.rows * 7 + seed.summary.columns);
  const columns = seed.columns.map((c) => c.name);
  const rows: (string | number | boolean | null)[][] = [];
  const limit = Math.min(8, seed.summary.rows);
  for (let i = 0; i < limit; i++) {
    const row: (string | number | boolean | null)[] = seed.columns.map((c) => {
      if (c.nullCount > 0 && rng() < c.nullCount / Math.max(1, seed.summary.rows)) return null;
      if (!c.numeric) {
        const top = c.top ?? [];
        if (top.length === 0) return `value_${Math.floor(rng() * 6)}`;
        return top[Math.floor(rng() * top.length)][0];
      }
      const mean = c.mean ?? 0;
      const std = c.std ?? Math.max(1, Math.abs(mean) * 0.4);
      const val = mean + (rng() + rng() - 1) * std * 1.5;
      const isInt = /int/i.test(c.dtype);
      return isInt ? Math.round(val) : Number(val.toFixed(2));
    });
    rows.push(row);
  }
  return { columns, rows, maxRows: limit };
}

/* ------------------------------------------------------------------ */
/* Demo datasets                                                      */
/* ------------------------------------------------------------------ */

const CHURN_COLUMNS: ColDef[] = [
  { name: "customerID", dtype: "object", numeric: false, nullCount: 0, cardinality: 7043 },
  {
    name: "gender",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["Male", 3555],
      ["Female", 3488],
    ],
  },
  {
    name: "SeniorCitizen",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 0.162,
    std: 0.369,
    min: 0,
    q1: 0,
    median: 0,
    q3: 0,
    max: 1,
  },
  {
    name: "Partner",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["No", 3641],
      ["Yes", 3402],
    ],
  },
  {
    name: "Dependents",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["No", 4933],
      ["Yes", 2110],
    ],
  },
  {
    name: "tenure",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 32.37,
    std: 24.56,
    min: 0,
    q1: 9,
    median: 29,
    q3: 55,
    max: 72,
  },
  {
    name: "PhoneService",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["Yes", 6361],
      ["No", 682],
    ],
  },
  {
    name: "MultipleLines",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 3390],
      ["Yes", 2971],
      ["No phone service", 682],
    ],
  },
  {
    name: "InternetService",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["Fiber optic", 3096],
      ["DSL", 2421],
      ["No", 1526],
    ],
  },
  {
    name: "OnlineSecurity",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 3498],
      ["Yes", 2019],
      ["No internet service", 1526],
    ],
  },
  {
    name: "OnlineBackup",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 3088],
      ["Yes", 2429],
      ["No internet service", 1526],
    ],
  },
  {
    name: "DeviceProtection",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 3095],
      ["Yes", 2422],
      ["No internet service", 1526],
    ],
  },
  {
    name: "TechSupport",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 3473],
      ["Yes", 2044],
      ["No internet service", 1526],
    ],
  },
  {
    name: "StreamingTV",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 2810],
      ["Yes", 2707],
      ["No internet service", 1526],
    ],
  },
  {
    name: "StreamingMovies",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["No", 2779],
      ["Yes", 2738],
      ["No internet service", 1526],
    ],
  },
  {
    name: "Contract",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["Month-to-month", 3875],
      ["Two year", 1695],
      ["One year", 1473],
    ],
  },
  {
    name: "PaperlessBilling",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["Yes", 4171],
      ["No", 2872],
    ],
  },
  {
    name: "PaymentMethod",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 4,
    top: [
      ["Electronic check", 2365],
      ["Mailed check", 1612],
      ["Bank transfer (automatic)", 1544],
      ["Credit card (automatic)", 1522],
    ],
  },
  {
    name: "MonthlyCharges",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 64.76,
    std: 30.09,
    min: 18.25,
    q1: 35.5,
    median: 70.35,
    q3: 89.85,
    max: 118.75,
  },
  {
    name: "TotalCharges",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 2283.3,
    std: 2266.77,
    min: 18.8,
    q1: 401.45,
    median: 1397.6,
    q3: 3794.7,
    max: 8684.8,
  },
  {
    name: "Churn",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["No", 5174],
      ["Yes", 1869],
    ],
  },
];

const AI_COLUMNS: ColDef[] = [
  {
    name: "age",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 54.44,
    std: 9.04,
    min: 28,
    q1: 47,
    median: 54,
    q3: 61,
    max: 77,
  },
  {
    name: "gender",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["Male", 543],
      ["Female", 375],
    ],
  },
  {
    name: "chest_pain_type",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 4,
    top: [
      ["ASY", 496],
      ["NAP", 205],
      ["ATA", 173],
      ["TA", 44],
    ],
  },
  {
    name: "resting_blood_pressure",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 132.4,
    std: 17.6,
    min: 94,
    q1: 120,
    median: 130,
    q3: 140,
    max: 200,
  },
  {
    name: "cholesterol",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 198.8,
    std: 109.4,
    min: 85,
    q1: 173,
    median: 223,
    q3: 267,
    max: 603,
  },
  {
    name: "resting_ecg",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["Normal", 552],
      ["LVH", 188],
      ["ST", 178],
    ],
  },
  {
    name: "max_heart_rate",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 137.5,
    std: 25.5,
    min: 71,
    q1: 120,
    median: 138,
    q3: 156,
    max: 202,
  },
  {
    name: "exercise_angina",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["N", 549],
      ["Y", 369],
    ],
  },
  {
    name: "oldpeak",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 0.887,
    std: 1.067,
    min: -2.6,
    q1: 0,
    median: 0.6,
    q3: 1.6,
    max: 6.2,
  },
  {
    name: "st_slope",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["Flat", 462],
      ["Up", 440],
      ["Down", 16],
    ],
  },
  {
    name: "heart_disease",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 0.45,
    std: 0.498,
    min: 0,
    q1: 0,
    median: 0,
    q3: 1,
    max: 1,
  },
];

const INSURANCE_COLUMNS: ColDef[] = [
  {
    name: "age",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 39.2,
    std: 14.0,
    min: 18,
    q1: 27,
    median: 39,
    q3: 51,
    max: 64,
  },
  {
    name: "sex",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["male", 676],
      ["female", 662],
    ],
  },
  {
    name: "bmi",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 30.66,
    std: 6.1,
    min: 15.96,
    q1: 26.3,
    median: 30.4,
    q3: 34.7,
    max: 53.13,
  },
  {
    name: "children",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 1.09,
    std: 1.21,
    min: 0,
    q1: 0,
    median: 1,
    q3: 2,
    max: 5,
  },
  {
    name: "smoker",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 2,
    top: [
      ["no", 1064],
      ["yes", 274],
    ],
  },
  {
    name: "region",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 4,
    top: [
      ["southeast", 364],
      ["southwest", 325],
      ["northwest", 325],
      ["northeast", 324],
    ],
  },
  {
    name: "charges",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 13270.4,
    std: 12110.0,
    min: 1121.9,
    q1: 4740.3,
    median: 9382.0,
    q3: 16639.9,
    max: 63770.4,
  },
];

const FAULTY_COLUMNS: ColDef[] = [
  { name: "order_id", dtype: "object", numeric: false, nullCount: 0, cardinality: 5000 },
  { name: "customer_id", dtype: "object", numeric: false, nullCount: 312, cardinality: 3800 },
  {
    name: "order_total",
    dtype: "float64",
    numeric: true,
    nullCount: 210,
    mean: 128.4,
    std: 96.2,
    min: -18.5,
    q1: 41.2,
    median: 99.4,
    q3: 188.9,
    max: 1124.5,
  },
  {
    name: "shipping_region",
    dtype: "object",
    numeric: false,
    nullCount: 34,
    cardinality: 9,
    top: [
      ["west", 1187],
      ["east", 1151],
      ["south", 1103],
      ["north", 1053],
    ],
  },
  {
    name: "priority",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["standard", 2810],
      ["priority", 1540],
      ["express", 650],
    ],
  },
  {
    name: "is_returned",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 0.12,
    std: 0.33,
    min: 0,
    q1: 0,
    median: 0,
    q3: 0,
    max: 1,
  },
];

const SEGMENTS_COLUMNS: ColDef[] = [
  {
    name: "annual_income_k",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 60.2,
    std: 26.4,
    min: 15.0,
    q1: 41.0,
    median: 58.0,
    q3: 76.0,
    max: 137.0,
  },
  {
    name: "spending_score",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 50.2,
    std: 25.8,
    min: 1,
    q1: 34,
    median: 50,
    q3: 73,
    max: 99,
  },
  {
    name: "age",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 39.0,
    std: 14.0,
    min: 18,
    q1: 28,
    median: 36,
    q3: 49,
    max: 70,
  },
  {
    name: "recency_days",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 48.4,
    std: 26.1,
    min: 1,
    q1: 24,
    median: 46,
    q3: 70,
    max: 99,
  },
  {
    name: "freq_purchases",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 12.5,
    std: 6.4,
    min: 1,
    q1: 7,
    median: 12,
    q3: 17,
    max: 31,
  },
  {
    name: "avg_order_value",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 96.8,
    std: 41.2,
    min: 12.4,
    q1: 66.1,
    median: 92.6,
    q3: 125.8,
    max: 244.6,
  },
  {
    name: "returns_flag",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 0.18,
    std: 0.38,
    min: 0,
    q1: 0,
    median: 0,
    q3: 0,
    max: 1,
  },
  { name: "customer_id", dtype: "object", numeric: false, nullCount: 0, cardinality: 2000 },
];

const IRIS_COLUMNS: ColDef[] = [
  {
    name: "sepal_length",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 5.84,
    std: 0.83,
    min: 4.3,
    q1: 5.1,
    median: 5.8,
    q3: 6.4,
    max: 7.9,
  },
  {
    name: "sepal_width",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 3.05,
    std: 0.43,
    min: 2.0,
    q1: 2.8,
    median: 3.0,
    q3: 3.3,
    max: 4.4,
  },
  {
    name: "petal_length",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 3.76,
    std: 1.76,
    min: 1.0,
    q1: 1.6,
    median: 4.35,
    q3: 5.1,
    max: 6.9,
  },
  {
    name: "petal_width",
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 1.2,
    std: 0.76,
    min: 0.1,
    q1: 0.3,
    median: 1.3,
    q3: 1.8,
    max: 2.5,
  },
  {
    name: "species",
    dtype: "object",
    numeric: false,
    nullCount: 0,
    cardinality: 3,
    top: [
      ["setosa", 50],
      ["versicolor", 50],
      ["virginica", 50],
    ],
  },
];

const CREDIT_CARD_COLUMNS: ColDef[] = [
  {
    name: "LIMIT_BAL",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 167484.3,
    std: 129747.7,
    min: 10000,
    q1: 50000,
    median: 140000,
    q3: 240000,
    max: 1000000,
  },
  {
    name: "SEX",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 1.6,
    std: 0.49,
    min: 1,
    q1: 1,
    median: 2,
    q3: 2,
    max: 2,
  },
  {
    name: "EDUCATION",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 1.85,
    std: 0.52,
    min: 1,
    q1: 2,
    median: 2,
    q3: 2,
    max: 4,
  },
  {
    name: "MARRIAGE",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 1.55,
    std: 0.52,
    min: 0,
    q1: 1,
    median: 2,
    q3: 2,
    max: 3,
  },
  {
    name: "AGE",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 35.5,
    std: 9.2,
    min: 21,
    q1: 28,
    median: 34,
    q3: 41,
    max: 79,
  },
  {
    name: "PAY_0",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: -0.02,
    std: 1.12,
    min: -2,
    q1: -1,
    median: 0,
    q3: 0,
    max: 8,
  },
  {
    name: "BILL_AMT1",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 51223.3,
    std: 73635.9,
    min: -165580,
    q1: 2551,
    median: 22381,
    q3: 67091,
    max: 964511,
  },
  {
    name: "PAY_AMT1",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 5663.6,
    std: 10239.0,
    min: 0,
    q1: 1000,
    median: 2100,
    q3: 5000,
    max: 873552,
  },
  {
    name: "default_payment_next_month",
    dtype: "int64",
    numeric: true,
    nullCount: 0,
    mean: 0.221,
    std: 0.415,
    min: 0,
    q1: 0,
    median: 0,
    q3: 0,
    max: 1,
  },
];

export const DATASET_SEEDS: DatasetSeed[] = [
  {
    summary: {
      id: "ds_churn",
      name: "customer_churn.csv",
      path: "samples/customer_churn.csv",
      format: "csv",
      sizeBytes: 2_411_600,
      rows: 7043,
      columns: 21,
      engine: "polars",
      engineReason: engineReason(2_411_600),
      validationPassed: true,
      missingCells: 11,
      duplicateRows: 92,
      targetColumn: "Churn",
      taskType: "classification",
      registeredAt: "2026-09-18T09:12:00.000Z",
      lastUsedRunId: "run_8f17d3c9",
    },
    columns: CHURN_COLUMNS,
    transformLog: [
      { action: "handle_nulls", strategy: "drop", columns_affected: 0 },
      {
        action: "cast_dtypes",
        columns_cast: ["customerID", "gender"],
        type_map: { customerID: "string", gender: "category" },
      },
      { action: "encode_categoricals", columns_encoded: 1 },
    ],
    validationAssertions: { duplicateRows: 92 },
  },
  {
    summary: {
      id: "ds_heart",
      name: "heart_disease.csv",
      path: "samples/heart_disease.csv",
      format: "csv",
      sizeBytes: 402_300,
      rows: 918,
      columns: 11,
      engine: "pandas",
      engineReason: engineReason(402_300),
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 0,
      targetColumn: "heart_disease",
      taskType: "classification",
      registeredAt: "2026-09-19T14:02:00.000Z",
      lastUsedRunId: "run_5e2b7d4a",
    },
    columns: AI_COLUMNS,
    transformLog: [
      { action: "handle_nulls", strategy: "drop", columns_affected: 0 },
      { action: "encode_categoricals", columns_encoded: 4 },
    ],
    validationAssertions: { duplicateRows: 0 },
  },
  {
    summary: {
      id: "ds_insurance",
      name: "insurance_costs.csv",
      path: "samples/insurance_costs.csv",
      format: "csv",
      sizeBytes: 301_000,
      rows: 1338,
      columns: 7,
      engine: "pandas",
      engineReason: engineReason(301_000),
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 1,
      targetColumn: "charges",
      taskType: "regression",
      registeredAt: "2026-09-17T11:40:00.000Z",
      lastUsedRunId: "run_a1b2c3d4",
    },
    columns: INSURANCE_COLUMNS,
    validationAssertions: { duplicateRows: 1 },
  },
  {
    summary: {
      id: "ds_faulty",
      name: "faulty_orders.csv",
      path: "samples/faulty_orders.csv",
      format: "csv",
      sizeBytes: 512_800,
      rows: 5000,
      columns: 6,
      engine: "pandas",
      engineReason: engineReason(512_800),
      validationPassed: false,
      missingCells: 556,
      duplicateRows: 0,
      targetColumn: "is_returned",
      taskType: "classification",
      registeredAt: "2026-09-18T16:55:00.000Z",
      lastUsedRunId: "run_7f0e9d8c",
    },
    columns: FAULTY_COLUMNS,
    transformLog: [
      {
        action: "handle_nulls",
        strategy: "drop",
        columns_affected: 556,
        rows_before: 5000,
        rows_after: 4444,
      },
      { action: "encode_categoricals", columns_encoded: 2 },
    ],
    validationAssertions: {
      nullColumns: ["customer_id", "order_total", "shipping_region"],
      passed: false,
      issues: ["Missing values found in 3 columns.", "Negative order_total values present."],
    },
  },
  {
    summary: {
      id: "ds_segments",
      name: "customer_segments.csv",
      path: "samples/customer_segments.csv",
      format: "csv",
      sizeBytes: 288_000,
      rows: 2000,
      columns: 8,
      engine: "pandas",
      engineReason: engineReason(288_000),
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 12,
      targetColumn: null,
      taskType: "clustering",
      registeredAt: "2026-09-16T08:20:00.000Z",
      lastUsedRunId: "run_3d4c5b6a",
    },
    columns: SEGMENTS_COLUMNS,
    validationAssertions: { duplicateRows: 12 },
  },
  {
    summary: {
      id: "ds_iris",
      name: "iris.csv",
      path: "data/iris.csv",
      format: "csv",
      sizeBytes: 4_300,
      rows: 150,
      columns: 5,
      engine: "pandas",
      engineReason: engineReason(4_300),
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 0,
      targetColumn: "species",
      taskType: "classification",
      registeredAt: "2026-09-14T10:00:00.000Z",
      lastUsedRunId: null,
      sample: true,
    },
    columns: IRIS_COLUMNS,
    validationAssertions: { duplicateRows: 0 },
  },
  {
    summary: {
      id: "ds_cc_clients",
      name: "credit_card_clients.csv",
      path: "data/credit_card_clients.csv",
      format: "csv",
      sizeBytes: 2_310_400,
      rows: 30000,
      columns: 9,
      engine: "polars",
      engineReason: engineReason(2_310_400),
      validationPassed: true,
      missingCells: 0,
      duplicateRows: 0,
      targetColumn: "default_payment_next_month",
      taskType: "classification",
      registeredAt: "2026-09-13T09:30:00.000Z",
      lastUsedRunId: null,
      sample: true,
    },
    columns: CREDIT_CARD_COLUMNS,
    validationAssertions: { duplicateRows: 0 },
  },
];

export const DEMO_DATASETS: Record<string, Dataset> = Object.fromEntries(
  DATASET_SEEDS.map((seed) => [seed.summary.id, buildDataset(seed)]),
);

export const NEW_RUN_AVAILABLE_DATASETS = [
  "ds_churn",
  "ds_heart",
  "ds_insurance",
  "ds_segments",
  "ds_iris",
  "ds_cc_clients",
];

/* ------------------------------------------------------------------ */
/* Mutable demo store (upload / delete parity)                        */
/* ------------------------------------------------------------------ */

/** Generic numeric columns for synthetic uploaded files. */
function genericColumns(count: number): ColDef[] {
  return Array.from({ length: Math.max(1, count) }, (_, i) => ({
    name: `column_${i + 1}`,
    dtype: "float64",
    numeric: true,
    nullCount: 0,
    mean: 0,
    std: 1,
    min: -3,
    q1: -0.67,
    median: 0,
    q3: 0.67,
    max: 3,
  }));
}

/** Register a synthetic uploaded dataset in the demo store. */
export function registerDemoDataset(summary: DatasetSummary): Dataset {
  const seed: DatasetSeed = {
    summary,
    columns: genericColumns(summary.columns),
    validationAssertions: { duplicateRows: 0 },
  };
  DATASET_SEEDS.push(seed);
  const dataset = buildDataset(seed);
  DEMO_DATASETS[summary.id] = dataset;
  NEW_RUN_AVAILABLE_DATASETS.push(summary.id);
  return dataset;
}

/** Remove a dataset from the demo store; false if it does not exist. */
export function removeDemoDataset(id: string): boolean {
  const idx = DATASET_SEEDS.findIndex((s) => s.summary.id === id);
  if (idx === -1 && !DEMO_DATASETS[id]) return false;
  if (idx !== -1) DATASET_SEEDS.splice(idx, 1);
  delete DEMO_DATASETS[id];
  const avail = NEW_RUN_AVAILABLE_DATASETS.indexOf(id);
  if (avail !== -1) NEW_RUN_AVAILABLE_DATASETS.splice(avail, 1);
  return true;
}
