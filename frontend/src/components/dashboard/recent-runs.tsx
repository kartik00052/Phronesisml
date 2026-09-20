import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RunStatusBadge } from "@/components/ui/status-badge";
import { TASK_LABELS } from "@/config/status";
import { formatDateTime, formatScore } from "@/lib/format";
import type { RecentRunActivity } from "@/types/run";

function RunLinkRow({ run }: { run: RecentRunActivity }) {
  return (
    <TableRow className="cursor-pointer">
      <TableCell className="max-w-[240px]">
        <Link to={`/runs/${run.id}`} className="block truncate font-medium text-foreground hover:text-primary">
          {run.datasetName}
        </Link>
        <span className="block truncate font-mono text-xs text-muted-foreground">{run.id}</span>
      </TableCell>
      <TableCell>
        <RunStatusBadge status={run.status} />
      </TableCell>
      <TableCell className="capitalize">{TASK_LABELS[run.taskType] ?? run.taskType}</TableCell>
      <TableCell className="truncate">{run.bestModelType ? `Best: ${run.bestModelType}` : "—"}</TableCell>
      <TableCell className="tabular-nums">{formatScore(run.bestScore)}</TableCell>
      <TableCell className="text-muted-foreground">{formatDateTime(run.createdAt)}</TableCell>
    </TableRow>
  );
}

export function RecentRuns({
  runs,
  loading,
}: {
  runs?: RecentRunActivity[];
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="text-sm">Recent activity</CardTitle>
        <Button asChild variant="ghost" size="sm" className="gap-1 text-muted-foreground">
          <Link to="/runs">
            View all <ArrowRight className="size-3.5" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : runs && runs.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Dataset</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Task</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Started</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <RunLinkRow key={run.id} run={run} />
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
            <p className="text-sm text-muted-foreground">
              No runs yet — launch your first experiment to get started.
            </p>
            <Button asChild size="sm">
              <Link to="/runs/new">Create a run</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}