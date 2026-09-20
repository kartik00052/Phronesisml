import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, CheckCircle2, Info, TriangleAlert, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg~*]:pl-8",
  {
    variants: {
      variant: {
        default: "border-border bg-card text-foreground",
        destructive: "border-danger/30 bg-danger/5 text-foreground [&>svg]:text-danger",
        warning: "border-warning/30 bg-warning/5 text-foreground [&>svg]:text-warning",
        info: "border-info/30 bg-info/5 text-foreground [&>svg]:text-info",
        success: "border-success/30 bg-success/5 text-foreground [&>svg]:text-success",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

function Alert({
  className,
  variant,
  icon,
  children,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants> & { icon?: LucideIcon }) {
  const Icon =
    icon ??
    (variant === "destructive"
      ? AlertCircle
      : variant === "warning"
        ? TriangleAlert
        : variant === "success"
          ? CheckCircle2
          : Info);
  return (
    <div data-slot="alert" role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      <Icon aria-hidden />
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function AlertTitle({ className, ...props }: React.ComponentProps<"h5">) {
  return <h5 className={cn("mb-1 font-medium leading-none tracking-tight", className)} {...props} />;
}

function AlertDescription({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("text-sm [&_p]:leading-relaxed", className)} {...props} />;
}

export { Alert, AlertTitle, AlertDescription };