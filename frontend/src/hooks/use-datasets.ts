import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteDataset,
  getDataset,
  getRunDataset,
  listDatasets,
  recommendEngine,
  uploadDataset,
} from "@/api/datasets";
import type { ListQuery } from "@/types/api";

export const queryKeys = {
  datasets: (query: ListQuery = {}) => ["datasets", query] as const,
  dataset: (id: string) => ["datasets", id] as const,
  runDataset: (runId: string) => ["datasets", "run", runId] as const,
  engineRecommendation: (input: { bytes: number; rows?: number; cols?: number }) =>
    ["engine", "recommend", input] as const,
};

export function useDatasets(query: ListQuery = {}) {
  return useQuery({
    queryKey: queryKeys.datasets(query),
    queryFn: () => listDatasets(query),
  });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.dataset(id ?? ""),
    queryFn: () => getDataset(id!),
    enabled: !!id,
  });
}

export function useRunDataset(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.runDataset(runId ?? ""),
    queryFn: () => getRunDataset(runId!),
    enabled: !!runId,
  });
}

export function useEngineRecommendation(
  input: { bytes: number; rows?: number; cols?: number } | null,
) {
  return useQuery({
    queryKey: queryKeys.engineRecommendation(input ?? { bytes: -1 }),
    queryFn: () => recommendEngine(input!),
    enabled: !!input && input.bytes > 0,
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (p: number) => void }) =>
      uploadDataset(file, onProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDataset(id),
    onSuccess: (_res, id) => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dataset(id) });
    },
  });
}
