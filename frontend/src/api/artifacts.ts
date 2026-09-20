import { apiRequest } from "./client";
import { isDemoMode } from "@/mocks";
import { demoArtifacts, demoArtifactContent } from "@/mocks/handlers";
import type { ArtifactContent, ArtifactManifest } from "@/types/artifact";

export async function listArtifacts(runId: string): Promise<ArtifactManifest> {
  if (isDemoMode()) return demoArtifacts(runId);
  return apiRequest<ArtifactManifest>(`/runs/${encodeURIComponent(runId)}/artifacts`);
}

/** Dereference a single artifact's content for preview / download. */
export async function getArtifactContent(runId: string, name: string): Promise<ArtifactContent> {
  if (isDemoMode()) return demoArtifactContent(runId, name);
  return apiRequest<ArtifactContent>(
    `/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(name)}/content`,
  );
}