import { useOutletContext } from "react-router-dom";

import { RunModelsView } from "@/components/run/run-models";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunModelsTab() {
  const { run } = useOutletContext<RunOutletContext>();
  return <RunModelsView runId={run.id} taskType={run.summary.taskType} />;
}
