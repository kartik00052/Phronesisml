import { Link } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useRunProgress } from "@/hooks/use-pipeline";
import type { RecentRunActivity } from "@/types/run";

/** Prominent live banner shown on the dashboard while a run is active. */
export function ActiveRunBanner({ run }: { run: RecentRunActivity }) {
  const { data: progress } = useRunProgress(run.id, true);
  const pct =
    progress && progress.totalStages > 0
      ? Math.round((progress.completedStages.length / progress.totalStages) * 100)
      : 0;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-info/40 bg-info/5 p-4 sm:flex-row sm:items-center">
      <Loader2 className="size-5 shrink-0 animate-spin text-info" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">
          {run.datasetName} is {progress?.currentStage ? `running ${progress.currentStage.replace(/_/g, " ")}` : "in progress"}
        </p>
        <div className="mt-2 flex items-center gap-3">
          <Progress value={pct} className="h-1.5 max-w-sm" />
          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {progress ? `${progress.completedStages.length}/${progress.totalStages} stages` : "queued"}
          </span>
        </div>
      </div>
      <Button asChild size="sm" variant="outline" className="shrink-0 gap-1.5">
        <Link to={`/runs/${run.id}`}>
          Open workspace
          <ArrowRight className="size-3.5" />
        </Link>
      </Button>
    </div>
  );
}
