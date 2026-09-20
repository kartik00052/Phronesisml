import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StageDetailPanel } from "@/components/run/stage-detail";
import { STAGE_META } from "@/config/pipeline";
import type { PipelineStageId, StageDetail } from "@/types/pipeline";

export function StageInspector({
  stage,
  open,
  onOpenChange,
}: {
  stage: StageDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const meta = stage && stage.id !== "node_sampling" ? STAGE_META[stage.id as PipelineStageId] : null;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-lg">
        <SheetHeader className="border-b border-border px-4 py-3">
          <SheetTitle className="text-sm">
            {meta?.label ?? stage?.name ?? "Stage inspector"}
          </SheetTitle>
        </SheetHeader>
        <div className="p-4">
          {stage ? (
            <StageDetailPanel stage={stage} active />
          ) : (
            <p className="text-sm text-muted-foreground">No stage selected.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
