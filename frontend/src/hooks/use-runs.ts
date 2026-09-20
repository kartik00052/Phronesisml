import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelRun,
  createRun,
  deleteRun,
  getDashboardStats,
  getRecentRuns,
  getRun,
  getRunLogs,
  listRuns,
  restoreRun,
} from "@/api/runs";
import type { ListQuery } from "@/types/api";
import type { RunRequest } from "@/types/run";
import { isDemoMode } from "@/mocks";

export const queryKeys = {
  runs: (query: ListQuery = {}) => ["runs", query] as const,
  run: (id: string) => ["runs", id] as const,
  runLogs: (id: string) => ["runs", id, "logs"] as const,
  dashboardStats: () => ["stats"] as const,
  recentRuns: () => ["runs", "recent"] as const,
};

export function useRuns(query: ListQuery = {}, opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.runs(query),
    queryFn: () => listRuns(query),
    enabled: opts?.enabled ?? true,
    placeholderData: (prev) => prev,
  });
}

/** Polls the run while live (running/queued) so the workspace stays fresh. */
export function useRun(runId: string | undefined, opts?: { live?: boolean }) {
  const live = opts?.live ?? false;
  return useQuery({
    queryKey: queryKeys.run(runId ?? ""),
    queryFn: () => getRun(runId!),
    enabled: !!runId,
    refetchInterval: live ? (isDemoMode() ? 700 : 2000) : false,
  });
}

export function useRunLogs(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.runLogs(runId ?? ""),
    queryFn: () => getRunLogs(runId!),
    enabled: !!runId,
    refetchInterval: isDemoMode() ? 700 : false,
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats(),
    queryFn: getDashboardStats,
  });
}

export function useRecentRuns() {
  return useQuery({
    queryKey: queryKeys.recentRuns(),
    queryFn: getRecentRuns,
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: RunRequest) => createRun(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.recentRuns() });
    },
  });
}

function useRunMutation<TData>(
  mutationFn: (runId: string) => Promise<TData>,
  keys: (runId: string) => readonly unknown[],
) {
  const queryClient = useQueryClient();
  return useMutation<TData, unknown, string>({
    mutationFn,
    onSuccess: (_data, runId) => {
      void queryClient.invalidateQueries({ queryKey: keys(runId) });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.recentRuns() });
    },
  });
}

export function useCancelRun() {
  return useRunMutation(
    (runId) => cancelRun(runId),
    (runId) => queryKeys.run(runId),
  );
}

export function useRestoreRun() {
  return useRunMutation(
    (runId) => restoreRun(runId),
    (runId) => queryKeys.run(runId),
  );
}

export function useDeleteRun() {
  return useRunMutation(
    (runId) => deleteRun(runId),
    (runId) => queryKeys.run(runId),
  );
}
