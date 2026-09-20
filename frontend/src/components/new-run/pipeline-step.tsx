import { useController, useFormContext } from "react-hook-form";
import { ChevronDown, SlidersHorizontal } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { STAGE_META, STAGE_SLICES } from "@/config/pipeline";
import { RUN_MODE_META, type WizardValues } from "@/components/new-run/form";

export function PipelineStep() {
  const { control, watch, setValue } = useFormContext<WizardValues>();
  const depthController = useController({ control, name: "pipelineDepth" });
  const modeController = useController({ control, name: "mode" });
  const advancedOpen = watch("advanced");

  const toggleAdvanced = () => setValue("advanced", !advancedOpen);

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm">Pipeline depth</Label>
          <span className="text-xs text-muted-foreground">How far the workflow should run</span>
        </div>
        <RadioGroup
          value={depthController.field.value}
          onValueChange={depthController.field.onChange}
          className="grid gap-2 sm:grid-cols-2"
        >
          {[...STAGE_SLICES].reverse().map((slice) => (
            <label
              key={slice.key}
              className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                depthController.field.value === slice.key
                  ? "border-ring bg-primary/5 ring-1 ring-ring"
                  : "border-border bg-surface hover:border-border-strong"
              }`}
            >
              <RadioGroupItem value={slice.key} id={`depth-${slice.key}`} className="mt-0.5" />
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">{slice.label}</span>
                  <span className="text-xs text-muted-foreground">{slice.api}</span>
                </span>
                <span className="mt-1 flex flex-wrap gap-1">
                  {slice.stages.map((s) => (
                    <span
                      key={s}
                      className="rounded border border-border bg-muted/40 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
                    >
                      {STAGE_META[s].shortLabel}
                    </span>
                  ))}
                </span>
              </span>
            </label>
          ))}
        </RadioGroup>
      </section>

      <Separator />

      <section className="space-y-3">
        <Label className="text-sm">Execution mode</Label>
        <RadioGroup
          value={modeController.field.value}
          onValueChange={modeController.field.onChange}
          className="grid gap-2 sm:grid-cols-3"
        >
          {(Object.keys(RUN_MODE_META) as (keyof typeof RUN_MODE_META)[]).map((mode) => (
            <label
              key={mode}
              className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                modeController.field.value === mode
                  ? "border-ring bg-primary/5 ring-1 ring-ring"
                  : "border-border bg-surface hover:border-border-strong"
              }`}
            >
              <RadioGroupItem value={mode} id={`mode-${mode}`} className="mt-0.5" />
              <span className="min-w-0">
                <span className="block capitalize text-sm font-medium text-foreground">{RUN_MODE_META[mode].label}</span>
                <span className="block text-xs text-muted-foreground">{RUN_MODE_META[mode].description}</span>
              </span>
            </label>
          ))}
        </RadioGroup>
      </section>

      <Separator />

      <section className="space-y-3">
        <button
          type="button"
          onClick={toggleAdvanced}
          className="flex w-full items-center justify-between rounded-md px-1 py-1 text-sm font-medium text-foreground hover:text-primary"
        >
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="size-4" />
            Advanced options
          </span>
          <ChevronDown className={`size-4 transition-transform ${advancedOpen ? "rotate-180" : ""}`} />
        </button>
        {advancedOpen && <AdvancedFields />}
      </section>
    </div>
  );
}

function AdvancedField({
  name,
  label,
  placeholder,
  help,
}: {
  name: keyof WizardValues;
  label: string;
  placeholder: string;
  help?: string;
}) {
  const { control } = useFormContext<WizardValues>();
  const field = useController({ control, name });
  return (
    <div>
      <Label htmlFor={name} className="mb-1.5 block text-xs text-muted-foreground">
        {label}
      </Label>
      <Input
        id={name}
        value={(field.field.value as string) ?? ""}
        onChange={(e) => field.field.onChange(e.target.value)}
        placeholder={placeholder}
        className="h-8 text-sm"
      />
      {help && <p className="mt-1 text-xs text-muted-foreground">{help}</p>}
    </div>
  );
}

function AdvancedFields() {
  return (
    <div className="grid gap-4 rounded-md border border-border bg-surface/60 p-4 sm:grid-cols-2">
      <AdvancedField name="cv" label="CV folds" placeholder="5" />
      <AdvancedField name="maxTrials" label="Max HPO trials" placeholder="mode default" />
      <AdvancedField name="modelType" label="Model family (optional)" placeholder="auto" />
      <AdvancedField name="varianceThreshold" label="Variance threshold" placeholder="0.01" />
      <AdvancedField name="correlationThreshold" label="Correlation threshold" placeholder="0.98" />
      <AdvancedField name="minFeatures" label="Min features" placeholder="2" />
    </div>
  );
}