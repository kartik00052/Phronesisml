import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Check,
  Clock,
  Copy,
  Cpu,
  FileText,
  Gauge,
  Layers,
  PlusCircle,
  RefreshCw,
  Target,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent } from "@/components/ui/card";
import { RunActions } from "@/components/run/run-actions";
import { RunStatusBadge } from "@/components/ui/status-badge";
import { ENGINE_LABELS, TASK_LABELS } from "@/config/status";
import { formatDurationMs, formatNumber, formatScore, truncateId } from "@/lib/format";
import type { Run } from "@/types/run";

export function RunHeader({ run, onRefresh }: { run: Run; onRefresh?: () => void }) {
  const s = run.summary;
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  const copyRunId = async () => {
    try {
      await navigator.clipboard.writeText(run.id);
      setCopied(true);
      toast.success(`Copied run ID ${truncateId(run.id)}`);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy run ID");
    }
  };

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                {s.datasetName}
              </h1>
              <RunStatusBadge status={s.status} />
            </div>
            <p className="mt-1 flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
              run {truncateId(run.id)}
              <Button
                variant="ghost"
                size="icon"
                className="size-5 text-muted-foreground hover:text-foreground"
                onClick={copyRunId}
                aria-label="Copy run ID"
                title="Copy run ID"
              >
                {copied ? <Check className="size-3 text-success" /> : <Copy className="size-3" />}
              </Button>
            </p>
          </div>

          <div className="flex items-center gap-2">
            {onRefresh && (
              <Button variant="outline" size="sm" onClick={onRefresh} className="gap-1.5">
                <RefreshCw className="size-3.5" />
                Refresh
              </Button>
            )}
            <RunActions runId={run.id} status={s.status} onDeleted={() => navigate("/runs")} />
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to="/runs/new">
                <PlusCircle className="size-3.5" />
                New run
              </Link>
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Target className="size-3.5" />
            Task:{" "}
            <span className="font-medium capitalize text-foreground">
              {TASK_LABELS[s.taskType] ?? s.taskType}
            </span>
          </span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Cpu className="size-3.5" />
            Engine:{" "}
            <span className="font-medium text-foreground">
              {ENGINE_LABELS[s.engine] ?? s.engine}
            </span>
          </span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <FileText className="size-3.5" />
            Target:{" "}
            <span className="font-medium text-foreground">{s.targetColumn ?? "auto-detect"}</span>
          </span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Layers className="size-3.5" />
            {formatNumber(s.rows)} rows × {formatNumber(s.columns)} cols
          </span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="size-3.5" />
            {formatDurationMs(run.totalDurationMs ?? s.durationMs)}
          </span>
        </div>

        {s.mode && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="uppercase tracking-wide">
              {s.mode}
            </Badge>
            {s.bestModelType && (
              <Badge variant="outline" className="gap-1">
                <Gauge className="size-3" />
                Best: {s.bestModelType}
              </Badge>
            )}
            {s.bestScore != null && (
              <Badge variant="success">
                {s.primaryMetric}: {formatScore(s.bestScore)}
              </Badge>
            )}
            {s.hpoTruncated == null
              ? null
              : s.hpoTruncated && <Badge variant="warning">HPO truncated</Badge>}
            {s.error && (
              <Badge variant="danger">
                {s.error.length > 80 ? `${s.error.slice(0, 80)}…` : s.error}
              </Badge>
            )}
          </div>
        )}

        <Separator className="my-4" />
        <p className="text-xs text-muted-foreground">{s.engineReason}</p>
      </CardContent>
    </Card>
  );
}
