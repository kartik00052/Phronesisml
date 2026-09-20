import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Activity, ArrowRight } from "lucide-react";

import { getPipelineProgress } from "@/api/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { STAGE_META } from "@/config/pipeline";
import { isDemoMode } from "@/mocks";
import type { RecentRunActivity } from "@/types/run";

/**
 * Live progress of the currently running experiment (if any).
 * Polls the pipeline progress endpoint while a run is active.
 */
export function PipelineHealth({ run }: { run?: RecentRunActivity }) {
  const isLive = !!run && run.status === "running";
  const { data: progress } = useQuery({
    queryKey: ["pipeline", "progress", run?.id],
    queryFn: () => getPipelineProgress(run!.id),
    enabled: isLive,
    refetchInterval: isDemoMode() ? 550 : 2000,
  });

  if (!isLive) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center gap-4 p-5">
          <div className="flex size-10 items-center justify-center rounded-md border border-border bg-muted/40 text-muted-foreground">
            <Activity className="size-5" />
          </div>
          <div>
            <p className="text-sm font-medium">No active pipelines</p>
            <p className="text-sm text-muted-foreground">
              All experiments are idle.{" "}
              <Link to="/runs/new" className="font-medium text-primary hover:underline">
                Start a new run
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const completed = progress?.completedStages ?? [];
  const current = progress?.currentStage ?? null;
  const total = progress?.totalStages ?? 0;
  const pct = total > 0 ? Math.round((completed.length / total) * 100) : 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-60" />
            <span className="relative inline-flex size-2.5 rounded-full bg-info" />
          </span>
          Live pipeline
        </CardTitle>
        <Button asChild variant="ghost" size="sm" className="gap-1 text-muted-foreground">
          <Link to={`/runs/${run.id}`}>
            Open run <ArrowRight className="size-3.5" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{run.datasetName}</p>
            <p className="truncate font-mono text-xs text-muted-foreground">{run.id}</p>
          </div>
          <span className="shrink-0 text-sm font-semibold tabular-nums">{pct}%</span>
        </div>
        <div className="flex items-center gap-2">
          <Progress value={pct} className="h-1.5 flex-1" indicatorClassName="bg-info" />
          <span className="text-xs tabular-nums text-muted-foreground">
            {completed.length}/{total} stages
          </span>
        </div>
        {current && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-xs text-muted-foreground">Running:</span>
            <Badge variant="info">{STAGE_META[current]?.label ?? current}</Badge>
            {progress?.messages?.slice(-1).map((m, i) => (
              <span key={i} className="truncate text-xs text-muted-foreground">
                {m}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}