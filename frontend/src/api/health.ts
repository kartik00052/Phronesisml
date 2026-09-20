import { apiRequest, ApiError } from "./client";
import { isDemoMode } from "@/mocks";
import { demoHealth, demoCapabilities } from "@/mocks/handlers";
import type { HealthReport, CapabilitiesReport } from "@/types/health";

export async function getHealth(): Promise<HealthReport> {
  if (isDemoMode()) return demoHealth();
  return apiRequest<HealthReport>("/health");
}

export async function getCapabilities(): Promise<CapabilitiesReport> {
  if (isDemoMode()) return demoCapabilities();
  return apiRequest<CapabilitiesReport>("/capabilities").catch((err) => {
    if (err instanceof ApiError && err.kind === "NotFound") {
      // Real backend before the endpoint existed.
      return {
        name: "PhronesisML",
        version: "unknown",
        offline: true,
        deterministic: false,
        task_types: [],
        engines: [],
        explainers: [],
        pipeline_stages: [],
        sdk_methods: [],
        cli_commands: [],
        extras: [],
      } satisfies CapabilitiesReport;
    }
    throw err;
  });
}