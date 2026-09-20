import { useController, useFormContext } from "react-hook-form";
import { Crosshair, Sparkles } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { WizardValues } from "@/components/new-run/form";
import { useDatasets } from "@/hooks/use-datasets";
import { TASK_LABELS } from "@/config/status";
import type { TaskType } from "@/types/run";

const TASK_OPTIONS: TaskType[] = [
  "classification",
  "regression",
  "clustering",
  "anomaly_detection",
  "ambiguous",
  "analytics",
  "unknown",
];

/**
 * Target & task configuration. Defaults to the agent's auto-detection; the
 * detection agent still runs unless a target column is explicitly set here.
 */
export function TargetTaskStep() {
  const { control, watch } = useFormContext<WizardValues>();
  const targetController = useController({ control, name: "targetOverride" });
  const taskController = useController({ control, name: "taskOverride" });

  const { data: datasets } = useDatasets({ pageSize: 50 });
  const selectedId = watch("datasetId");
  const dataset = datasets?.items.find((d) => d.id === selectedId);

  const detectedTarget = dataset?.targetColumn ?? null;
  const detectedTask = dataset?.taskType ? (dataset.taskType as TaskType) : null;

  const overrideActive = targetController.field.value.trim().length > 0;

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm">Prediction target</Label>
          <span className="text-xs text-muted-foreground">Leave blank to auto-detect</span>
        </div>

        {dataset ? (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface px-3 py-2.5 text-sm">
            <Crosshair className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">Last detected:</span>
            <Badge variant="outline" className="font-mono">
              {detectedTarget ?? "no target yet"}
            </Badge>
            {detectedTask && (
              <Badge variant="secondary">{TASK_LABELS[detectedTask] ?? detectedTask}</Badge>
            )}
            <span className="ml-auto hidden text-xs text-muted-foreground sm:inline">
              The detection agent re-runs on the selected dataset.
            </span>
          </div>
        ) : (
          <Alert variant="warning">Select a dataset on the previous step first.</Alert>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="targetOverride" className="text-xs text-muted-foreground">
              Target column (optional)
            </Label>
            <Input
              id="targetOverride"
              value={targetController.field.value ?? ""}
              onChange={(e) => targetController.field.onChange(e.target.value)}
              placeholder={detectedTarget ?? "Auto-detect"}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Fix the label column explicitly. Overrides the agent's detection.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="taskOverride" className="text-xs text-muted-foreground">
              Task type (optional)
            </Label>
            <Select
              value={taskController.field.value || ""}
              onValueChange={(v) => taskController.field.onChange(v)}
            >
              <SelectTrigger id="taskOverride" className="text-sm">
                <SelectValue placeholder="Auto-detect" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Auto-detect</SelectItem>
                {TASK_OPTIONS.filter((t) => t !== "unknown").map((t) => (
                  <SelectItem key={t} value={t}>
                    {TASK_LABELS[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Pin the problem type when auto-detection is likely to be ambiguous.
            </p>
          </div>
        </div>
      </section>

      {overrideActive && (
        <div className="flex items-start gap-2 rounded-md border border-info/30 bg-info/5 p-3 text-sm">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-info" />
          <p className="text-muted-foreground">
            A target override is set. The pipeline will skip{" "}
            <span className="font-medium text-foreground">target detection</span> and use{" "}
            <span className="font-mono text-foreground">{targetController.field.value}</span> as the
            label column.
          </p>
        </div>
      )}
    </div>
  );
}