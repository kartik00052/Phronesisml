import { NavLink } from "react-router-dom";

import { cn } from "@/lib/cn";

const TABS: { to: string; label: string; end?: boolean }[] = [
  { to: "", label: "Overview", end: true },
  { to: "pipeline", label: "Pipeline" },
  { to: "data", label: "Data" },
  { to: "models", label: "Models" },
  { to: "explainability", label: "Explainability" },
  { to: "reports", label: "Reports" },
  { to: "artifacts", label: "Artifacts" },
  { to: "logs", label: "Logs" },
];

export function RunTabs({ runId }: { runId: string }) {
  return (
    <nav
      className="scrollbar-thin -mb-px flex gap-1 overflow-x-auto border-b border-border"
      aria-label="Run workspace sections"
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.label}
          to={tab.to ? `/runs/${runId}/${tab.to}` : `/runs/${runId}`}
          end={tab.end}
          className={({ isActive }) =>
            cn(
              "whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:border-border-strong hover:text-foreground",
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
