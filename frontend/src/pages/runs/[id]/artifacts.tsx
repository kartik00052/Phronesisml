import { useOutletContext } from "react-router-dom";

import { RunArtifactsView } from "@/components/run/run-artifacts";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunArtifactsTab() {
  const { run } = useOutletContext<RunOutletContext>();
  return <RunArtifactsView runId={run.id} />;
}
