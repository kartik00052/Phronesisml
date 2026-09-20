import { useOutletContext } from "react-router-dom";

import { RunOverview } from "@/components/run/run-overview";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunOverviewTab() {
  const { run, stages } = useOutletContext<RunOutletContext>();
  return <RunOverview run={run} stages={stages} />;
}
