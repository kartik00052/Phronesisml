import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import { demoListModels, demoGetModelDetail } from "@/mocks/handlers";
import type { ModelDetail, ModelRankingRow } from "@/types/model";

export async function listModels(runId: string): Promise<ModelRankingRow[]> {
  if (isDemoMode()) return demoListModels(runId);
  return apiRequest<ModelRankingRow[]>(`/runs/${encodeURIComponent(runId)}/models`);
}

export async function getModelDetail(runId: string, modelType: string): Promise<ModelDetail> {
  if (isDemoMode()) return demoGetModelDetail(runId, modelType);
  return apiRequest<ModelDetail>(
    `/runs/${encodeURIComponent(runId)}/models/${encodeURIComponent(modelType)}`,
  );
}