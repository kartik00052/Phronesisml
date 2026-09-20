import { useOutletContext } from "react-router-dom";

import { LogViewer } from "@/components/run/log-viewer";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunLogsTab() {
  const { logs, live } = useOutletContext<RunOutletContext>();
  return <LogViewer logs={logs} live={live} height={560} />;
}
