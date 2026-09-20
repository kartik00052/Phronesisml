import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import {
  demoListRuns,
  demoGetRun,
  demoCreateRun,
  demoCancelRun,
  demoRestoreRun,
  demoDeleteRun,
  demoGetRunLogs,
  demoDashboardStats,
  demoRecentRuns,
} from "@/mocks/handlers";
import type { ListQuery, Page } from "@/types/api";
import type { Run, RunSummary, RunRequest, DashboardStats, RecentRunActivity } from "@/types/run";

export async function listRuns(query: ListQuery = {}): Promise<Page<RunSummary>> {
  if (isDemoMode()) return demoListRuns(query);
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v != null) params.set(k, String(v));
  const qs = params.toString();
  return apiRequest<Page<RunSummary>>(`/runs${qs ? `?${qs}` : ""}`);
}

export async function getRun(runId: string): Promise<Run> {
  if (isDemoMode()) return demoGetRun(runId);
  return apiRequest<Run>(`/runs/${encodeURIComponent(runId)}`);
}

export async function createRun(request: RunRequest): Promise<Run> {
  if (isDemoMode()) return demoCreateRun(request);
  return apiRequest<Run>("/runs", { method: "POST", body: JSON.stringify(request) });
}

export async function cancelRun(runId: string): Promise<Run> {
  if (isDemoMode()) return demoCancelRun(runId);
  return apiRequest<Run>(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
}

export async function restoreRun(runId: string): Promise<Run> {
  if (isDemoMode()) return demoRestoreRun(runId);
  return apiRequest<Run>(`/runs/${encodeURIComponent(runId)}/restore`, { method: "POST" });
}

export async function deleteRun(runId: string): Promise<{ deleted: boolean; id?: string }> {
  if (isDemoMode()) return demoDeleteRun(runId);
  return apiRequest<{ deleted: boolean; id?: string }>(`/runs/${encodeURIComponent(runId)}`, {
    method: "DELETE",
  });
}

export async function getRunLogs(runId: string): Promise<string[]> {
  if (isDemoMode()) return demoGetRunLogs(runId);
  return apiRequest<string[]>(`/runs/${encodeURIComponent(runId)}/logs`);
}

export async function getDashboardStats(): Promise<DashboardStats> {
  if (isDemoMode()) return demoDashboardStats();
  return apiRequest<DashboardStats>("/stats");
}

export async function getRecentRuns(): Promise<RecentRunActivity[]> {
  if (isDemoMode()) return demoRecentRuns();
  return apiRequest<RecentRunActivity[]>("/runs/recent");
}
