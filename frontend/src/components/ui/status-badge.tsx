import { Loader2 } from "lucide-react";
import type { VariantProps } from "class-variance-authority";

import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/badge";
import {
  RUN_STATUS_META,
  STAGE_STATUS_META,
  type StatusMeta,
} from "@/config/status";
import type { RunStatus } from "@/types/run";
import type { PipelineStageStatus } from "@/types/pipeline";

type BadgeVariant = NonNullable<VariantProps<typeof Badge>["variant"]>;

function toneVariant(tone: StatusMeta["tone"]): BadgeVariant {
  switch (tone) {
    case "danger":
      return "danger";
    case "warning":
      return "warning";
    case "success":
      return "success";
    case "info":
      return "info";
    default:
      return "muted";
  }
}

export function RunStatusBadge({ status, className }: { status: RunStatus; className?: string }) {
  const meta = RUN_STATUS_META[status];
  return (
    <Badge variant={toneVariant(meta.tone)} className={cn(status === "running" && "[&>svg]:animate-spin", className)}>
      <meta.icon />
      {meta.label}
    </Badge>
  );
}

export function StageStatusBadge({
  status,
  className,
}: {
  status: PipelineStageStatus;
  className?: string;
}) {
  const meta = STAGE_STATUS_META[status];
  const Icon = status === "running" ? Loader2 : meta.icon;
  return (
    <Badge variant={toneVariant(meta.tone)} className={cn(status === "running" && "[&>svg]:animate-spin", className)}>
      <Icon />
      {meta.label}
    </Badge>
  );
}