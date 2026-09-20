import { useController, useFormContext } from "react-hook-form";
import { useState } from "react";
import { Cpu, HardDrive, Rows3, Sparkles, Upload } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { UploadDatasetDialog } from "@/components/datasets/upload-dataset-dialog";
import type { WizardValues } from "@/components/new-run/form";
import { useDatasets } from "@/hooks/use-datasets";
import { ENGINE_LABELS } from "@/config/status";
import { formatBytes, formatNumber } from "@/lib/format";
import type { DatasetSummary } from "@/types/dataset";

function DatasetOptionCard({
  dataset,
  checked,
  onSelect,
}: {
  dataset: DatasetSummary;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={
        "flex w-full flex-col gap-2 rounded-md border p-3 text-left transition-colors " +
        (checked
          ? "border-ring bg-primary/5 ring-1 ring-ring"
          : "border-border bg-surface hover:border-border-strong hover:bg-surface-muted")
      }
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{dataset.name}</p>
          <p className="truncate font-mono text-xs text-muted-foreground">{dataset.path}</p>
        </div>
        <Badge variant={dataset.validationPassed ? "success" : "warning"}>
          {dataset.validationPassed ? "Valid" : "Warnings"}
        </Badge>
        {dataset.sample && (
          <Badge variant="secondary" className="gap-1">
            <Sparkles className="size-3" />
            Sample
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Rows3 className="size-3.5" />
          {formatNumber(dataset.rows)} × {formatNumber(dataset.columns)}
        </span>
        <span className="flex items-center gap-1">
          <HardDrive className="size-3.5" />
          {formatBytes(dataset.sizeBytes)}
        </span>
        <span className="flex items-center gap-1">
          <Cpu className="size-3.5" />
          {ENGINE_LABELS[dataset.engine] ?? dataset.engine}
        </span>
      </div>
    </button>
  );
}

export function DataSourceStep() {
  const { control, watch } = useFormContext<WizardValues>();
  const datasetController = useController({ control, name: "datasetId" });

  const { data: datasets, isLoading } = useDatasets({ pageSize: 50 });
  const selectedId = watch("datasetId");
  const [uploadOpen, setUploadOpen] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Label className="text-sm">Source dataset</Label>
          {selectedId && <Badge variant="secondary">Selected</Badge>}
        </div>
      </div>
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : datasets && datasets.items.length > 0 ? (
        <>
          <div className="grid gap-2 sm:grid-cols-2">
            {datasets.items.map((d) => (
              <DatasetOptionCard
                key={d.id}
                dataset={d}
                checked={d.id === selectedId}
                onSelect={() => datasetController.field.onChange(d.id)}
              />
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Don&apos;t see your file?{" "}
            <Button
              variant="link"
              className="h-auto p-0 gap-1 text-xs"
              onClick={() => setUploadOpen(true)}
            >
              <Upload className="size-3" /> Upload a dataset now
            </Button>
          </div>
        </>
      ) : (
        <div className="space-y-3">
          <Alert variant="warning">
            No datasets registered yet. Upload one to start an experiment.
          </Alert>
          <Button variant="outline" className="gap-1.5" onClick={() => setUploadOpen(true)}>
            <Upload className="size-4" />
            Upload dataset
          </Button>
        </div>
      )}
      <UploadDatasetDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={(id) => datasetController.field.onChange(id)}
      />
    </div>
  );
}
