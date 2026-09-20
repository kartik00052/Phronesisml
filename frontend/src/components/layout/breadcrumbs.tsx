import { Fragment } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/cn";
import { buildCrumbs } from "@/lib/crumbs";

export function Breadcrumbs({ className }: { className?: string }) {
  const { pathname } = useLocation();
  const crumbs = buildCrumbs(pathname);

  if (crumbs.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1 text-sm", className)}>
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <Fragment key={i}>
            {i > 0 && <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/50" />}
            {!isLast && crumb.to ? (
              <Link
                to={crumb.to}
                className="truncate text-muted-foreground transition-colors hover:text-foreground"
              >
                {crumb.label}
              </Link>
            ) : (
              <span className="truncate font-medium text-foreground" aria-current="page">
                {crumb.label}
              </span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}