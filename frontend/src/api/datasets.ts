import { apiRequest, uploadFile } from "./client";
import { isDemoMode } from "@/mocks";
import {
  demoListDatasets,
  demoGetDataset,
  demoGetRunDataset,
  demoRecommendEngine,
  demoUploadDataset,
  demoDeleteDataset,
} from "@/mocks/handlers";
import type { ListQuery, Page } from "@/types/api";
import type {
  Dataset,
  DatasetSummary,
  DatasetUploadResult,
  EngineRecommendation,
} from "@/types/dataset";

export async function listDatasets(query: ListQuery = {}): Promise<Page<DatasetSummary>> {
  if (isDemoMode()) return demoListDatasets(query);
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v != null) params.set(k, String(v));
  const qs = params.toString();
  return apiRequest<Page<DatasetSummary>>(`/datasets${qs ? `?${qs}` : ""}`);
}

export async function getDataset(id: string): Promise<Dataset> {
  if (isDemoMode()) return demoGetDataset(id);
  return apiRequest<Dataset>(`/datasets/${encodeURIComponent(id)}`);
}

export async function getRunDataset(runId: string): Promise<Dataset | null> {
  if (isDemoMode()) return demoGetRunDataset(runId);
  return apiRequest<Dataset | null>(`/runs/${encodeURIComponent(runId)}/dataset`);
}

export async function uploadDataset(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DatasetUploadResult> {
  if (isDemoMode()) return demoUploadDataset(file, onProgress);
  return uploadFile<DatasetUploadResult>("/datasets", file, onProgress);
}

export async function deleteDataset(id: string): Promise<{ deleted: boolean; id?: string }> {
  if (isDemoMode()) return demoDeleteDataset(id);
  return apiRequest<{ deleted: boolean; id?: string }>(`/datasets/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function recommendEngine(input: {
  bytes: number;
  rows?: number;
  cols?: number;
}): Promise<EngineRecommendation> {
  if (isDemoMode()) return demoRecommendEngine(input);
  return apiRequest<EngineRecommendation>("/engine/recommend", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
