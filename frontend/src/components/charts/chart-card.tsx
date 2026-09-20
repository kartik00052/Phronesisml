import * as React from "react";
import { BarChart3, Table2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

export interface ChartCardProps {
  title: string;
  description?: string;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyMessage?: string;
  actions?: React.ReactNode;
  /** Optional tabular equivalent for accessibility / exact values. */
  dataTable?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/**
 * Consistent analytical chart container: title, provenance/description,
 * loading / empty / error states, and an optional accessible data table.
 */
export function ChartCard({
  title,
  description,
  loading,
  error,
  empty,
  emptyMessage = "No data available for this view.",
  actions,
  dataTable,
  className,
  bodyClassName,
  children,
}: ChartCardProps) {
  const [showTable, setShowTable] = React.useState(false);

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-2">
        <div className="min-w-0">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="size-3.5 text-muted-foreground" />
            <span className="truncate">{title}</span>
          </CardTitle>
          {description && (
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {actions}
          {dataTable && (
            <Button
              variant="ghost"
              size="icon"
              className="size-7 text-muted-foreground"
              aria-label={showTable ? "Show chart" : "Show data table"}
              aria-pressed={showTable}
              onClick={() => setShowTable((v) => !v)}
            >
              {showTable ? <BarChart3 className="size-3.5" /> : <Table2 className="size-3.5" />}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className={cn("pt-2", bodyClassName)}>
        {loading ? (
          <Skeleton className="h-56 w-full" />
        ) : error ? (
          <div className="flex h-56 items-center justify-center rounded-md border border-dashed border-danger/40 bg-danger/5 p-6 text-center text-sm text-danger">
            {error}
          </div>
        ) : empty ? (
          <div className="flex h-56 items-center justify-center rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            {emptyMessage}
          </div>
        ) : showTable && dataTable ? (
          <div className="scrollbar-thin max-h-80 overflow-auto">{dataTable}</div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
