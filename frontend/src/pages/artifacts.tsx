import * as React from "react";
import { Archive } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { RunPicker } from "@/components/run/run-picker";
import { RunArtifactsView } from "@/components/run/run-artifacts";
import { Card, CardContent } from "@/components/ui/card";

export default function ArtifactsPage() {
  const [runId, setRunId] = React.useState("");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Artifacts"
        description="Model binaries, encodings, SHAP outputs, and reports produced by runs."
      >
        <RunPicker value={runId} onChange={setRunId} showStatus />
      </PageHeader>

      {runId ? (
        <RunArtifactsView runId={runId} />
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <Archive className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Select a run to inspect its artifact manifest.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
