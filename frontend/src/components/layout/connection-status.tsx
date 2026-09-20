import { cn } from "@/lib/cn";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useHealth } from "@/hooks/use-health";
import { isDemoMode } from "@/mocks";
import type { HealthProbeState } from "@/types/health";

type State = "demo" | "loading" | "ok" | "degraded" | "offline";

const DOT: Record<State, string> = {
  demo: "bg-warning",
  loading: "bg-muted-foreground animate-pulse",
  ok: "bg-success",
  degraded: "bg-warning",
  offline: "bg-danger",
};

const LABEL: Record<State, string> = {
  demo: "Demo",
  loading: "Connecting…",
  ok: "API online",
  degraded: "Degraded",
  offline: "API offline",
};

function degradedDetail(
  missing: string[] | undefined,
  database?: HealthProbeState,
  storage?: HealthProbeState,
): string {
  const parts: string[] = [];
  if (missing?.length) parts.push(`Missing core deps: ${missing.join(", ")}`);
  if (database && database.reachable === false) parts.push("Database unreachable");
  if (storage && storage.writable === false) parts.push("Storage not writable");
  return parts.length ? parts.join(" · ") : "Backend is degraded.";
}

/** Small connection/health indicator for the top bar. */
export function ConnectionStatus() {
  const demo = isDemoMode();
  const { data, isLoading, isError } = useHealth();

  const state: State = demo
    ? "demo"
    : isLoading
      ? "loading"
      : isError
        ? "offline"
        : data?.status === "ok"
          ? "ok"
          : "degraded";

  const detail = demo
    ? "Running against bundled demo data. Set VITE_DEMO_MODE=false to target a live backend."
    : state === "ok"
      ? `PhronesisML ${data?.version ?? ""} · Python ${data?.python ?? ""}`
      : state === "offline"
        ? "No response from the backend API."
        : state === "degraded"
          ? degradedDetail(data?.missing_core, data?.database, data?.storage)
          : "Checking backend health…";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs font-medium text-muted-foreground">
          <span className={cn("size-2 rounded-full", DOT[state])} aria-hidden />
          <span className="hidden sm:inline">{LABEL[state]}</span>
          <span className="sr-only">Backend status: {LABEL[state]}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent side="bottom">{detail}</TooltipContent>
    </Tooltip>
  );
}
