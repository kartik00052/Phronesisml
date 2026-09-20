import { useOutletContext } from "react-router-dom";

import { RunReportView } from "@/components/run/run-report";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunReportsTab() {
  const { run } = useOutletContext<RunOutletContext>();
  return <RunReportView runId={run.id} />;
}
