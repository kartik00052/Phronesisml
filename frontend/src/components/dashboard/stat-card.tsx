import type * as React from "react";
import { type LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  tone = "default",
  loading,
}: {
  label: string;
  value: React.ReactNode;
  icon: LucideIcon;
  hint?: React.ReactNode;
  tone?: "default" | "success" | "info" | "danger" | "warning";
  loading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-16" />
          ) : (
            <p className="mt-1 text-2xl font-semibold tracking-tight">{value}</p>
          )}
          {hint && (
            <p className={cn("mt-1 truncate text-xs", tone === "danger" ? "text-danger" : "text-muted-foreground")}>
              {hint}
            </p>
          )}
        </div>
        <div
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-md border",
            tone === "success" && "border-success/30 bg-success/10 text-success",
            tone === "info" && "border-info/30 bg-info/10 text-info",
            tone === "danger" && "border-danger/30 bg-danger/10 text-danger",
            tone === "warning" && "border-warning/30 bg-warning/10 text-warning",
            tone === "default" && "border-border bg-muted/40 text-muted-foreground",
          )}
        >
          <Icon className="size-4" />
        </div>
      </CardContent>
    </Card>
  );
}