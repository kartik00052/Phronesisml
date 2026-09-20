import { useOutletContext } from "react-router-dom";

import { RunExplainabilityView } from "@/components/run/run-explainability";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunExplainabilityTab() {
  const { run } = useOutletContext<RunOutletContext>();
  return <RunExplainabilityView runId={run.id} />;
}
