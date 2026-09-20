import { useQuery } from "@tanstack/react-query";

import { getPipelineOverview, getPipelineProgress, getPipelineStages } from "@/api/pipeline";
import { isDemoMode } from "@/mocks";

export const pipelineKeys = {
  stages: (runId: string) => ["pipeline", "stages", runId] as const,
  progress: (runId: string) => ["pipeline", "progress", runId] as const,
  overview: (runId: string) => ["pipeline", "overview", runId] as const,
};

const POLL_MS = isDemoMode() ? 550 : 2000;

export function usePipelineStages(runId: string | undefined, live = false) {
  return useQuery({
    queryKey: pipelineKeys.stages(runId ?? ""),
    queryFn: () => getPipelineStages(runId!),
    enabled: !!runId,
    refetchInterval: live ? POLL_MS : false,
  });
}

export function usePipelineOverview(runId: string | undefined, live = false) {
  return useQuery({
    queryKey: pipelineKeys.overview(runId ?? ""),
    queryFn: () => getPipelineOverview(runId!),
    enabled: !!runId,
    refetchInterval: live ? POLL_MS : false,
  });
}

export function useRunProgress(runId: string | undefined, live = false) {
  return useQuery({
    queryKey: pipelineKeys.progress(runId ?? ""),
    queryFn: () => getPipelineProgress(runId!),
    enabled: !!runId,
    refetchInterval: live ? POLL_MS : false,
  });
}
