import * as React from "react";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Stepper, type Step } from "@/components/new-run/stepper";
import { DataSourceStep } from "@/components/new-run/data-source-step";
import { TargetTaskStep } from "@/components/new-run/target-task-step";
import { EngineStep } from "@/components/new-run/engine-step";
import { PipelineStep } from "@/components/new-run/pipeline-step";
import { ReviewStep } from "@/components/new-run/review-step";
import {
  wizardDefaults,
  wizardSchema,
  wizardToRequest,
  type WizardValues,
} from "@/components/new-run/form";
import { useDatasets, useEngineRecommendation } from "@/hooks/use-datasets";
import { useCreateRun } from "@/hooks/use-runs";
import { ENGINE_LABELS } from "@/config/status";
import { toApiError } from "@/api/client";
import type { EngineName } from "@/types/run";

const STEPS: Step[] = [
  { key: "dataset", label: "Dataset" },
  { key: "target", label: "Target & Task" },
  { key: "engine", label: "Engine" },
  { key: "pipeline", label: "Pipeline" },
  { key: "review", label: "Review & launch" },
];

const STEP_FIELDS: (keyof WizardValues)[][] = [
  ["datasetId"],
  [],
  ["engine", "nullStrategy"],
  ["pipelineDepth", "mode"],
  [],
];

export function NewRunWizard() {
  const [step, setStep] = React.useState(0);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const presetDatasetId = searchParams.get("datasetId")?.trim() || undefined;

  const form = useForm<WizardValues>({
    resolver: zodResolver(wizardSchema),
    defaultValues: { ...wizardDefaults, datasetId: presetDatasetId ?? wizardDefaults.datasetId },
    mode: "onChange",
  });

  const watchDatasetId = form.watch("datasetId");
  const watchEngine = form.watch("engine");
  const { data: datasets } = useDatasets({ pageSize: 50 });

  React.useEffect(() => {
    if (presetDatasetId && datasets && !datasets.items.some((d) => d.id === presetDatasetId)) {
      form.resetField("datasetId", { defaultValue: "" });
    }
  }, [presetDatasetId, datasets, form]);

  const dataset = datasets?.items.find((d) => d.id === watchDatasetId);

  const recommendation = useEngineRecommendation(
    dataset ? { bytes: dataset.sizeBytes, rows: dataset.rows, cols: dataset.columns } : null,
  );
  const resolvedEngine: EngineName =
    watchEngine === "auto"
      ? ((recommendation.data?.engine as EngineName) ?? "pandas")
      : watchEngine;

  const createRun = useCreateRun();

  const next = async () => {
    const stepFields = STEP_FIELDS[step];
    const valid = stepFields.length === 0 ? true : await form.trigger(stepFields);
    if (!valid) return;
    setStep((s) => Math.min(STEPS.length - 1, s + 1));
  };

  const back = () => setStep((s) => Math.max(0, s - 1));

  const submit = async () => {
    const valid = await form.trigger();
    if (!valid) return;
    createRun.mutate(wizardToRequest(form.getValues(), resolvedEngine), {
      onSuccess: (run) => navigate(`/runs/${run.id}`),
    });
  };

  return (
    <FormProvider {...form}>
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 overflow-x-auto pb-1">
          <Stepper steps={STEPS} current={step} />
        </div>

        <div className="rounded-lg border border-border bg-card p-5 shadow-card sm:p-6">
          {step === 0 && <DataSourceStep />}
          {step === 1 && <TargetTaskStep />}
          {step === 2 && <EngineStep />}
          {step === 3 && <PipelineStep />}
          {step === 4 && (
            <ReviewStep
              dataset={dataset}
              resolvedEngine={ENGINE_LABELS[resolvedEngine] ?? resolvedEngine}
            />
          )}

          {createRun.error && (
            <Alert variant="destructive" className="mt-5">
              {toApiError(createRun.error).message}
            </Alert>
          )}

          <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
            <Button variant="ghost" onClick={back} disabled={step === 0 || createRun.isPending}>
              <ArrowLeft className="size-4" />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => navigate("/runs")}
                disabled={createRun.isPending}
              >
                Cancel
              </Button>
              {step < STEPS.length - 1 ? (
                <Button onClick={next}>
                  Continue
                  <ArrowRight className="size-4" />
                </Button>
              ) : (
                <Button onClick={submit} disabled={createRun.isPending}>
                  {createRun.isPending ? (
                    <Sparkles className="size-4 animate-pulse" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  Launch run
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </FormProvider>
  );
}
