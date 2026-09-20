import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import { demoPipelineOverview, demoPipelineStages, demoPipelineProgress } from "@/mocks/handlers";
import type { PipelineOverview, PipelineProgress, StageDetail } from "@/types/pipeline";

export async function getPipelineOverview(runId: string): Promise<PipelineOverview> {
  if (isDemoMode()) return demoPipelineOverview(runId);
  return apiRequest<PipelineOverview>(`/runs/${encodeURIComponent(runId)}/pipeline`);
}

export async function getPipelineStages(runId: string): Promise<StageDetail[]> {
  if (isDemoMode()) return demoPipelineStages(runId);
  return apiRequest<StageDetail[]>(`/runs/${encodeURIComponent(runId)}/pipeline/stages`);
}

export async function getPipelineProgress(runId: string): Promise<PipelineProgress> {
  if (isDemoMode()) return demoPipelineProgress(runId);
  return apiRequest<PipelineProgress>(`/runs/${encodeURIComponent(runId)}/pipeline/progress`);
}