import * as React from "react";
import { ChevronLeft, ChevronRight, Info, Sparkles, Wand2 } from "lucide-react";

import { ChartCard } from "@/components/charts/chart-card";
import { FeatureImportanceChart } from "@/components/charts/feature-importance-chart";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useExplainability } from "@/hooks/use-run-extras";
import { formatNumber, formatScore } from "@/lib/format";
import type { ExplainabilityView, ShapPoint } from "@/types/explainability";

function Beeswarm({ points, featureCount = 12 }: { points: ShapPoint[]; featureCount?: number }) {
  const grouped = points.reduce<Record<string, ShapPoint[]>>((acc, p) => {
    (acc[p.feature] ??= []).push(p);
    return acc;
  }, {});
  const features = Object.keys(grouped).slice(0, featureCount);
  const maxAbs = Math.max(...features.flatMap((f) => grouped[f]).map((p) => Math.abs(p.shapValue)), 1e-9);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox="0 0 640 400"
        className="h-[400px] w-full min-w-120"
        role="img"
        aria-label="SHAP beeswarm plot: feature value vs SHAP contribution"
      >
        <line x1="320" y1="10" x2="320" y2="390" stroke="var(--border)" strokeDasharray="4 4" />
        {features.map((feature, i) => {
          const cy = 40 + i * ((400 - 80) / Math.max(features.length, 1));
          const pts = grouped[feature].slice(0, 80);
          return (
            <g key={feature}>
              {pts.map((p, j) => {
                const x = 320 + (p.shapValue / maxAbs) * 250;
                const y = cy + ((j % 3) - 1) * 12;
                return (
                  <circle
                    key={j}
                    cx={x}
                    cy={y}
                    r={2.6}
                    fill={p.featureValue < 0.5 ? "var(--info)" : "var(--warning)"}
                    opacity={0.85}
                  />
                );
              })}
              <text x={628} y={cy + 4} textAnchor="end" className="fill-muted-foreground" fontSize={11}>
                {feature.length > 16 ? `${feature.slice(0, 15)}…` : feature}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-warning" /> High feature value
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-info" /> Low feature value
        </span>
        <span>← lower SHAP value · higher SHAP value →</span>
      </div>
    </div>
  );
}

const provenanceItems = (d: ExplainabilityView) => [
  { label: "Explainer", value: d.report.explainer_type },
  { label: "Sampling", value: d.report.sampled ? `Sampled SHAP ${formatNumber(d.report.n_samples_used)}/${formatNumber(d.report.max_samples)} background` : "Full SHAP" },
  { label: "Features", value: `${formatNumber(d.report.n_features_used)} used in the explanation` },
  { label: "Base value", value: formatScore(d.baseValue) },
];

export function RunExplainabilityView({ runId }: { runId: string }) {
  const { data, isLoading, isError, error } = useExplainability(runId);
  const samples = data?.samples ?? null;
  const total = samples?.length ?? 1;
  const [rawIdx, setRawIdx] = React.useState<number | null>(null);
  React.useEffect(() => setRawIdx(null), [runId]);

  const idx = rawIdx ?? Math.min(data?.sampleId ?? 0, total - 1);
  const active = samples?.[idx] ?? {
    importance: data?.importance ?? [],
    beeswarm: data?.beeswarm ?? [],
    baseValue: data?.baseValue,
    prediction: data?.prediction,
    predictionLabel: data?.predictionLabel,
  };

  const step = (dir: -1 | 1) => setRawIdx(Math.min(total - 1, Math.max(0, idx + dir)));

  if (isLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 rounded-lg lg:col-span-1" />
        <Skeleton className="h-80 rounded-lg lg:col-span-2" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Could not load explanations"
        description={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }

  if (!data) {
    return (
      <EmptyState
        icon={<Sparkles className="size-6" />}
        title="No explanations available yet"
        description="The run may still be in progress, or the explainability stage was skipped. Explanations are generated from the best model after training."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-card px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Wand2 className="size-4 text-info" />
            Model explanations
          </h2>
          <div className="flex items-center gap-1.5">
            <Badge variant="outline">{data.report.explainer_type}</Badge>
            <Badge variant={data.report.sampled ? "secondary" : "success"}>
              {data.report.sampled ? "Sampled SHAP" : "Full SHAP"}
            </Badge>
          </div>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4">
          {provenanceItems(data).map((item) => (
            <div key={item.label} className="min-w-0">
              <dt className="text-muted-foreground">{item.label}</dt>
              <dd className="mt-0.5 truncate font-medium text-foreground">{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="size-8 p-0"
          onClick={() => step(-1)}
          disabled={idx === 0}
          aria-label="Previous sample"
        >
          <ChevronLeft className="size-4" />
        </Button>
        <span className="text-sm text-muted-foreground">
          Sample <span className="font-medium text-foreground">#{idx + 1}</span>
          {samples ? ` of ${total}` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          className="size-8 p-0"
          onClick={() => step(1)}
          disabled={!samples || idx === total - 1}
          aria-label="Next sample"
        >
          <ChevronRight className="size-4" />
        </Button>
        {active.baseValue != null && (
          <Badge variant="secondary">
            base {formatScore(active.baseValue)} → prediction {formatScore(active.prediction ?? 0)}
            {active.predictionLabel ? ` (${active.predictionLabel})` : ""}
          </Badge>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <ChartCard
          title="Feature importance"
          description="Mean absolute SHAP contribution per feature."
          className="lg:col-span-2"
        >
          <FeatureImportanceChart items={active.importance ?? []} height={360} maxFeatures={15} />
        </ChartCard>

        <ChartCard
          title="SHAP beeswarm"
          description="Per-sample attributions coloured by feature value."
          className="lg:col-span-3"
        >
          <Beeswarm points={active.beeswarm ?? []} />
        </ChartCard>
      </div>

      <Alert variant="info">
        <Info />
        <div className="text-xs">
          {formatNumber(data.report.n_samples_used)} of {formatNumber(data.report.max_samples)} background
          samples used across {data.report.n_features_used} features
          {data.report.sampled ? " (sampled SHAP)" : ""}. Attributions explain this model's behaviour and are
          not causal.
        </div>
      </Alert>
    </div>
  );
}