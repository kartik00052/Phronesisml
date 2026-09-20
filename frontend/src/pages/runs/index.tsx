import * as React from "react";
import { Link } from "react-router-dom";
import { ArrowUpDown, GitCompareArrows, PlusCircle, Search } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RunStatusBadge } from "@/components/ui/status-badge";
import { RunActions } from "@/components/run/run-actions";
import { TASK_LABELS } from "@/config/status";
import { useRuns } from "@/hooks/use-runs";
import { formatDateTime, formatDurationMs, formatNumber, formatScore } from "@/lib/format";
import type { RunStatus } from "@/types/run";

type SortKey = "createdAt" | "bestScore" | "durationMs";

export default function RunsListPage() {
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<string>("");
  const [taskType, setTaskType] = React.useState<string>("");
  const [sort, setSort] = React.useState<SortKey>("createdAt");
  const [order, setOrder] = React.useState<"asc" | "desc">("desc");
  const [page, setPage] = React.useState(1);
  const pageSize = 20;

  const debouncedSearch = useDebounced(search, 300);

  const { data, isLoading, isError } = useRuns({
    page,
    pageSize,
    sort,
    order,
    status: status || undefined,
    taskType: taskType || undefined,
    search: debouncedSearch || undefined,
  });

  const toggleSort = (key: SortKey) => {
    if (sort === key) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setOrder("desc");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Runs"
        description="Every experiment launched on the platform, with status, task type, and best model."
        children={
          <>
            <Button asChild variant="outline">
              <Link to="/runs/compare">
                <GitCompareArrows className="size-4" />
                Compare
              </Link>
            </Button>
            <Button asChild>
              <Link to="/runs/new">
                <PlusCircle className="size-4" />
                New Run
              </Link>
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search runs…"
            className="h-9 w-64 pl-8"
          />
        </div>
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All statuses</SelectItem>
            {(["queued", "running", "completed", "failed"] as RunStatus[]).map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={taskType}
          onValueChange={(v) => {
            setTaskType(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-48 h-9">
            <SelectValue placeholder="Task type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All tasks</SelectItem>
            {Object.entries(TASK_LABELS).map(([k, label]) => (
              <SelectItem key={k} value={k}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Dataset</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Task</TableHead>
              <TableHead>Engine</TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort("bestScore")}
              >
                <span className="inline-flex items-center gap-1">
                  Best score <ArrowUpDown className="size-3" />
                </span>
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort("durationMs")}
              >
                <span className="inline-flex items-center gap-1">
                  Duration <ArrowUpDown className="size-3" />
                </span>
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => toggleSort("createdAt")}
              >
                <span className="inline-flex items-center gap-1">
                  Started <ArrowUpDown className="size-3" />
                </span>
              </TableHead>
              <TableHead className="sr-only">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={8}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                  Failed to load runs. Is the backend running?
                </TableCell>
              </TableRow>
            ) : data && data.items.length > 0 ? (
              data.items.map((run) => (
                <TableRow key={run.id} className="cursor-pointer">
                  <TableCell className="max-w-60">
                    <Link
                      to={`/runs/${run.id}`}
                      className="block truncate font-medium text-foreground hover:text-primary"
                    >
                      {run.datasetName}
                    </Link>
                    <span className="block truncate font-mono text-xs text-muted-foreground">
                      {run.id}
                    </span>
                  </TableCell>
                  <TableCell>
                    <RunStatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="capitalize">
                    {TASK_LABELS[run.taskType] ?? run.taskType}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{run.engine}</TableCell>
                  <TableCell className="tabular-nums">{formatScore(run.bestScore)}</TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {formatDurationMs(run.durationMs)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(run.createdAt)}
                  </TableCell>
                  <TableCell className="w-28">
                    <RunActions runId={run.id} status={run.status} />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-sm text-muted-foreground">
                  No runs match.{" "}
                  <Link to="/runs/new" className="font-medium text-primary hover:underline">
                    Launch one
                  </Link>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {data && data.total > pageSize && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
            <span className="text-muted-foreground">
              {formatNumber(data.total)} total · page {data.page}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Prev
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.hasMore}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
