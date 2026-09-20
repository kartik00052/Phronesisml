import * as React from "react";
import { FileText } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { RunPicker } from "@/components/run/run-picker";
import { RunReportView } from "@/components/run/run-report";
import { Card, CardContent } from "@/components/ui/card";

export default function ReportsPage() {
  const [runId, setRunId] = React.useState("");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Markdown experiment reports generated after each completed run."
      >
        <RunPicker value={runId} onChange={setRunId} showStatus />
      </PageHeader>

      {runId ? (
        <RunReportView runId={runId} />
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <FileText className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Select a completed run to preview its report.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
