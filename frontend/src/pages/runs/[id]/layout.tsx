import * as React from "react";
import { Outlet, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { PageSkeleton } from "@/components/layout/page-skeleton";
import { RunHeader } from "@/components/run/run-header";
import { RunTabs } from "@/components/run/run-tabs";
import { Alert } from "@/components/ui/alert";
import { ErrorState } from "@/components/ui/empty-state";
import { useRun, useRunLogs, queryKeys } from "@/hooks/use-runs";
import { usePipelineStages, pipelineKeys } from "@/hooks/use-pipeline";
import { useRunEvents } from "@/hooks/use-run-events";
import { toApiError } from "@/api/client";
import type { Run } from "@/types/run";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunLayout() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();

  const cachedRun = queryClient.getQueryData<Run>(queryKeys.run(runId));
  const live = cachedRun?.status === "running" || cachedRun?.status === "queued";

  // Real-time event stream: replay-from-last-seq + live events drive query
  // invalidation so the workspace reflects persisted backend state.
  useRunEvents(runId, live);

  const { data: run, isLoading, isError, error, refetch } = useRun(runId, { live });
  const { data: stages } = usePipelineStages(runId, live);
  const { data: logs } = useRunLogs(runId);

  const refresh = React.useCallback(() => {
    void refetch();
    void queryClient.invalidateQueries({ queryKey: pipelineKeys.stages(runId) });
    void queryClient.invalidateQueries({ queryKey: pipelineKeys.overview(runId) });
    void queryClient.invalidateQueries({ queryKey: ["runs", runId, "logs"] });
  }, [refetch, queryClient, runId]);

  if (isLoading) return <PageSkeleton />;

  if (isError || !run) {
    return (
      <ErrorState
        title={`Could not load run ${runId}`}
        description={error ? toApiError(error).message : "Unknown error"}
        action={
          <button
            type="button"
            onClick={() => void refetch()}
            className="text-xs font-medium text-primary underline"
          >
            Try again
          </button>
        }
      />
    );
  }

  const context: RunOutletContext = {
    run,
    stages: stages ?? [],
    logs: logs ?? run.logs,
    live,
    refresh,
  };

  return (
    <div className="space-y-5">
      <RunHeader run={run} onRefresh={refresh} />

      {run.status === "failed" && run.error && (
        <Alert variant="destructive">
          <p className="font-medium">{run.error.message}</p>
          {run.error.context && (
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {JSON.stringify(run.error.context)}
            </p>
          )}
        </Alert>
      )}

      <RunTabs runId={run.id} />

      <Outlet context={context} />
    </div>
  );
}
