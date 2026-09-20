import { useController, useFormContext } from "react-hook-form";
import { Cpu } from "lucide-react";

import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useDatasets, useEngineRecommendation } from "@/hooks/use-datasets";
import { NULL_STRATEGY_META, type WizardValues } from "@/components/new-run/form";
import { ENGINE_LABELS } from "@/config/status";

export function EngineStep() {
  const { control, watch } = useFormContext<WizardValues>();
  const engineController = useController({ control, name: "engine" });
  const nullController = useController({ control, name: "nullStrategy" });

  const { data: datasets } = useDatasets({ pageSize: 50 });
  const selectedId = watch("datasetId");
  const selectedDataset = datasets?.items.find((d) => d.id === selectedId);

  const recommendation = useEngineRecommendation(
    selectedDataset
      ? { bytes: selectedDataset.sizeBytes, rows: selectedDataset.rows, cols: selectedDataset.columns }
      : null,
  );

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm">Compute engine</Label>
          {selectedDataset && (
            <span className="text-xs text-muted-foreground">{selectedDataset.name}</span>
          )}
        </div>
        <RadioGroup
          value={engineController.field.value}
          onValueChange={engineController.field.onChange}
          className="gap-2"
        >
          {(["auto", "pandas", "polars", "spark"] as const).map((engine) => (
            <label
              key={engine}
              className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                engineController.field.value === engine
                  ? "border-ring bg-primary/5 ring-1 ring-ring"
                  : "border-border bg-surface hover:border-border-strong"
              }`}
            >
              <RadioGroupItem value={engine} id={`engine-${engine}`} className="mt-0.5" />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">
                  {engine === "auto" ? "Auto (recommended)" : ENGINE_LABELS[engine]}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {engine === "auto"
                    ? "Select the best engine for this dataset size."
                    : `Force ${ENGINE_LABELS[engine]} for every stage.`}
                </span>
              </span>
            </label>
          ))}
        </RadioGroup>
        {selectedDataset && engineController.field.value === "auto" && (
          <div className="flex items-start gap-2 rounded-md border border-info/30 bg-info/5 p-3 text-sm">
            <Cpu className="mt-0.5 size-4 shrink-0 text-info" />
            <div>
              <p className="font-medium text-foreground">
                {recommendation.data?.engine
                  ? `Recommended: ${ENGINE_LABELS[recommendation.data.engine]}`
                  : "Computing recommendation…"}
              </p>
              <p className="text-xs text-muted-foreground">
                {recommendation.data?.reason ?? "Based on dataset size and row count."}
              </p>
              {recommendation.data && (
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {recommendation.data.routing.n_rows.toLocaleString()} rows ·{" "}
                  {recommendation.data.routing.n_cols} cols ·{" "}
                  {recommendation.data.routing.memory_bytes.toLocaleString()} bytes in memory
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <Label className="text-sm">Missing value strategy</Label>
        <RadioGroup
          value={nullController.field.value}
          onValueChange={nullController.field.onChange}
          className="gap-2"
        >
          {(Object.keys(NULL_STRATEGY_META) as (keyof typeof NULL_STRATEGY_META)[]).map((key) => (
            <label
              key={key}
              className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                nullController.field.value === key
                  ? "border-ring bg-primary/5 ring-1 ring-ring"
                  : "border-border bg-surface hover:border-border-strong"
              }`}
            >
              <RadioGroupItem value={key} id={`null-${key}`} className="mt-0.5" />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{NULL_STRATEGY_META[key].label}</span>
                <span className="block text-xs text-muted-foreground">{NULL_STRATEGY_META[key].description}</span>
              </span>
            </label>
          ))}
        </RadioGroup>
      </div>
    </div>
  );
}