import { useOutletContext } from "react-router-dom";

import { RunDataView } from "@/components/run/run-data";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunDataTab() {
  const { run } = useOutletContext<RunOutletContext>();
  return <RunDataView runId={run.id} />;
}
