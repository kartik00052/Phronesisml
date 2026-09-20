import { Terminal, Timer } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StageStatusBadge } from "@/components/ui/status-badge";
import { STAGE_META } from "@/config/pipeline";
import { formatDateTime, formatDurationMs } from "@/lib/format";
import type { StageDetail } from "@/types/pipeline";

function SummaryRow({ label, value }: { label: string; value: unknown }) {
  if (value == null || value === "" || value === false) return null;
  let display: string;
  if (typeof value === "number") display = String(Math.round(value * 1000) / 1000);
  else if (typeof value === "object") display = JSON.stringify(value);
  else display = String(value);
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate font-medium text-foreground" title={display}>
        {display}
      </dd>
    </div>
  );
}

export function StageDetailPanel({
  stage,
  active,
}: {
  stage: StageDetail;
  active: boolean;
}) {
  const meta = STAGE_META[stage.id as keyof typeof STAGE_META];
  const summary = stage.summary ?? {};
  const entries = Object.entries(summary);

  if (!active) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
          Select a stage in the pipeline to inspect its outputs.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0 pb-3">
        <div>
          <CardTitle className="text-base">{meta?.label ?? stage.name}</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">{meta?.description ?? stage.id}</p>
        </div>
        <StageStatusBadge status={stage.status} />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Timer className="size-3.5" />
            {formatDurationMs(stage.durationMs)}
          </span>
          {stage.startedAt && <span>Started {formatDateTime(stage.startedAt)}</span>}
          {stage.completedAt && <span>Finished {formatDateTime(stage.completedAt)}</span>}
        </div>

        {stage.error && (
          <div className="rounded-md border border-danger/30 bg-danger/5 p-3">
            <p className="text-sm font-medium text-danger">{stage.error.message}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{stage.error.type}</p>
          </div>
        )}

        <Separator />

        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Summary
          </p>
          {entries.length > 0 ? (
            <dl className="divide-y divide-border">{entries.map(([k, v]) => <SummaryRow key={k} label={k} value={v} />)}</dl>
          ) : (
            <p className="text-sm text-muted-foreground">No summary captured yet.</p>
          )}
        </div>

        {stage.logs.length > 0 && (
          <>
            <Separator />
            <div>
              <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Terminal className="size-3.5" />
                Stage logs
              </p>
              <div className="max-h-48 space-y-1 overflow-y-auto rounded-md bg-background p-3 font-mono text-xs leading-relaxed scrollbar-thin">
                {stage.logs.map((line, i) => (
                  <p key={i} className="whitespace-pre-wrap text-muted-foreground">
                    {line}
                  </p>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}