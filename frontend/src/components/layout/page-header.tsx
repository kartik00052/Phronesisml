import type * as React from "react";

import { cn } from "@/lib/cn";

export function PageHeader({
  title,
  description,
  children,
  className,
  actionsClassName,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  actionsClassName?: string;
}) {
  return (
    <div className={cn("mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children && (
        <div className={cn("flex shrink-0 items-center gap-2", actionsClassName)}>{children}</div>
      )}
    </div>
  );
}