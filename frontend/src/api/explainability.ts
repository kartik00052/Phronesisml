import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import { demoExplainability } from "@/mocks/handlers";
import type { ExplainabilityView } from "@/types/explainability";

export async function getExplainability(runId: string): Promise<ExplainabilityView | null> {
  if (isDemoMode()) return demoExplainability(runId);
  return apiRequest<ExplainabilityView | null>(
    `/runs/${encodeURIComponent(runId)}/explainability`,
  );
}