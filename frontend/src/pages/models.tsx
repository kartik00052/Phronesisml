import * as React from "react";
import { BrainCircuit } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { RunPicker } from "@/components/run/run-picker";
import { RunModelsView } from "@/components/run/run-models";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRun } from "@/hooks/use-runs";

export default function ModelsPage() {
  const [runId, setRunId] = React.useState("");
  const { data: run, isLoading } = useRun(runId || undefined);

  const header = (
    <PageHeader
      title="Models"
      description="Best models per run, from quick baselines to fully tuned candidates."
    >
      <RunPicker value={runId} onChange={setRunId} showStatus />
    </PageHeader>
  );

  if (runId && isLoading) {
    return (
      <div className="space-y-6">
        {header}
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (!runId || !run) {
    return (
      <div className="space-y-6">
        {header}
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <BrainCircuit className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Select a run to view its model leaderboard.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {header}
      <RunModelsView runId={run.id} taskType={run.summary.taskType} />
    </div>
  );
}
