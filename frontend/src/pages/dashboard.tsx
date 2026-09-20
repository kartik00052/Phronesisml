import { Link } from "react-router-dom";
import {
  Archive,
  BrainCircuit,
  CheckCircle2,
  Database,
  FlaskConical,
  GitBranch,
  Sparkles,
  Trophy,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { EngineBreakdown, TaskBreakdown } from "@/components/dashboard/breakdowns";
import { RecentRuns } from "@/components/dashboard/recent-runs";
import { PipelineHealth } from "@/components/dashboard/pipeline-health";
import { ActiveRunBanner } from "@/components/dashboard/active-run-banner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDashboardStats, useRecentRuns } from "@/hooks/use-runs";
import { useDatasets } from "@/hooks/use-datasets";
import { formatNumber, formatScore } from "@/lib/format";

const TASK_HINTS: Record<string, string> = {
  classification: "Predict a category",
  regression: "Predict a number",
  clustering: "Discover groups",
  anomaly_detection: "Find outliers",
  ambiguous: "Let the agent decide",
};

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: runs, isLoading: runsLoading } = useRecentRuns();
  const { data: datasets } = useDatasets();

  const runningRun = runs?.find((r) => r.status === "running");
  const dominantTask = stats?.totalRuns
    ? (Object.entries(stats.taskBreakdown).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null)
    : null;

  const hasRuns = (stats?.totalRuns ?? 0) > 0;
  const hasDatasets = (stats?.totalDatasets ?? 0) > 0;
  const showEmptyState = !statsLoading && !hasRuns && !hasDatasets;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Cross-run overview of experiments, model leaderboards, and pipeline health."
        children={
          <>
            <Button asChild variant="outline">
              <Link to="/datasets">Datasets</Link>
            </Button>
            <Button asChild>
              <Link to="/runs/new">
                <Sparkles className="size-4" />
                New Run
              </Link>
            </Button>
          </>
        }
      />

      {runningRun && <ActiveRunBanner run={runningRun} />}

      {showEmptyState && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 p-8 text-center">
            <Sparkles className="size-8 text-primary" />
            <p className="text-lg font-semibold">Your workspace is ready</p>
            <p className="max-w-md text-sm text-muted-foreground">
              No experiments yet. Pick a sample dataset like Iris, or upload your own CSV, and
              launch your first run.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <Button asChild>
                <Link to="/runs/new">
                  <Sparkles className="size-4" />
                  New Run
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/datasets">Browse datasets</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <PipelineHealth run={runningRun} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total runs"
          value={formatNumber(stats?.totalRuns ?? 0)}
          icon={GitBranch}
          loading={statsLoading}
          hint={dominantTask ? `${dominantTask.replace(/_/g, " ")} dominant` : "no experiments yet"}
        />
        <StatCard
          label="Active runs"
          value={formatNumber(stats?.activeRuns ?? 0)}
          icon={FlaskConical}
          tone="info"
          loading={statsLoading}
          hint={dominantTask ? TASK_HINTS[dominantTask] : undefined}
        />
        <StatCard
          label="Completed"
          value={formatNumber(stats?.completedRuns ?? 0)}
          icon={CheckCircle2}
          tone="success"
          loading={statsLoading}
          hint={`avg best score ${stats?.avgBestScore != null ? formatScore(stats.avgBestScore) : "—"}`}
        />
        <StatCard
          label="Failed"
          value={formatNumber(stats?.failedRuns ?? 0)}
          icon={XCircle}
          tone={stats?.failedRuns ? "danger" : "default"}
          loading={statsLoading}
          hint={stats?.failedRuns ? "review run workspace" : "all green"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4">
          <Card>
            <CardContent className="flex items-start justify-between gap-3 p-4">
              <div>
                <div className="flex items-center gap-2">
                  <Trophy className="size-4 text-warning" />
                  <Badge variant="success">Best model</Badge>
                </div>
                <p className="mt-2 text-sm font-medium text-muted-foreground">Top experiment</p>
                <p className="truncate text-lg font-semibold">{runs?.[0]?.bestModelType ?? "—"}</p>
                <p className="text-xs text-muted-foreground">
                  {runs?.[0] ? `${runs[0].datasetName}` : "No runs yet"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-semibold tabular-nums text-success">
                  {formatScore(runs?.[0]?.bestScore)}
                </p>
              </div>
            </CardContent>
          </Card>

          <EngineBreakdown stats={stats} loading={statsLoading} />
        </div>

        <div className="lg:col-span-2">
          <TaskBreakdown stats={stats} loading={statsLoading} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="flex items-center gap-2 text-sm font-medium">
                  <Database className="size-4 text-muted-foreground" />
                  Registered datasets
                </p>
                <p className="mt-0.5 text-2xl font-semibold">
                  {formatNumber(stats?.totalDatasets ?? datasets?.items?.length ?? 0)}
                </p>
              </div>
              <Badge variant={stats?.failedRuns ? "default" : "success"}>
                {stats?.failedRuns ? `${stats.failedRuns} failed` : "Healthy"}
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-muted/40 text-muted-foreground">
              <BrainCircuit className="size-5" />
            </div>
            <div>
              <p className="text-sm font-medium">ML models</p>
              <p className="flex items-center gap-2 text-2xl font-semibold">
                {formatNumber(stats?.totalModels ?? 0)}
                <span className="text-sm font-normal text-muted-foreground">evaluated</span>
              </p>
            </div>
            <Archive className="ml-auto size-4 text-muted-foreground" />
          </CardContent>
        </Card>
      </div>

      <RecentRuns runs={runs} loading={runsLoading} />
    </div>
  );
}
