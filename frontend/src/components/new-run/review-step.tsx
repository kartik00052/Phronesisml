import { useFormContext } from "react-hook-form";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { STAGE_META, STAGE_SLICES } from "@/config/pipeline";
import { ENGINE_LABELS } from "@/config/status";
import { NULL_STRATEGY_META, RUN_MODE_META, type WizardValues } from "@/components/new-run/form";
import { formatBytes, formatNumber } from "@/lib/format";
import type { DatasetSummary } from "@/types/dataset";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium text-foreground">{value ?? "—"}</dd>
    </div>
  );
}

export function ReviewStep({
  dataset,
  resolvedEngine,
}: {
  dataset?: DatasetSummary;
  resolvedEngine: string;
}) {
  const { watch } = useFormContext<WizardValues>();
  const values = watch();

  const depth = STAGE_SLICES.find((s) => s.key === values.pipelineDepth);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Data source</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="divide-y divide-border">
            <Row label="Dataset" value={dataset?.name} />
            <Row label="Shape" value={dataset ? `${formatNumber(dataset.rows)} × ${formatNumber(dataset.columns)}` : undefined} />
            <Row label="Size" value={dataset ? formatBytes(dataset.sizeBytes) : undefined} />
            <Row
              label="Engine"
              value={
                <span className="flex items-center justify-end gap-2">
                  {values.engine === "auto" ? (
                    <>
                      Auto
                      {resolvedEngine && <Badge variant="info">→ {resolvedEngine}</Badge>}
                    </>
                  ) : (
                    ENGINE_LABELS[values.engine]
                  )}
                </span>
              }
            />
            <Row label="Null strategy" value={NULL_STRATEGY_META[values.nullStrategy].label} />
            <Row label="Target" value={values.targetOverride.trim() || <span className="text-muted-foreground">auto-detect</span>} />
            <Row label="Task" value={values.taskOverride.trim() || "auto-detect"} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="divide-y divide-border">
            <Row label="Depth" value={depth ? `${depth.label} — ${depth.api}` : undefined} />
            <Row label="Stages" value={depth ? depth.stages.length : 0} />
            <Row label="Mode" value={<span className="capitalize">{RUN_MODE_META[values.mode].label}</span>} />
            <Row label="CV folds" value={values.cv} />
            <Row label="Max trials" value={values.maxTrials || "mode default"} />
          </dl>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Stages to execute</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1.5">
            {depth?.stages.map((s) => (
              <Badge key={s} variant="outline" className="font-medium">
                {STAGE_META[s].label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}