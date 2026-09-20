import { Activity, Database, Gauge, Layers, Timer, TriangleAlert } from "lucide-react";

import { ActivityFeed } from "@/components/run/activity-feed";
import { SamplingPanel } from "@/components/run/sampling-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useRunProgress } from "@/hooks/use-pipeline";
import { formatDurationMs, formatNumber, formatRelative, formatScore } from "@/lib/format";
import type { Run } from "@/types/run";
import type { StageDetail } from "@/types/pipeline";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 truncate text-sm font-semibold tabular-nums text-foreground" title={value}>
        {value}
      </p>
      {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function LiveProgress({ runId, status }: { runId: string; status: string }) {
  const { data: progress } = useRunProgress(runId, status === "running" || status === "queued");
  if (!progress) return null;
  const pct =
    progress.totalStages > 0
      ? Math.round((progress.completedStages.length / progress.totalStages) * 100)
      : 0;

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2 font-medium text-foreground">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-info" />
            </span>
            {progress.status === "completed"
              ? "Pipeline complete"
              : progress.currentStage
                ? `Running: ${progress.currentStage.replace(/_/g, " ")}`
                : "Queued…"}
          </span>
          <span className="tabular-nums text-muted-foreground">
            {progress.completedStages.length}/{progress.totalStages} stages
          </span>
        </div>
        <Progress value={pct} className="h-1.5" />
        {progress.messages.at(-1) && (
          <p className="truncate text-xs text-muted-foreground">{progress.messages.at(-1)}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function RunOverview({ run, stages }: { run: Run; stages: StageDetail[] }) {
  const s = run.summary;

  return (
    <div className="space-y-4">
      {(run.status === "running" || run.status === "queued") && (
        <LiveProgress runId={run.id} status={run.status} />
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label={`Best ${s.primaryMetric || "score"}`}
          value={s.bestScore != null ? formatScore(s.bestScore) : "—"}
          hint={s.bestModelType ?? "Pending"}
        />
        <Stat
          label="Dataset"
          value={s.datasetName}
          hint={`${formatNumber(s.rows)} × ${formatNumber(s.columns)} · ${s.fileFormat}`}
        />
        <Stat label="Task" value={s.taskType.replace(/_/g, " ")} hint={s.targetColumn ? `target: ${s.targetColumn}` : "no target"} />
        <Stat label="Engine" value={s.engine} hint={s.engineReason} />
        <Stat
          label="Duration"
          value={run.totalDurationMs != null ? formatDurationMs(run.totalDurationMs) : "—"}
          hint={s.mode}
        />
        <Stat
          label="Stages executed"
          value={`${run.stagesExecuted.length}/${run.stagesRequested.length}`}
          hint="of requested stages"
        />
        <Stat
          label="Trials"
          value={s.trialCount != null ? formatNumber(s.trialCount) : "—"}
          hint={s.hpoTruncated ? "HPO truncated by budget" : "full search"}
        />
        <Stat
          label="Updated"
          value={s.updatedAt ? formatRelative(s.updatedAt) : "—"}
          hint={new Date(s.updatedAt).toLocaleString()}
        />
      </div>

      {run.warnings.length > 0 && (
        <Card className="border-warning/40 bg-warning/5">
          <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
            <TriangleAlert className="size-4 text-warning" />
            <CardTitle className="text-sm">Warnings ({run.warnings.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
              {run.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="size-4 text-muted-foreground" />
              Agent activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stages.length > 0 ? (
              <ActivityFeed run={run} stages={stages} />
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Activity appears once stages report progress.
              </p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <SamplingPanel sampling={run.sampling} resource={run.resourceReport} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat icon={<Layers className="size-3.5" />} label="Requested" value={String(run.stagesRequested.length)} />
        <MiniStat icon={<Gauge className="size-3.5" />} label="Mode" value={s.mode} />
        <MiniStat icon={<Database className="size-3.5" />} label="Format" value={s.fileFormat} />
        <MiniStat
          icon={<Timer className="size-3.5" />}
          label="Created"
          value={new Date(run.createdAt).toLocaleDateString()}
        />
      </div>
    </div>
  );
}

function MiniStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-xs">
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-muted-foreground">{label}</span>
      <span className="ml-auto font-medium capitalize text-foreground">{value}</span>
    </div>
  );
}
