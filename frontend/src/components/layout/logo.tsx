import { cn } from "@/lib/cn";

export function Logo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden className="size-4">
          <circle cx="5" cy="5" r="2.6" fill="currentColor" />
          <circle cx="19" cy="6" r="2.6" fill="currentColor" />
          <circle cx="12" cy="18.5" r="2.6" fill="currentColor" />
          <path
            d="M5 7.6v6.4M19 8.6v6.4M5 15.6l13-2.7M19 8.6L7.5 3.9"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </div>
      {!compact && (
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-tight text-foreground">PhronesisML</span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            Agentic AutoML
          </span>
        </div>
      )}
    </div>
  );
}