import * as React from "react";
import {
  Activity,
  CheckCircle2,
  Database,
  Flag,
  Gauge,
  PlayCircle,
  Rocket,
  TriangleAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { STAGE_META } from "@/config/pipeline";
import { formatRelative } from "@/lib/format";
import { formatDurationMs } from "@/lib/format";
import type { Run } from "@/types/run";
import type { PipelineStageId, StageDetail } from "@/types/pipeline";

type EventKind = "run" | "sampling" | "engine" | "stage" | "complete" | "fail";

interface ActivityEvent {
  id: string;
  time: string;
  title: string;
  detail?: string;
  kind: EventKind;
  status?: StageDetail["status"];
  durationMs?: number | null;
}

const KIND_STYLE: Record<EventKind, { dot: string; badge?: string }> = {
  run: { dot: "bg-info" },
  sampling: { dot: "bg-warning" },
  engine: { dot: "bg-secondary-foreground" },
  stage: { dot: "bg-primary" },
  complete: { dot: "bg-success" },
  fail: { dot: "bg-danger" },
};

function buildEvents(run: Run, stages: StageDetail[]): ActivityEvent[] {
  const events: ActivityEvent[] = [];
  const stageById = new Map(stages.map((s) => [s.id, s]));
  const stageName = (id: string) => STAGE_META[id as PipelineStageId]?.label ?? id.replace(/_/g, " ");

  events.push({
    id: "run-created",
    time: run.createdAt,
    title: `Run ${run.id} queued by the agent`,
    detail: `${run.summary.datasetName} · ${run.summary.rows.toLocaleString()}×${run.summary.columns} · ${run.request.mode} mode`,
    kind: "run",
  });

  if (run.sampling) {
    const s = run.sampling;
    events.push({
      id: "sampling",
      time: stageById.get("node_sampling")?.startedAt ?? run.createdAt,
      title: s.was_sampled ? "Sampling strategy applied" : "Sampling not required",
      detail: s.was_sampled
        ? `${[s.sampling_method, s.sampling_ratio != null ? `${Math.round(s.sampling_ratio * 100)}% of data` : null, s.reason]
            .filter(Boolean)
            .join(" · ")}`
        : s.reason,
      kind: "sampling",
    });
  }

  events.push({
    id: "engine",
    time: stageById.get("etl")?.completedAt ?? stageById.get("etl")?.startedAt ?? run.createdAt,
    title: `Compute engine resolved → ${run.summary.engine}`,
    detail: run.summary.engineReason,
    kind: "engine",
  });

  const summaryText = (value: StageDetail["summary"][string]): string | undefined =>
    value == null ? undefined : String(value);

  for (const [index, stage] of stages.entries()) {
    if (stage.queuedAt) {
      events.push({
        id: `${stage.id}-${index}-queued`,
        time: stage.queuedAt,
        title: `${stageName(stage.id)} queued`,
        detail: summaryText(stage.summary.role) ?? STAGE_META[stage.id as PipelineStageId]?.description,
        kind: "stage",
        status: "queued",
      });
    }
    if (stage.startedAt) {
      events.push({
        id: `${stage.id}-${index}-started`,
        time: stage.startedAt,
        title: `${stageName(stage.id)} started`,
        kind: "stage",
        status: "running",
      });
    }
    if (stage.completedAt) {
      events.push({
        id: `${stage.id}-${index}-completed`,
        time: stage.completedAt,
        title: `${stageName(stage.id)} ${stage.status === "failed" ? "failed" : "completed"}`,
        detail: stage.error?.message ?? summaryText(stage.summary.notes),
        kind: stage.status === "failed" ? "fail" : "stage",
        status: stage.status,
        durationMs: stage.durationMs,
      });
    }
  }

  if (run.status === "completed") {
    events.push({
      id: "run-complete",
      time: run.updatedAt,
      title: `Run complete — best ${run.summary.bestModelType ?? "model"}`,
      detail: run.summary.bestScore != null
        ? `${run.summary.primaryMetric} ${run.summary.bestScore.toFixed(3)}${run.summary.hpoTruncated ? " (HPO truncated)" : ""}`
        : undefined,
      kind: "complete",
      durationMs: run.totalDurationMs,
    });
  } else if (run.status === "failed") {
    events.push({
      id: "run-fail",
      time: run.updatedAt,
      title: "Run failed",
      detail: run.error?.message,
      kind: "fail",
    });
  }

  return events
    .filter((e) => e.time)
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

function EventIcon({ kind }: { kind: EventKind }) {
  switch (kind) {
    case "run":
      return <Rocket className="size-3.5" />;
    case "sampling":
      return <Database className="size-3.5" />;
    case "engine":
      return <Gauge className="size-3.5" />;
    case "complete":
      return <CheckCircle2 className="size-3.5" />;
    case "fail":
      return <TriangleAlert className="size-3.5" />;
    default:
      return <PlayCircle className="size-3.5" />;
  }
}

export function ActivityFeed({ run, stages }: { run: Run; stages: StageDetail[] }) {
  const events = React.useMemo(() => buildEvents(run, stages), [run, stages]);

  if (events.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-dashed p-8 text-sm text-muted-foreground">
        <Activity className="size-4" /> No activity recorded yet.
      </div>
    );
  }

  return (
    <ol className="relative ml-2 space-y-5 border-l border-border pl-6">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span
            className={`absolute -left-[31px] flex size-4 items-center justify-center rounded-full border border-border ${KIND_STYLE[event.kind].dot}`}
            style={{ color: "var(--background)" }}
          >
            <span className="text-[9px]"><EventIcon kind={event.kind} /></span>
          </span>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <p className="text-sm font-medium text-foreground">{event.title}</p>
            {event.status && (
              <Badge variant={event.status === "failed" ? "danger" : event.status === "running" ? "info" : event.status === "queued" ? "muted" : "success"}>
                {event.status}
              </Badge>
            )}
            {event.durationMs != null && (
              <span className="font-mono text-xs text-muted-foreground">{formatDurationMs(event.durationMs)}</span>
            )}
            <span className="ml-auto shrink-0 text-xs tabular-nums text-muted-foreground">
              {formatRelative(event.time)}
            </span>
          </div>
          {event.detail && (
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{event.detail}</p>
          )}
        </li>
      ))}
      {run.status === "running" && (
        <li className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-60" />
            <span className="relative inline-flex size-2.5 rounded-full bg-info" />
          </span>
          <span><Flag className="mr-1 inline size-3.5" /> orchestrating pipeline…</span>
        </li>
      )}
    </ol>
  );
}