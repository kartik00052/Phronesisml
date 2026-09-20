import * as React from "react";
import { BarChart3, Database, GitCompareArrows, ShieldCheck, Table2 } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { CategoryBarChart } from "@/components/charts/distribution";
import { CorrelationHeatmap, type CorrelationMatrix } from "@/components/charts/correlation-heatmap";
import { ChartCard } from "@/components/charts/chart-card";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRunDataset } from "@/hooks/use-datasets";
import { formatBytes, formatNumber } from "@/lib/format";
import type { ColumnInfo, Dataset, NumericColumnSummary } from "@/types/dataset";

function nullTone(pct: number) {
  if (pct === 0) return "text-muted-foreground";
  if (pct < 5) return "text-warning";
  return "text-danger";
}

const columnDefs: ColumnDef<ColumnInfo, unknown>[] = [
  {
    id: "name",
    accessorKey: "name",
    header: "Column",
    cell: ({ row }) => <span className="font-mono text-xs font-medium">{row.original.name}</span>,
  },
  {
    id: "dtype",
    accessorKey: "dtype",
    header: "Dtype",
    cell: ({ row }) => (
      <Badge variant="outline" className="font-mono text-[10px]">
        {row.original.dtype}
      </Badge>
    ),
  },
  {
    id: "kind",
    header: "Kind",
    enableGlobalFilter: false,
    accessorFn: (c) => (c.numeric ? "numeric" : c.categorical ? "categorical" : "other"),
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.numeric ? "numeric" : row.original.categorical ? "categorical" : "other"}
      </span>
    ),
  },
  {
    id: "nulls",
    header: "Missing",
    enableGlobalFilter: false,
    accessorFn: (c) => c.nullPercent,
    cell: ({ row }) => (
      <span className={`tabular-nums ${nullTone(row.original.nullPercent)}`}>
        {row.original.nullCount > 0 ? `${row.original.nullPercent.toFixed(1)}%` : "0%"}
      </span>
    ),
  },
  {
    id: "cardinality",
    header: "Cardinality",
    enableGlobalFilter: false,
    accessorFn: (c) => c.cardinality ?? 0,
    cell: ({ row }) => (
      <span className="tabular-nums text-muted-foreground">
        {row.original.cardinality != null ? formatNumber(row.original.cardinality) : "—"}
      </span>
    ),
  },
  {
    id: "range",
    header: "Range / Top",
    enableGlobalFilter: false,
    cell: ({ row }) => {
      const c = row.original;
      if (c.stats) {
        return (
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            {c.stats.min} … {c.stats.max}
          </span>
        );
      }
      const top = c.topValues ? Object.keys(c.topValues).slice(0, 3).join(", ") : "—";
      return <span className="text-xs text-muted-foreground">{top}</span>;
    },
  },
];

function RangeBar({ stats }: { stats: NumericColumnSummary }) {
  const min = stats.min;
  const max = stats.max;
  const span = max - min || 1;
  const pct = (v: number) => ((v - min) / span) * 100;
  const q1 = Number(stats["25%"]);
  const med = Number(stats["50%"]);
  const q3 = Number(stats["75%"]);
  return (
    <div className="space-y-1">
      <div className="relative h-2.5 rounded-full bg-muted">
        <div
          className="absolute h-full rounded-full bg-info/40"
          style={{ left: `${pct(q1)}%`, width: `${Math.max(2, pct(q3) - pct(q1))}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-foreground"
          style={{ left: `${pct(med)}%` }}
        />
      </div>
      <div className="flex justify-between font-mono text-[10px] tabular-nums text-muted-foreground">
        <span>{min}</span>
        <span className="text-foreground">median {med}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

function pearson(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n < 3) return 0;
  const ma = a.slice(0, n).reduce((s, v) => s + v, 0) / n;
  const mb = b.slice(0, n).reduce((s, v) => s + v, 0) / n;
  let num = 0;
  let da = 0;
  let db = 0;
  for (let i = 0; i < n; i++) {
    const x = a[i] - ma;
    const y = b[i] - mb;
    num += x * y;
    da += x * x;
    db += y * y;
  }
  const den = Math.sqrt(da * db);
  return den === 0 ? 0 : num / den;
}

function correlationMatrix(dataset: Dataset): CorrelationMatrix | null {
  const numeric = dataset.profile.numeric_columns;
  if (numeric.length < 2 || dataset.preview.rows.length < 3) return null;
  const idx = numeric.map((name) => dataset.preview.columns.indexOf(name));
  const series = idx.map((col) =>
    dataset.preview.rows.map((row) => {
      const v = row[col];
      return typeof v === "number" ? v : Number(v);
    }),
  );
  const values = series.map((a) => series.map((b) => Number(pearson(a, b).toFixed(3))));
  return { labels: numeric, values };
}

export function RunDataView({ runId }: { runId: string }) {
  const { data, isLoading, isError, error } = useRunDataset(runId);
  const matrix = React.useMemo(() => (data ? correlationMatrix(data) : null), [data]);

  if (isLoading) return <DataTable columns={columnDefs} data={[]} loading pageSize={8} />;
  if (isError) {
    return (
      <ErrorState
        title="Could not load dataset"
        description={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }
  if (!data) {
    return (
      <EmptyState
        icon={<Database className="size-6" />}
        title="Dataset not linked"
        description="This run has no dataset profile attached. Profiles are captured during the EDA stage."
      />
    );
  }

  const { profile, validation } = data;
  const numericCols = profile.numeric_columns.filter((c) => profile.numeric_summary[c]);
  const categoricalCols = profile.categorical_columns.filter((c) => profile.categorical_summary[c]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <SummaryStat label="Rows" value={formatNumber(profile.shape.rows)} />
        <SummaryStat label="Columns" value={formatNumber(profile.shape.columns)} />
        <SummaryStat label="Memory" value={formatBytes(profile.memory_bytes)} />
        <SummaryStat
          label="Validation"
          value={validation.passed ? "Passed" : `${validation.null_columns.length} issues`}
          tone={validation.passed ? "success" : "danger"}
        />
      </div>

      <Tabs defaultValue="schema">
        <TabsList>
          <TabsTrigger value="schema">
            <Table2 className="mr-1.5 size-3.5" /> Schema
          </TabsTrigger>
          <TabsTrigger value="distributions">
            <BarChart3 className="mr-1.5 size-3.5" /> Distributions
          </TabsTrigger>
          <TabsTrigger value="correlations">
            <GitCompareArrows className="mr-1.5 size-3.5" /> Correlations
          </TabsTrigger>
          <TabsTrigger value="quality">
            <ShieldCheck className="mr-1.5 size-3.5" /> Quality
          </TabsTrigger>
        </TabsList>

        <TabsContent value="schema" className="mt-4">
          <DataTable
            columns={columnDefs}
            data={data.columns}
            searchPlaceholder="Search columns…"
            getRowId={(c) => c.name}
            pageSize={15}
          />
        </TabsContent>

        <TabsContent value="distributions" className="mt-4">
          {numericCols.length === 0 && categoricalCols.length === 0 ? (
            <EmptyState title="No distributions available" description="The profile reported no columns." />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {numericCols.slice(0, 8).map((name) => {
                const stats = profile.numeric_summary[name];
                return (
                  <ChartCard
                    key={name}
                    title={name}
                    description={`numeric · mean ${stats.mean.toFixed(2)} · std ${stats.std.toFixed(2)}`}
                  >
                    <div className="px-1 pt-6">
                      <RangeBar stats={stats} />
                    </div>
                  </ChartCard>
                );
              })}
              {categoricalCols.slice(0, 6).map((name) => {
                const summary = profile.categorical_summary[name];
                return (
                  <ChartCard
                    key={name}
                    title={name}
                    description={`categorical · ${formatNumber(summary.cardinality)} distinct values`}
                  >
                    <CategoryBarChart values={summary.top_values} height={220} />
                  </ChartCard>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="correlations" className="mt-4">
          {matrix ? (
            <ChartCard
              title="Numeric correlation matrix"
              description={`Pearson r, computed from the ${data.preview.rows.length}-row preview sample — indicative only, not the full dataset.`}
            >
              <CorrelationHeatmap matrix={matrix} height={Math.min(560, 80 + matrix.labels.length * 34)} />
            </ChartCard>
          ) : (
            <EmptyState
              icon={<GitCompareArrows className="size-6" />}
              title="Correlation unavailable"
              description="Need at least two numeric columns and a preview sample to compute correlations."
            />
          )}
        </TabsContent>

        <TabsContent value="quality" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Validation report" description="Checks run before ETL." loading={false}>
              <ul className="space-y-2 text-sm">
                <QualityRow
                  label="Overall"
                  value={validation.passed ? "Passed" : "Failed"}
                  tone={validation.passed ? "success" : "danger"}
                />
                <QualityRow label="Duplicate rows" value={formatNumber(validation.duplicate_rows)} tone={validation.duplicate_rows ? "warning" : "muted"} />
                <QualityRow
                  label="Columns with nulls"
                  value={validation.null_columns.length ? validation.null_columns.join(", ") : "None"}
                  tone={validation.null_columns.length ? "warning" : "muted"}
                />
                <QualityRow
                  label="Empty columns"
                  value={validation.empty_columns.length ? validation.empty_columns.join(", ") : "None"}
                  tone={validation.empty_columns.length ? "danger" : "muted"}
                />
              </ul>
            </ChartCard>

            <ChartCard title="Transform log" description="ETL actions applied to this dataset.">
              {data.transformLog.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No transforms recorded.
                </p>
              ) : (
                <ol className="space-y-2 text-sm">
                  {data.transformLog.map((entry, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium tabular-nums text-muted-foreground">
                        {i + 1}
                      </span>
                      <span>
                        <span className="font-medium text-foreground">{entry.action}</span>
                        {Object.entries(entry)
                          .filter(([k]) => k !== "action")
                          .map(([k, v]) => (
                            <span key={k} className="ml-1 text-xs text-muted-foreground">
                              {k}: {String(v)}
                            </span>
                          ))}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </ChartCard>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SummaryStat({ label, value, tone }: { label: string; value: string; tone?: "success" | "danger" }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={
          "mt-0.5 text-sm font-semibold tabular-nums " +
          (tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : "text-foreground")
        }
      >
        {value}
      </p>
    </div>
  );
}

function QualityRow({ label, value, tone }: { label: string; value: string; tone: "success" | "warning" | "danger" | "muted" }) {
  const toneClass = {
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
    muted: "text-muted-foreground",
  }[tone];
  return (
    <li className="flex items-start justify-between gap-4 border-b border-border pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={"text-right font-medium " + toneClass}>{value}</span>
    </li>
  );
}
