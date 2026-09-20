import * as React from "react";
import { BrainCircuit, Trophy } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { EvaluationCharts } from "@/components/charts/evaluation-charts";
import { useModelDetail, useModels } from "@/hooks/use-run-extras";
import { metricDescriptorsFor, metricValue } from "@/config/metrics";
import { formatDuration, formatScore, formatNumber } from "@/lib/format";
import type { ModelRankingRow } from "@/types/model";

export function RunModelsView({ runId, taskType }: { runId: string; taskType: string }) {
  const [selected, setSelected] = React.useState<string | null>(null);
  const { data: rows, isLoading, isError, error } = useModels(runId);
  const detail = useModelDetail(runId, selected);
  const descriptors = metricDescriptorsFor(taskType);

  const columns = React.useMemo<ColumnDef<ModelRankingRow, unknown>[]>(() => {
    const cols: ColumnDef<ModelRankingRow, unknown>[] = [
      {
        id: "rank",
        accessorKey: "rank",
        header: "#",
        cell: ({ row }) => (
          <span className="tabular-nums text-muted-foreground">{row.original.rank}</span>
        ),
        enableGlobalFilter: false,
      },
      {
        id: "model",
        accessorKey: "model_type",
        header: "Model",
        cell: ({ row }) => (
          <span className="inline-flex items-center gap-2 font-medium">
            {row.original.model_type}
            {row.original.best && <Badge variant="success">Best</Badge>}
            {row.original.status === "running" && <Badge variant="info">Training</Badge>}
            {row.original.status === "failed" && <Badge variant="danger">Failed</Badge>}
          </span>
        ),
      },
    ];
    for (const d of descriptors) {
      cols.push({
        id: d.key,
        header: d.label,
        enableGlobalFilter: false,
        accessorFn: (row) =>
          metricValue({ ...row.secondary_metrics, [descriptors[0].key]: row.primary_score }, d.key) ??
          Number.NEGATIVE_INFINITY,
        cell: ({ row }) => (
          <span className="tabular-nums">
            {formatScore(
              metricValue(
                { ...row.original.secondary_metrics, [descriptors[0].key]: row.original.primary_score },
                d.key,
              ),
              d.precision ?? 3,
            )}
          </span>
        ),
      });
    }
    cols.push(
      {
        id: "trials",
        accessorKey: "trials_used",
        header: "Trials",
        enableGlobalFilter: false,
        cell: ({ row }) => (
          <span className="tabular-nums text-muted-foreground">
            {formatNumber(row.original.trials_used)}
          </span>
        ),
      },
      {
        id: "time",
        accessorKey: "time_elapsed",
        header: "Time",
        enableGlobalFilter: false,
        cell: ({ row }) => (
          <span className="tabular-nums text-muted-foreground">
            {formatDuration(row.original.time_elapsed)}
          </span>
        ),
      },
    );
    return cols;
  }, [descriptors]);

  const best = rows?.find((r) => r.best);

  if (isError) {
    return (
      <EmptyState
        icon={<BrainCircuit className="size-6" />}
        title="Could not load models"
        description={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }

  return (
    <div className="space-y-4">
      {best && (
        <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/5 px-4 py-3">
          <Trophy className="size-4 text-warning" />
          <p className="text-sm">
            Best model: <span className="font-semibold text-success">{best.model_type}</span>{" "}
            <span className="text-muted-foreground">
              · {formatScore(best.primary_score)} {descriptors[0]?.label.toLowerCase()}
            </span>
          </p>
        </div>
      )}

      <DataTable
        columns={columns}
        data={rows ?? []}
        loading={isLoading}
        searchPlaceholder="Search models…"
        emptyMessage="No models yet"
        emptyHint="The leaderboard populates as candidates finish training."
        getRowId={(r) => r.model_type}
        onRowClick={(r) => setSelected(r.model_type)}
        initialSorting={[{ id: "rank", desc: false }]}
        pageSize={12}
      />

      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-2xl">
          <SheetHeader className="border-b border-border px-4 py-3">
            <SheetTitle className="text-sm">{selected} · model detail</SheetTitle>
          </SheetHeader>
          <div className="space-y-4 p-4">
            {detail.isLoading && <Skeleton className="h-48 w-full" />}
            {detail.data && (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Metric label="Score" value={formatScore(detail.data.score)} />
                  <Metric label="Rank" value={`#${detail.data.rank}`} />
                  <Metric label="Trials" value={formatNumber(detail.data.trials_used)} />
                  <Metric label="Features" value={formatNumber(detail.data.nFeatures)} />
                </div>
                {detail.data.evaluation && (
                  <EvaluationCharts evaluation={detail.data.evaluation} />
                )}
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Best params
                  </p>
                  <pre className="overflow-x-auto rounded-md border border-border bg-background p-3 font-mono text-xs scrollbar-thin">
                    {JSON.stringify(detail.data.best_params, null, 2)}
                  </pre>
                </div>
              </>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}
