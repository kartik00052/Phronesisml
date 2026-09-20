import { CheckCircle2, Circle, CircleDot, Loader2, SkipForward, TriangleAlert, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";
import { STAGE_META } from "@/config/pipeline";
import { STAGE_STATUS_META } from "@/config/status";
import { formatDurationMs } from "@/lib/format";
import type { PipelineStageId, PipelineStageStatus, StageDetail } from "@/types/pipeline";

const STATUS_ICON: Record<PipelineStageStatus, React.ReactNode> = {
  idle: <Circle className="size-4 text-muted-foreground/50" />,
  queued: <Circle className="size-4 text-muted-foreground" />,
  running: <Loader2 className="size-4 animate-spin text-info" />,
  completed: <CheckCircle2 className="size-4 text-success" />,
  warning: <TriangleAlert className="size-4 text-warning" />,
  failed: <XCircle className="size-4 text-danger" />,
  skipped: <SkipForward className="size-4 text-muted-foreground/60" />,
  sampled: <CircleDot className="size-4 text-warning" />,
};

const RAIL: Record<PipelineStageStatus, string> = {
  idle: "bg-border",
  queued: "bg-border-strong",
  running: "bg-info",
  completed: "bg-success",
  warning: "bg-warning",
  failed: "bg-danger",
  skipped: "bg-border",
  sampled: "bg-warning/70",
};

export interface PipelineStepperProps {
  stages: StageDetail[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Linear, primary representation of the 11-stage pipeline. */
export function PipelineStepper({ stages, selectedId, onSelect }: PipelineStepperProps) {
  return (
    <ol className="space-y-0" aria-label="Pipeline stages">
      {stages.map((stage, index) => {
        const meta = stage.id === "node_sampling" ? null : STAGE_META[stage.id as PipelineStageId];
        const statusMeta = STAGE_STATUS_META[stage.status];
        const label = meta?.label ?? (stage.id === "node_sampling" ? "Sampling" : stage.name);
        const selected = selectedId === stage.id;
        const firstSummary = Object.entries(stage.summary ?? {}).find(
          ([, v]) => typeof v === "string" || typeof v === "number",
        );

        return (
          <li key={`${stage.id}-${index}`} className="relative">
            {index < stages.length - 1 && (
              <span
                className={cn("absolute left-[18px] top-9 h-[calc(100%-1.5rem)] w-px", RAIL[stage.status])}
                aria-hidden
              />
            )}
            <button
              type="button"
              onClick={() => onSelect(stage.id)}
              aria-current={selected ? "step" : undefined}
              className={cn(
                "group flex w-full items-start gap-3 rounded-md px-2 py-2 text-left transition-colors",
                selected ? "bg-muted/60" : "hover:bg-muted/30",
              )}
            >
              <span className="relative z-10 mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-card">
                {STATUS_ICON[stage.status]}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{label}</span>
                    <span className="text-xs text-muted-foreground">{statusMeta.label}</span>
                  </span>
                  <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    {stage.durationMs != null ? formatDurationMs(stage.durationMs) : "—"}
                  </span>
                </span>
                <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                  {stage.error?.message ??
                    (firstSummary ? `${firstSummary[0]}: ${String(firstSummary[1])}` : meta?.description)}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
