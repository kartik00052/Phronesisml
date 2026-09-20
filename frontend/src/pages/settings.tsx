import { CheckCircle2, Info, Monitor, Moon, Sun, XCircle } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useThemeStore, type ThemePreference } from "@/stores/theme";
import { useCapabilities, useHealth } from "@/hooks/use-health";
import { getBaseUrl } from "@/api/client";
import { isDemoMode } from "@/mocks";

const THEME_OPTIONS: { value: ThemePreference; label: string; icon: React.ReactNode }[] = [
  { value: "light", label: "Light", icon: <Sun className="size-4" /> },
  { value: "dark", label: "Dark", icon: <Moon className="size-4" /> },
  { value: "system", label: "System", icon: <Monitor className="size-4" /> },
];

export default function SettingsPage() {
  const { preference, setPreference } = useThemeStore();
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: capabilities } = useCapabilities();

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Settings" description="Application, theme, and connection preferences." />

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Theme</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={preference}
            onValueChange={(v) => setPreference(v as ThemePreference)}
            className="grid gap-2 sm:grid-cols-3"
          >
            {THEME_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                  preference === opt.value
                    ? "border-ring bg-primary/5 ring-1 ring-ring"
                    : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                <RadioGroupItem value={opt.value} id={`theme-${opt.value}`} className="mt-0.5" />
                <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                  {opt.icon}
                  {opt.label}
                </span>
              </label>
            ))}
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Info className="size-4 text-muted-foreground" />
            Connection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Data source</span>
            <Badge variant={isDemoMode() ? "warning" : "success"}>
              {isDemoMode() ? "Demo (in-browser mocks)" : "Real backend"}
            </Badge>
          </div>
          {!isDemoMode() && (
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">API base URL</span>
              <span className="font-mono text-xs">{getBaseUrl()}</span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Platform health</CardTitle>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          ) : health ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant={health.status === "ok" ? "success" : "warning"}>
                  {health.status === "ok" ? "Healthy" : "Degraded"}
                </Badge>
                <span className="text-muted-foreground">
                  PhronesisML <span className="font-mono">{health.version}</span>
                </span>
                <span className="text-muted-foreground">· Python {health.python}</span>
              </div>
              <Separator />
              <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                {Object.entries(health.dependencies).map(([name, dep]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between gap-2 rounded-md px-2 py-1 hover:bg-muted/30"
                  >
                    <span className="truncate font-mono text-xs text-foreground">{name}</span>
                    <span className="flex items-center gap-1.5 text-xs">
                      {dep.installed ? (
                        <>
                          <CheckCircle2 className="size-3.5 text-success" />
                          <span className="text-muted-foreground">{dep.version ?? "ok"}</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="size-3.5 text-danger" />
                          <span className="text-danger">missing</span>
                        </>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Health report unavailable.</p>
          )}
        </CardContent>
      </Card>

      {capabilities && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Capabilities</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Task types
              </p>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.task_types.map((t) => (
                  <Badge key={t} variant="outline">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Compute engines
              </p>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.engines.map((e) => (
                  <Badge key={e} variant="outline">
                    {e}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Explainers
              </p>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.explainers.map((e) => (
                  <Badge key={e} variant="outline">
                    {e}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {capabilities?.optional_models && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Optional model backends</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {capabilities.optional_models.map((m) => (
              <div
                key={m.name}
                className="flex items-center justify-between gap-2 rounded-md border border-border p-2.5"
              >
                <div className="min-w-0">
                  <p className="font-mono text-xs font-medium text-foreground">{m.name}</p>
                  {m.installed ? (
                    <p className="text-xs text-success">
                      {m.version ? `installed ${m.version}` : "installed"}
                    </p>
                  ) : (
                    <p className="truncate text-xs text-muted-foreground" title={m.reason ?? ""}>
                      not installed{m.reason ? ` — ${m.reason}` : ""}
                    </p>
                  )}
                </div>
                {m.installed ? (
                  <CheckCircle2 className="size-4 shrink-0 text-success" />
                ) : (
                  <XCircle className="size-4 shrink-0 text-danger" />
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
