import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import { demoReport } from "@/mocks/handlers";
import type { ReportFormat, ReportInfo } from "@/types/report";

export async function getReport(runId: string, format: ReportFormat = "markdown"): Promise<ReportInfo> {
  if (isDemoMode()) return demoReport(runId, format);
  return apiRequest<ReportInfo>(
    `/runs/${encodeURIComponent(runId)}/report?format=${format}`,
  );
}