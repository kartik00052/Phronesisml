import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ENGINE_COLORS, TASK_COLORS, engineLabel } from "@/config/visual";
import { formatNumber } from "@/lib/format";
import type { DashboardStats } from "@/types/run";

export function EngineBreakdown({ stats, loading }: { stats?: DashboardStats; loading?: boolean }) {
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Runs by compute engine</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }
  const entries = Object.entries(stats?.engineBreakdown ?? {});
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Runs by compute engine</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([engine, count]) => {
          const pct = Math.round((count / total) * 100);
          return (
            <div key={engine} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 font-medium">
                  <span
                    className="inline-block size-2 rounded-sm"
                    style={{ backgroundColor: ENGINE_COLORS[engine] }}
                  />
                  {engineLabel(engine)}
                </span>
                <span className="text-muted-foreground">{formatNumber(count)}</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: ENGINE_COLORS[engine] }}
                />
              </div>
            </div>
          );
        })}
        {entries.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">No runs yet.</p>
        )}
      </CardContent>
    </Card>
  );
}

export function TaskBreakdown({ stats, loading }: { stats?: DashboardStats; loading?: boolean }) {
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Runs by task type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-5" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }
  const entries = Object.entries(stats?.taskBreakdown ?? {});
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Runs by task type</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {entries.map(([task, count]) => {
            const pct = Math.round((count / total) * 100);
            return (
              <div key={task} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block size-3 shrink-0 rounded-full"
                  style={{ backgroundColor: TASK_COLORS[task] }}
                />
                <span className="truncate capitalize text-foreground/90">{task.replace(/_/g, " ")}</span>
                <span className="ml-auto font-semibold tabular-nums">{formatNumber(count)}</span>
                <span className="w-8 text-right text-xs text-muted-foreground">{pct}%</span>
              </div>
            );
          })}
        </div>
        {entries.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">No runs yet.</p>
        )}
      </CardContent>
    </Card>
  );
}