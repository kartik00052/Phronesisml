import { useQuery } from "@tanstack/react-query";

import { getModelDetail, listModels } from "@/api/models";
import { getExplainability } from "@/api/explainability";
import { getReport } from "@/api/reports";
import { getArtifactContent, listArtifacts } from "@/api/artifacts";

export const queryKeys = {
  models: (runId: string) => ["models", runId] as const,
  modelDetail: (runId: string, modelType: string) => ["models", runId, modelType] as const,
  explainability: (runId: string) => ["explainability", runId] as const,
  report: (runId: string, format: string) => ["reports", runId, format] as const,
  artifacts: (runId: string) => ["artifacts", runId] as const,
  artifactContent: (runId: string, name: string) => ["artifacts", runId, name] as const,
};

export function useModels(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.models(runId ?? ""),
    queryFn: () => listModels(runId!),
    enabled: !!runId,
  });
}

export function useModelDetail(runId: string | undefined, modelType: string | null) {
  return useQuery({
    queryKey: queryKeys.modelDetail(runId ?? "", modelType ?? ""),
    queryFn: () => getModelDetail(runId!, modelType!),
    enabled: !!runId && !!modelType,
  });
}

export function useExplainability(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.explainability(runId ?? ""),
    queryFn: () => getExplainability(runId!),
    enabled: !!runId,
  });
}

export function useReport(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.report(runId ?? "", "markdown"),
    queryFn: () => getReport(runId!, "markdown"),
    enabled: !!runId,
  });
}

export function useArtifacts(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.artifacts(runId ?? ""),
    queryFn: () => listArtifacts(runId!),
    enabled: !!runId,
  });
}

export function useArtifactContent(runId: string | undefined, name: string | null) {
  return useQuery({
    queryKey: queryKeys.artifactContent(runId ?? "", name ?? ""),
    queryFn: () => getArtifactContent(runId!, name!),
    enabled: !!runId && !!name,
  });
}