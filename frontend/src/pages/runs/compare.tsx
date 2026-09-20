import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Check, Columns3, GitCompareArrows, Loader2, Trophy, X } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { RunStatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { useRuns } from "@/hooks/use-runs";
import { useModels } from "@/hooks/use-run-extras";
import { TASK_LABELS } from "@/config/status";
import { formatDateTime, formatDurationMs, formatNumber, formatScore } from "@/lib/format";
import type { RunSummary } from "@/types/run";

interface Row {
  label: string;
  value: (r: RunSummary) => string;
  /** Render raw text; otherwise value is treated as comparable. */
  raw?: boolean;
}

const ROWS: Row[] = [
  { label: "Status", value: (r) => r.status, raw: true },
  { label: "Dataset", value: (r) => r.datasetName },
  { label: "Task", value: (r) => TASK_LABELS[r.taskType] ?? r.taskType },
  { label: "Target", value: (r) => r.targetColumn ?? "auto-detect" },
  { label: "Engine", value: (r) => r.engine },
  { label: "Mode", value: (r) => r.mode },
  { label: "Rows × Cols", value: (r) => `${formatNumber(r.rows)} × ${formatNumber(r.columns)}` },
  { label: "Best model", value: (r) => r.bestModelType ?? "—" },
  { label: "Primary metric", value: (r) => r.primaryMetric || "—" },
  { label: "Best score", value: (r) => formatScore(r.bestScore), raw: true },
  { label: "Trials", value: (r) => (r.trialCount != null ? formatNumber(r.trialCount) : "—") },
  { label: "HPO truncated", value: (r) => (r.hpoTruncated ? "yes" : "no") },
  { label: "Duration", value: (r) => formatDurationMs(r.durationMs), raw: true },
  { label: "Started", value: (r) => formatDateTime(r.createdAt) },
];

function RunLeaderboard({ runId }: { runId: string }) {
  const { data, isLoading, isError } = useModels(runId);
  if (isLoading) {
    return (
      <div className="flex h-28 items-center justify-center rounded-lg border border-border bg-card">
        <Loader2 className="size-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  const models = data ?? [];
  if (isError || models.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card px-4 py-3 text-xs text-muted-foreground">
        No leaderboard available for this run yet.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-card">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-[10px] uppercase tracking-wide text-muted-foreground">
            <th className="px-3 py-2">#</th>
            <th className="px-3 py-2">Model</th>
            <th className="px-3 py-2 text-right">Score</th>
            <th className="px-3 py-2 text-right">Trials</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {models.slice(0, 3).map((m) => (
            <tr key={m.model_type} className="border-b border-border last:border-0">
              <td className="px-3 py-2 text-muted-foreground">{m.rank}</td>
              <td className="px-3 py-2 font-mono text-foreground">{m.model_type}</td>
              <td className="px-3 py-2 text-right tabular-nums">{formatScore(m.primary_score)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                {formatNumber(m.trials_used)}
              </td>
              <td className="px-3 py-2">
                {m.best ? (
                  <Badge variant="success" className="px-1.5 py-0 text-[10px]">
                    best
                  </Badge>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function RunComparePage() {
  const { data, isLoading } = useRuns({ pageSize: 50, sort: "createdAt", order: "desc" });
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = React.useState<string[]>([]);
  const [differencesOnly, setDifferencesOnly] = React.useState(true);

  const runs = data?.items ?? [];
  const chosen = selected
    .map((id) => runs.find((r) => r.id === id))
    .filter((r): r is RunSummary => !!r);

  const persist = React.useCallback(
    (ids: string[]) => {
      const next = new URLSearchParams(searchParams);
      if (ids.length > 0) next.set("runs", ids.join(","));
      else next.delete("runs");
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  // Selection is carried in the URL (?runs=a,b,c) so comparisons are shareable.
  const selectedParam = searchParams.get("runs");
  React.useEffect(() => {
    const ids = (selectedParam ?? "").split(",").filter(Boolean);
    setSelected(ids);
  }, [selectedParam]);

  // Drop ids that don't exist in the loaded list (stale share links, deleted runs).
  React.useEffect(() => {
    if (!data) return;
    const known = new Set(runs.map((r) => r.id));
    const stale = selected.filter((id) => !known.has(id));
    if (stale.length > 0) {
      const next = selected.filter((id) => known.has(id));
      setSelected(next);
      persist(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const toggle = (id: string) => {
    const next = selected.includes(id)
      ? selected.filter((x) => x !== id)
      : selected.length >= 4
        ? selected
        : [...selected, id];
    setSelected(next);
    persist(next);
  };

  const visibleRows = differencesOnly
    ? ROWS.filter((row) => new Set(chosen.map(row.value)).size > 1)
    : ROWS;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compare runs"
        description="Line up to four experiments side by side, showing only the fields that differ."
      >
        <Button asChild variant="outline">
          <Link to="/runs">Back to runs</Link>
        </Button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <div className="rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Select runs
              </span>
              <span className="text-xs tabular-nums text-muted-foreground">{selected.length}/4</span>
            </div>
            {isLoading ? (
              <div className="space-y-2 p-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-9 w-full" />
                ))}
              </div>
            ) : (
              <ul className="scrollbar-thin max-h-[420px] divide-y divide-border overflow-y-auto">
                {runs.map((run) => {
                  const active = selected.includes(run.id);
                  return (
                    <li key={run.id}>
                      <button
                        type="button"
                        onClick={() => toggle(run.id)}
                        aria-pressed={active}
                        className={cn(
                          "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-muted/40",
                          active && "bg-primary/5",
                        )}
                      >
                        <span
                          className={cn(
                            "flex size-4 shrink-0 items-center justify-center rounded border",
                            active ? "border-primary bg-primary text-primary-foreground" : "border-border",
                          )}
                        >
                          {active && <Check className="size-3" />}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-foreground">
                            {run.datasetName}
                          </span>
                          <span className="block truncate font-mono text-[10px] text-muted-foreground">
                            {run.id}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        <div className="space-y-4 lg:col-span-3">
          <div className="flex items-center gap-2">
            <Switch
              id="differences-only"
              checked={differencesOnly}
              onCheckedChange={setDifferencesOnly}
            />
            <Label htmlFor="differences-only" className="text-sm text-muted-foreground">
              Differences only
            </Label>
          </div>

          {chosen.length < 2 ? (
            <EmptyState
              icon={<GitCompareArrows className="size-6" />}
              title="Select at least two runs"
              description="Pick experiments from the list to compare their configuration and results."
            />
          ) : visibleRows.length === 0 ? (
            <EmptyState
              icon={<Check className="size-6" />}
              title="These runs are identical"
              description="No differing fields to show. Turn off “Differences only” to see all fields."
            />
          ) : (
            <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border bg-card">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="w-40 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Field
                    </th>
                    {chosen.map((run) => (
                      <th key={run.id} className="min-w-44 px-3 py-2 text-left">
                        <Link
                          to={`/runs/${run.id}`}
                          className="block truncate font-medium text-foreground hover:text-primary"
                          title={run.datasetName}
                        >
                          {run.datasetName}
                        </Link>
                        <span className="mt-0.5 block">
                          <RunStatusBadge status={run.status} />
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => (
                    <tr key={row.label} className="border-b border-border last:border-0">
                      <td className="px-3 py-2 text-xs font-medium text-muted-foreground">
                        {row.label}
                      </td>
                      {chosen.map((run) => (
                        <td key={run.id} className="px-3 py-2 tabular-nums text-foreground">
                          {row.value(run)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {selected.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setSelected([]);
                persist([]);
              }}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="size-3" /> Clear selection
            </button>
          )}
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Columns3 className="size-3.5" /> Comparing {chosen.length} run
            {chosen.length === 1 ? "" : "s"}
          </p>

          {chosen.length >= 1 && (
            <section className="mt-6">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Trophy className="size-4 text-warning" />
                Model leaderboards
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Best performing candidates from each run's HPO loop.
              </p>
              <div
                className={cn(
                  "mt-3 grid gap-4",
                  chosen.length > 1 ? "md:grid-cols-2" : "md:grid-cols-1",
                )}
              >
                {chosen.map((run) => (
                  <RunLeaderboard key={run.id} runId={run.id} />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
