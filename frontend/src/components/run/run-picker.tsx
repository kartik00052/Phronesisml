import * as React from "react";
import { ChevronsUpDown, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useRuns } from "@/hooks/use-runs";
import { RUN_STATUS_META } from "@/config/status";
import { cn } from "@/lib/cn";
import { truncateId } from "@/lib/format";

/** Searchable run selector used by run-scoped pages (models, explainability, reports, artifacts). */
export function RunPicker({
  value,
  onChange,
  showStatus = false,
}: {
  value: string;
  onChange: (runId: string) => void;
  showStatus?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const search = React.useDeferredValue(query.trim().toLowerCase());

  const { data, isLoading } = useRuns({ search, pageSize: 100 });
  const runs = data?.items ?? [];
  const selected = runs.find((r) => r.id === value);

  if (isLoading) return <Skeleton className="h-9 w-64" />;

  if (runs.length === 0 && !selected) {
    return (
      <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted-foreground">
        No runs available.
      </div>
    );
  }

  return (
    <Popover open={open} onOpenChange={(v) => { setOpen(v); if (!v) setQuery(""); }}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="h-9 w-72 justify-between gap-2 font-normal"
        >
          <span className="min-w-0 flex-1 truncate text-left">
            {selected ? selected.datasetName : "Select a run…"}
          </span>
          {selected && (
            <span className="shrink-0 font-mono text-xs text-muted-foreground">
              {truncateId(selected.id)}
            </span>
          )}
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-0">
        <Command shouldFilter={false}>
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Search className="size-3.5 shrink-0 opacity-50" />
            <CommandInput
              value={query}
              onValueChange={setQuery}
              placeholder="Search runs…"
              className="h-9 border-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              aria-label="Search runs"
            />
          </div>
          <CommandList className="max-h-72">
            <CommandEmpty>No runs found.</CommandEmpty>
            <CommandGroup>
              {runs.map((run) => (
                <CommandItem
                  key={run.id}
                  value={run.id}
                  keywords={[run.datasetName, run.id, run.datasetPath, run.status]}
                  onSelect={() => {
                    onChange(run.id);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <span className="min-w-0 flex-1 truncate">{run.datasetName}</span>
                  {showStatus && (
                    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span className={cn("size-1.5 rounded-full", RUN_STATUS_META[run.status].dotClass)} />
                      {run.status}
                    </span>
                  )}
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {truncateId(run.id)}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}