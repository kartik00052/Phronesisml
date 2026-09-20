import * as React from "react";
import { useNavigate } from "react-router-dom";
import { CornerDownLeft, GitBranch, Plus, Search, Sparkles } from "lucide-react";

import { FLAT_NAV } from "@/config/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import { useThemeStore } from "@/stores/theme";
import { useRuns } from "@/hooks/use-runs";
import { RUN_STATUS_META } from "@/config/status";
import { truncateId } from "@/lib/format";

export function CommandMenu({
  open,
  setOpen,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const toggleTheme = useThemeStore((s) => s.toggle);

  const [query, setQuery] = React.useState("");
  const search = React.useDeferredValue(query.trim().toLowerCase());

  const { data: runResults } = useRuns(
    { search, pageSize: 5 },
    { enabled: search.length >= 2 },
  );

  const go = (to: string) => {
    setOpen(false);
    setQuery("");
    void navigate(to);
  };

  return (
    <CommandDialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setQuery(""); }}>
      <CommandInput
        placeholder="Search pages, runs, datasets, models…"
        value={query}
        onValueChange={setQuery}
        aria-label="Command menu"
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Actions">
          <CommandItem
            keywords={["new", "create", "launch", "experiment", "run"]}
            onSelect={() => go("/runs/new")}
          >
            <Plus />
            <span>Start a new run</span>
            <CommandShortcut>⌘N</CommandShortcut>
          </CommandItem>
          <CommandItem
            keywords={["dark", "light", "mode", "appearance", "theme"]}
            onSelect={() => toggleTheme()}
          >
            <Sparkles />
            <span>Toggle theme</span>
            <CommandShortcut>⌘⇧L</CommandShortcut>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />

        {search.length >= 2 && (
          <>
            <CommandGroup heading={`Runs matching “${search}”`}>
              {runResults?.items?.slice(0, 5).map((run) => (
                <CommandItem
                  key={run.id}
                  value={`run-${run.id}`}
                  keywords={[run.datasetName, run.id, run.datasetPath, run.status]}
                  onSelect={() => go(`/runs/${run.id}`)}
                >
                  <GitBranch />
                  <span className="min-w-0 truncate">{run.datasetName}</span>
                  <span className="truncate font-mono text-xs text-muted-foreground">
                    {truncateId(run.id)}
                  </span>
                  <CommandShortcut>{RUN_STATUS_META[run.status].label}</CommandShortcut>
                </CommandItem>
              ))}
              {!runResults?.items?.length && (
                <CommandItem value={`no-runs-${search}`} disabled>
                  No runs match this query.
                </CommandItem>
              )}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {FLAT_NAV.map((item) => (
          <CommandGroup heading={item.title} key={item.href}>
            <CommandItem
              value={item.title}
              keywords={item.keywords}
              onSelect={() => go(item.href)}
            >
              <item.icon />
              <span>{item.title}</span>
            </CommandItem>
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

export function CommandMenuTrigger({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "group flex h-8 w-full max-w-56 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-sm text-muted-foreground transition-colors hover:border-border-strong hover:bg-surface-muted " +
        (className ?? "")
      }
    >
      <Search className="size-3.5 shrink-0" />
      <span className="truncate">Search…</span>
      <span className="ml-auto hidden items-center gap-1 rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground lg:flex">
        <CornerDownLeft className="size-2.5" />K
      </span>
    </button>
  );
}