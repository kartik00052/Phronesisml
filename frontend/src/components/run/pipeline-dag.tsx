import { memo, useEffect, useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { CheckCircle2, CircleDot, Loader2, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";
import { STAGE_META } from "@/config/pipeline";
import { STAGE_PHASE_COLORS } from "@/config/visual";
import { formatDurationMs } from "@/lib/format";
import type { PipelineStageStatus, StageDetail } from "@/types/pipeline";

const STATUS_ICON: Partial<Record<PipelineStageStatus, React.ReactNode>> = {
  completed: <CheckCircle2 className="size-4 text-success" />,
  running: <Loader2 className="size-4 animate-spin text-info" />,
  failed: <XCircle className="size-4 text-danger" />,
  warning: <CircleDot className="size-4 text-warning" />,
};

const STATUS_BORDER: Record<PipelineStageStatus, string> = {
  idle: "border-border",
  queued: "border-border-strong",
  running: "border-info ring-2 ring-info/20",
  completed: "border-success/50",
  warning: "border-warning/50",
  failed: "border-danger/60",
  skipped: "border-border",
  sampled: "border-warning/40",
};

function StageNode({ data }: NodeProps) {
  const stage = data as {
    id: string;
    label: string;
    status: PipelineStageStatus;
    durationMs: number | null;
    summaryCount: number;
    phase: string;
  };
  const color = STAGE_PHASE_COLORS[stage.phase] ?? "var(--muted-foreground)";

  return (
    <div
      className={cn(
        "relative w-44 rounded-lg border bg-card px-3 py-2 shadow-card",
        STATUS_BORDER[stage.status],
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-foreground">{stage.label}</span>
        {STATUS_ICON[stage.status] ?? (
          <span className="size-2.5 rounded-full border border-border bg-muted" />
        )}
      </div>
      <div className="mt-1 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wide" style={{ color }}>
          {stage.phase}
        </span>
        <span className="text-[10px] tabular-nums text-muted-foreground">
          {stage.durationMs != null ? formatDurationMs(stage.durationMs) : "—"}
        </span>
      </div>
      {stage.summaryCount > 0 && (
        <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-info" style={{ width: "100%", opacity: 0.8 }} />
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  );
}

const nodeTypes = { stage: memo(StageNode) };

function toNodes(stages: StageDetail[]): Node[] {
  // Horizontal layout with consistent spacing; wrap columns every 6 stages.
  return stages.map((s, i) => {
    const col = Math.floor(i / 6);
    const row = i % 6;
    const meta = s.id === "node_sampling" ? null : STAGE_META[s.id];
    return {
      id: s.id,
      type: "stage",
      position: { x: 40 + col * 250, y: 40 + row * 88 },
      data: {
        id: s.id,
        label: meta?.label ?? (s.id === "node_sampling" ? "Sampling" : s.name),
        status: s.status,
        durationMs: s.durationMs,
        summaryCount: Object.keys(s.summary ?? {}).length,
        phase: meta?.phase ?? "data",
      },
    } satisfies Node;
  });
}

function toEdges(stages: StageDetail[], upstreamRunning: boolean): Edge[] {
  const edges: Edge[] = [];
  for (let i = 0; i < stages.length - 1; i++) {
    const a = stages[i];
    edges.push({
      id: `${a.id}-${stages[i + 1].id}`,
      source: a.id,
      target: stages[i + 1].id,
      markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "var(--border-strong)" },
      style: { stroke: "var(--border-strong)", strokeWidth: 1.5 },
      animated: upstreamRunning && a.status === "running",
    });
  }
  return edges;
}

export function PipelineDag({
  stages,
  selectedId,
  onSelect,
}: {
  stages: StageDetail[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const nextNodes = useMemo(() => toNodes(stages), [stages]);
  const nextEdges = useMemo(
    () => toEdges(stages, stages.some((s) => s.status === "running")),
    [stages],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(nextNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(nextEdges);

  // Live stages update (polled while a run is active) must flow into ReactFlow's
  // internal node/edge state — otherwise the DAG would only ever show the first
  // snapshot of the pipeline.
  useEffect(() => {
    setNodes(nextNodes);
    setEdges(nextEdges);
  }, [nextNodes, nextEdges, setNodes, setEdges]);

  return (
    <div className="relative h-[420px] w-full overflow-hidden rounded-lg border border-border bg-grid-sheet">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1 }}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        edgesFocusable={false}
        minZoom={0.3}
        maxZoom={1.6}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} color="var(--border)" />
        <Controls showInteractive={false} className="!bg-surface" />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => {
            const status = (n.data as { status: PipelineStageStatus }).status;
            return status === "completed"
              ? "var(--success)"
              : status === "running"
                ? "var(--info)"
                : status === "failed"
                  ? "var(--danger)"
                  : "var(--muted)";
          }}
          className="!bg-surface-muted"
        />
      </ReactFlow>
      {selectedId && (
        <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground shadow-sm">
          Selected: {STAGE_META[selectedId as keyof typeof STAGE_META]?.label ?? selectedId}
        </div>
      )}
    </div>
  );
}