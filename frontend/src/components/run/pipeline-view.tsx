import * as React from "react";
import { LayoutList, Network, PanelRightOpen } from "lucide-react";

import { PipelineDag } from "@/components/run/pipeline-dag";
import { StageDetailPanel } from "@/components/run/stage-detail";
import { PipelineStepper } from "@/components/pipeline/pipeline-stepper";
import { StageInspector } from "@/components/pipeline/stage-inspector";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";
import { formatDurationMs } from "@/lib/format";
import type { PipelineOverview, StageDetail } from "@/types/pipeline";

type View = "stepper" | "graph";

export function PipelineView({
  stages,
  selectedId,
  onSelect,
  overview,
}: {
  stages: StageDetail[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  overview?: PipelineOverview;
}) {
  const [view, setView] = React.useState<View>("stepper");
  const [inspectorOpen, setInspectorOpen] = React.useState(false);
  const selected = stages.find((s) => s.id === selectedId) ?? null;

  if (stages.length === 0) {
    return (
      <EmptyState
        title="Pipeline stages not available yet"
        description="Stages appear as the orchestrator reports progress."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {overview ? (
          <p className="text-xs text-muted-foreground">
            <span className="font-medium capitalize text-foreground">{overview.mode} mode</span> ·{" "}
            {overview.stagesExecuted.length}/{overview.stagesRequested.length} stages executed · total{" "}
            {formatDurationMs(overview.totalDurationMs)}
          </p>
        ) : (
          <span />
        )}
        <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
          <Button
            variant={view === "stepper" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 gap-1.5 px-2 text-xs"
            onClick={() => setView("stepper")}
            aria-pressed={view === "stepper"}
          >
            <LayoutList className="size-3.5" /> Stepper
          </Button>
          <Button
            variant={view === "graph" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 gap-1.5 px-2 text-xs"
            onClick={() => setView("graph")}
            aria-pressed={view === "graph"}
          >
            <Network className="size-3.5" /> Graph
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className={cn("lg:col-span-2", view === "graph" && "lg:col-span-5")}>
          {view === "stepper" ? (
            <Card>
              <CardContent className="p-2">
                <PipelineStepper
                  stages={stages}
                  selectedId={selectedId}
                  onSelect={(id) => {
                    onSelect(id);
                    setInspectorOpen(true);
                  }}
                />
              </CardContent>
            </Card>
          ) : (
            <PipelineDag stages={stages} selectedId={selectedId} onSelect={onSelect} />
          )}
        </div>

        <div className="hidden lg:col-span-3 lg:block">
          {view === "graph" ? (
            <Card className="border-dashed">
              <CardContent className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
                Select a node to inspect it.
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5"
                  disabled={!selected}
                  onClick={() => setInspectorOpen(true)}
                >
                  <PanelRightOpen className="size-3.5" /> Open inspector
                </Button>
              </CardContent>
            </Card>
          ) : selected ? (
            <StageDetailPanel stage={selected} active />
          ) : (
            <Card className="border-dashed">
              <CardContent className="p-6 text-sm text-muted-foreground">
                Select a stage to inspect its outputs.
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <Button
        variant="default"
        size="sm"
        className="fixed bottom-4 right-4 z-30 gap-1.5 shadow-lg lg:hidden"
        onClick={() => setInspectorOpen(true)}
        disabled={!selected}
      >
        <PanelRightOpen className="size-3.5" /> View stage
      </Button>

      <StageInspector stage={selected} open={inspectorOpen} onOpenChange={setInspectorOpen} />
    </div>
  );
}
