import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  CircleDot,
  CircleOff,
  Loader2,
  Play,
  SkipForward,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import type { PipelineStageStatus } from "@/types/pipeline";
import type { RunStatus, TaskType } from "@/types/run";

export interface StatusMeta {
  label: string;
  /** Semantic token class suffixes for {bg,text,border}. */
  tone: "muted" | "info" | "success" | "warning" | "danger";
  icon: LucideIcon;
  dotClass: string;
}

export const STAGE_STATUS_META: Record<PipelineStageStatus, StatusMeta> = {
  idle: {
    label: "Idle",
    tone: "muted",
    icon: Circle,
    dotClass: "bg-muted-foreground/40",
  },
  queued: {
    label: "Queued",
    tone: "muted",
    icon: Play,
    dotClass: "bg-muted-foreground/70",
  },
  running: {
    label: "Running",
    tone: "info",
    icon: Loader2,
    dotClass: "bg-info",
  },
  completed: {
    label: "Completed",
    tone: "success",
    icon: CheckCircle2,
    dotClass: "bg-success",
  },
  warning: {
    label: "Warning",
    tone: "warning",
    icon: AlertTriangle,
    dotClass: "bg-warning",
  },
  failed: {
    label: "Failed",
    tone: "danger",
    icon: XCircle,
    dotClass: "bg-danger",
  },
  skipped: {
    label: "Skipped",
    tone: "muted",
    icon: SkipForward,
    dotClass: "bg-muted-foreground/30",
  },
  sampled: {
    label: "Sampled",
    tone: "warning",
    icon: CircleDot,
    dotClass: "bg-warning",
  },
};

export const RUN_STATUS_META: Record<RunStatus, StatusMeta> = {
  queued: { label: "Queued", tone: "muted", icon: Circle, dotClass: "bg-muted-foreground/70" },
  running: { label: "Running", tone: "info", icon: Loader2, dotClass: "bg-info" },
  completed: { label: "Completed", tone: "success", icon: CheckCircle2, dotClass: "bg-success" },
  failed: { label: "Failed", tone: "danger", icon: XCircle, dotClass: "bg-danger" },
  cancelled: { label: "Cancelled", tone: "warning", icon: CircleOff, dotClass: "bg-warning" },
};

export const TASK_LABELS: Record<TaskType, string> = {
  classification: "Classification",
  regression: "Regression",
  clustering: "Clustering",
  anomaly_detection: "Anomaly Detection",
  ambiguous: "Ambiguous",
  analytics: "Analytics",
  unknown: "Unknown",
};

export const ENGINE_LABELS: Record<string, string> = {
  pandas: "Pandas",
  polars: "Polars",
  spark: "Spark",
  auto: "Auto",
};
