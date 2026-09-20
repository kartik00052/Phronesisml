import * as React from "react";
import { useOutletContext } from "react-router-dom";

import { PipelineView } from "@/components/run/pipeline-view";
import { usePipelineOverview } from "@/hooks/use-pipeline";
import type { RunOutletContext } from "@/components/run/run-context";

export default function RunPipelineTab() {
  const { run, stages, live } = useOutletContext<RunOutletContext>();
  const { data: overview } = usePipelineOverview(run.id, live);
  const [selectedStage, setSelectedStage] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (selectedStage || stages.length === 0) return;
    const current = stages.find((s) => s.status === "running" || s.status === "queued") ?? stages[0];
    if (current) setSelectedStage(current.id);
  }, [stages, selectedStage]);

  return (
    <PipelineView
      stages={stages}
      selectedId={selectedStage}
      onSelect={setSelectedStage}
      overview={overview}
    />
  );
}
