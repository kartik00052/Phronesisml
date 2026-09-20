import * as React from "react";
import { PieChart } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { RunPicker } from "@/components/run/run-picker";
import { RunExplainabilityView } from "@/components/run/run-explainability";
import { Card, CardContent } from "@/components/ui/card";

export default function ExplainabilityPage() {
  const [runId, setRunId] = React.useState("");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Explainability"
        description="SHAP-based feature attributions and insight summaries for every model."
      >
        <RunPicker value={runId} onChange={setRunId} showStatus />
      </PageHeader>

      {runId ? (
        <RunExplainabilityView runId={runId} />
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <PieChart className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Select a completed run to inspect its explanations.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
