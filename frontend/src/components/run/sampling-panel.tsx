import { Filter, MemoryStick } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatNumber, formatPercent } from "@/lib/format";
import type { ResourceReport, SamplingInfo } from "@/types/run";

export function SamplingPanel({
  sampling,
  resource,
}: {
  sampling: SamplingInfo | null;
  resource: ResourceReport | null;
}) {
  if (!sampling && !resource) return null;
  const wasSampled = sampling?.was_sampled ?? false;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Filter className="size-4 text-muted-foreground" />
            Sampling
            {wasSampled ? <Badge variant="warning">Sampled</Badge> : <Badge variant="success">Full data</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {wasSampled ? (
            <>
              <p className="text-muted-foreground">
                {sampling?.sampling_method ?? "Auto"} sampling reduced the dataset to reduce runtime.
              </p>
              <p className="mt-1 flex items-center gap-4 text-muted-foreground">
                <span>
                  {formatNumber(sampling?.sample_rows ?? 0)} of {formatNumber(sampling?.original_rows ?? 0)} rows
                </span>
                <span>({formatPercent(sampling?.sampling_ratio ?? 0)})</span>
              </p>
              {sampling?.reason && (
                <p className="mt-1 text-xs text-muted-foreground">{sampling.reason}</p>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">
              No sampling applied — the dataset fits comfortably in memory.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MemoryStick className="size-4 text-muted-foreground" />
            Estimated resources
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {resource ? (
            <>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Encoded features</span>
                <span className="font-medium tabular-nums">{formatNumber(resource.estimated_encoded_features)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Peak memory</span>
                <span className="font-medium tabular-nums">{formatBytes(resource.estimated_memory_mb * 1024 * 1024)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estimated runtime</span>
                <span className="font-medium tabular-nums">
                  {resource.estimated_runtime_seconds > 60
                    ? `${Math.round(resource.estimated_runtime_seconds / 60)} min`
                    : `${Math.round(resource.estimated_runtime_seconds)} s`}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">SHAP memory</span>
                <span className="font-medium tabular-nums">{formatBytes(resource.estimated_shap_memory_mb * 1024 * 1024)}</span>
              </div>
            </>
          ) : (
            <p className="text-muted-foreground">Resource report pending.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}