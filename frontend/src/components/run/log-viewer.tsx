import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDownToLine, Check, Copy, Search, TerminalSquare } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/cn";

type LogLevel = "info" | "warning" | "error" | "debug";

function detectLevel(line: string): LogLevel {
  const upper = line.toUpperCase();
  if (line.startsWith("[ERROR]") || /\bERROR\b|\bFAILED\b|Traceback/.test(upper)) return "error";
  if (line.startsWith("[WARN]") || /\bWARN(ING)?\b/.test(upper)) return "warning";
  if (line.startsWith("[DEBUG]") || /\bDEBUG\b/.test(upper)) return "debug";
  return "info";
}

const LEVEL_CLASS: Record<LogLevel, string> = {
  info: "text-muted-foreground",
  debug: "text-muted-foreground/60",
  warning: "text-warning",
  error: "text-danger",
};

const ROW_HEIGHT = 20;

export interface LogViewerProps {
  logs?: string[];
  loading?: boolean;
  /** Automatically follow new lines while true. */
  live?: boolean;
  height?: number;
  className?: string;
}

/**
 * Virtualized log viewer: only the visible window is rendered, so multi-MB
 * logs stay smooth. Supports search, level filtering, follow mode, wrapping,
 * copy, and line numbers.
 */
export function LogViewer({
  logs = [],
  loading,
  live = false,
  height = 420,
  className,
}: LogViewerProps) {
  const [query, setQuery] = React.useState("");
  const [level, setLevel] = React.useState<"all" | LogLevel>("all");
  const [follow, setFollow] = React.useState(live);
  const [wrap, setWrap] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const parentRef = React.useRef<HTMLDivElement>(null);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return logs
      .map((text, index) => ({ text, index, level: detectLevel(text) }))
      .filter((entry) => (level === "all" ? true : entry.level === level))
      .filter((entry) => (q ? entry.text.toLowerCase().includes(q) : true));
  }, [logs, query, level]);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => (wrap ? 34 : ROW_HEIGHT),
    overscan: 24,
  });

  React.useEffect(() => {
    if (follow && filtered.length > 0) {
      virtualizer.scrollToIndex(filtered.length - 1, { align: "end" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtered.length, follow]);

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(logs.join("\n"));
      setCopied(true);
      toast.success("Logs copied to clipboard");
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy logs");
    }
  };

  const counts = React.useMemo(() => {
    const acc = { error: 0, warning: 0 };
    for (const line of logs) {
      const l = detectLevel(line);
      if (l === "error") acc.error += 1;
      else if (l === "warning") acc.warning += 1;
    }
    return acc;
  }, [logs]);

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border bg-card", className)}>
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
        <span className="flex items-center gap-1.5 text-sm font-medium">
          <TerminalSquare className="size-3.5 text-muted-foreground" />
          Logs
          <span className="text-xs font-normal tabular-nums text-muted-foreground">
            {logs.length} lines
          </span>
        </span>
        {counts.error > 0 && (
          <span className="rounded bg-danger/10 px-1.5 py-0.5 text-xs font-medium tabular-nums text-danger">
            {counts.error} errors
          </span>
        )}
        {counts.warning > 0 && (
          <span className="rounded bg-warning/10 px-1.5 py-0.5 text-xs font-medium tabular-nums text-warning">
            {counts.warning} warnings
          </span>
        )}

        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter logs…"
              className="h-7 w-40 pl-7 text-xs"
              aria-label="Filter logs"
            />
          </div>
          <Select value={level} onValueChange={(v) => setLevel(v as typeof level)}>
            <SelectTrigger className="h-7 w-24 text-xs" aria-label="Filter by level">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All levels</SelectItem>
              <SelectItem value="debug">Debug</SelectItem>
              <SelectItem value="info">Info</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant={wrap ? "secondary" : "ghost"}
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => setWrap((v) => !v)}
            aria-pressed={wrap}
          >
            Wrap
          </Button>
          <Button
            variant={follow ? "secondary" : "ghost"}
            size="icon"
            className="size-7"
            onClick={() => setFollow((v) => !v)}
            aria-pressed={follow}
            aria-label="Follow latest logs"
            title="Follow latest"
          >
            <ArrowDownToLine className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={copyAll}
            aria-label="Copy logs"
            title="Copy logs"
          >
            {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 p-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-1 py-16 text-center">
          <TerminalSquare className="size-6 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">
            {logs.length === 0 ? "No logs yet" : "No matching lines"}
          </p>
          <p className="text-xs text-muted-foreground">
            {logs.length === 0
              ? "Logs stream here once the pipeline starts."
              : "Adjust the search or level filter."}
          </p>
        </div>
      ) : (
        <div ref={parentRef} className="scrollbar-thin overflow-auto" style={{ height }}>
          <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
            {virtualizer.getVirtualItems().map((item) => {
              const entry = filtered[item.index];
              return (
                <div
                  key={item.key}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${item.start}px)`,
                    height: item.size,
                  }}
                  className="flex gap-3 px-3 font-mono text-xs leading-5"
                >
                  <span className="w-10 shrink-0 select-none text-right tabular-nums text-muted-foreground/50">
                    {entry.index + 1}
                  </span>
                  <span
                    className={cn(
                      LEVEL_CLASS[entry.level],
                      wrap ? "whitespace-pre-wrap break-all" : "truncate whitespace-pre",
                    )}
                  >
                    {entry.text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
