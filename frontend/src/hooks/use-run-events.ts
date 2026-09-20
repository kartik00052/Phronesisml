import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { connectRunEvents } from "@/api/websocket";
import { isDemoMode } from "@/mocks";
import { pipelineKeys } from "@/hooks/use-pipeline";
import { queryKeys as runKeys } from "@/hooks/use-runs";
import { queryKeys as datasetKeys } from "@/hooks/use-datasets";
import { queryKeys as artifactKeys } from "@/hooks/use-run-extras";

/**
 * Live run events → query invalidation.
 *
 * In real mode, subscribes to `/ws/runs/{runId}` and invalidates the
 * pipeline / run / artifact queries on every event so the UI reflects
 * persisted backend state as soon as a stage finishes.
 */
export function useRunEvents(runId: string | undefined, enabled = false) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!runId || !enabled || isDemoMode()) return;
    const invalidate = () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.stages(runId) });
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.progress(runId) });
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.overview(runId) });
      void queryClient.invalidateQueries({ queryKey: runKeys.run(runId) });
      void queryClient.invalidateQueries({ queryKey: runKeys.runLogs(runId) });
      void queryClient.invalidateQueries({ queryKey: datasetKeys.runDataset(runId) });
      void queryClient.invalidateQueries({ queryKey: artifactKeys.artifacts(runId) });
      void queryClient.invalidateQueries({ queryKey: artifactKeys.explainability(runId) });
      void queryClient.invalidateQueries({ queryKey: artifactKeys.models(runId) });
      void queryClient.invalidateQueries({ queryKey: artifactKeys.report(runId, "markdown") });
    };
    return connectRunEvents(runId, { onEvent: invalidate });
  }, [runId, enabled, queryClient]);
}
