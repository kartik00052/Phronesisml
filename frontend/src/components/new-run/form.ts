import { z } from "zod";

import { STAGE_SLICES } from "@/config/pipeline";
import type { EngineName, NullStrategy, RunMode, RunRequest, TaskType } from "@/types/run";

export const NULL_STRATEGY_META: Record<
  NullStrategy,
  { label: string; description: string }
> = {
  drop: { label: "Drop rows", description: "Drop rows that contain missing values." },
  fill: { label: "Impute", description: "Fill missing values with the median / mode." },
  flag: { label: "Flag", description: "Keep rows but add indicator flags." },
};

export const RUN_MODE_META: Record<RunMode, { label: string; description: string }> = {
  fast: {
    label: "Fast",
    description: "Quick baseline — 5 trials, shallow search, best for exploration.",
  },
  balanced: {
    label: "Balanced",
    description: "Default — moderate search depth and trial budget.",
  },
  full: {
    label: "Full",
    description: "Exhaustive — 40+ trials, deep hyperparameter search.",
  },
};

export interface WizardValues {
  datasetId: string;
  engine: "auto" | EngineName;
  nullStrategy: NullStrategy;
  pipelineDepth: string;
  mode: RunMode;
  advanced: boolean;
  targetOverride: string;
  taskOverride: string;
  cv: string;
  maxTrials: string;
  modelType: string;
  samplingStrategy: string;
  varianceThreshold: string;
  correlationThreshold: string;
  minFeatures: string;
}

export const wizardSchema = z.object({
  datasetId: z.string().min(1, { message: "Select a dataset to continue" }),
  engine: z.enum(["auto", "pandas", "polars", "spark"]),
  nullStrategy: z.enum(["drop", "fill", "flag"]),
  pipelineDepth: z.string().min(1, { message: "Choose a pipeline depth" }),
  mode: z.enum(["fast", "balanced", "full"]),
  advanced: z.boolean(),
  targetOverride: z.string(),
  taskOverride: z.string(),
  cv: z
    .string()
    .optional()
    .refine((v) => !v || (Number.isInteger(Number(v)) && Number(v) >= 2 && Number(v) <= 20), {
      message: "CV folds must be an integer between 2 and 20",
    }),
  maxTrials: z
    .string()
    .optional()
    .refine((v) => !v || (Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= 500), {
      message: "Trials must be between 1 and 500",
    }),
  modelType: z.string(),
  samplingStrategy: z.string(),
  varianceThreshold: z
    .string()
    .optional()
    .refine((v) => !v || (Number(v) >= 0 && Number(v) <= 1), { message: "Must be between 0 and 1" }),
  correlationThreshold: z
    .string()
    .optional()
    .refine((v) => !v || (Number(v) >= 0 && Number(v) <= 1), { message: "Must be between 0 and 1" }),
  minFeatures: z
    .string()
    .optional()
    .refine((v) => !v || (Number.isInteger(Number(v)) && Number(v) >= 1), { message: "Must be a positive integer" }),
});

export const wizardDefaults: WizardValues = {
  datasetId: "",
  engine: "auto",
  nullStrategy: "drop",
  pipelineDepth: STAGE_SLICES[STAGE_SLICES.length - 1].key,
  mode: "balanced",
  advanced: false,
  targetOverride: "",
  taskOverride: "",
  cv: "5",
  maxTrials: "",
  modelType: "",
  samplingStrategy: "auto",
  varianceThreshold: "0.01",
  correlationThreshold: "0.98",
  minFeatures: "2",
};

export function optionalNumber(value: string): number | null {
  if (!value || value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Map wizard state (plus resolved engine) into the API RunRequest payload. */
export function wizardToRequest(
  values: WizardValues,
  resolvedEngine: EngineName,
): RunRequest {
  const depth = STAGE_SLICES.find((s) => s.key === values.pipelineDepth);
  const stages = depth?.stages ?? STAGE_SLICES[STAGE_SLICES.length - 1].stages;
  const target = values.targetOverride.trim();
  const task = values.taskOverride.trim() as TaskType | "";

  return {
    datasetId: values.datasetId,
    engine: values.engine === "auto" ? resolvedEngine : values.engine,
    nullStrategy: values.nullStrategy,
    stages,
    mode: values.mode,
    targetOverride: target || null,
    taskOverride: (task || null) as TaskType | null,
    cv: optionalNumber(values.cv),
    maxTrials: optionalNumber(values.maxTrials),
    modelType: values.modelType.trim() || null,
    samplingStrategy: values.samplingStrategy === "auto" ? undefined : values.samplingStrategy,
    varianceThreshold: optionalNumber(values.varianceThreshold) ?? undefined,
    correlationThreshold: optionalNumber(values.correlationThreshold) ?? undefined,
    minFeatures: optionalNumber(values.minFeatures) ?? undefined,
  };
}