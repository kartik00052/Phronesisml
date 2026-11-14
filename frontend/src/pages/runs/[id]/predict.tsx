import * as React from "react";
import { useOutletContext } from "react-router-dom";
import { Play, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { usePredictRun } from "@/hooks/use-runs";
import type { RunOutletContext } from "@/components/run/run-context";
import type { PredictionResponse } from "@/types/run";

export default function RunPredictPage() {
  const { run } = useOutletContext<RunOutletContext>();
  const [jsonInput, setJsonInput] = React.useState<string>("[\n  {\n    \n  }\n]");
  const [parseError, setParseError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<PredictionResponse | null>(null);

  const predictMutation = usePredictRun(run.id);

  const isModelReady = run.status === "completed" && Boolean(run.summary.bestModelType);

  const handlePredict = async () => {
    setParseError(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonInput);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "Invalid JSON syntax");
      return;
    }

    if (!Array.isArray(parsed) || parsed.length === 0) {
      setParseError('Input must be a non-empty array of objects, e.g. [{ "feature_name": 42 }]');
      return;
    }

    try {
      const data = await predictMutation.mutateAsync(parsed as Record<string, unknown>[]);
      setResult(data);
    } catch {
      // Error is captured by predictMutation.error
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Model Inference &amp; Prediction</h2>
        <p className="text-sm text-muted-foreground">
          Send sample feature payloads to execute real-time predictions against this run's fitted
          model.
        </p>
      </div>

      {!isModelReady ? (
        <Alert variant="warning" icon={AlertCircle}>
          <AlertTitle>Model Unavailable for Inference</AlertTitle>
          <AlertDescription className="text-xs text-muted-foreground">
            Predictions are only available once a run has completed successfully with a selected
            model.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Input Panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-primary" />
                Input Samples (JSON)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={12}
                className="w-full rounded-md border border-input bg-muted/40 p-3 font-mono text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder='[ { "alcohol": 13.2, "malic_acid": 2.7 } ]'
              />

              {parseError && (
                <Alert variant="destructive">
                  <p className="text-xs">{parseError}</p>
                </Alert>
              )}

              {predictMutation.isError && (
                <Alert variant="destructive">
                  <p className="text-xs">
                    {(predictMutation.error as Error)?.message || "Prediction request failed."}
                  </p>
                </Alert>
              )}

              <Button
                onClick={handlePredict}
                disabled={predictMutation.isPending}
                className="w-full gap-2"
              >
                <Play className="h-4 w-4" />
                {predictMutation.isPending ? "Predicting..." : "Run Inference"}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <CheckCircle2 className="h-4 w-4 text-success" />
                Inference Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className="space-y-4">
                  <div className="text-xs text-muted-foreground">
                    Model:{" "}
                    <span className="font-mono font-medium text-foreground">{result.modelType}</span>
                  </div>
                  <div className="overflow-hidden rounded-md border border-border">
                    <table className="w-full text-xs">
                      <thead className="bg-muted text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 text-left">#</th>
                          <th className="px-3 py-2 text-left">Prediction</th>
                          <th className="px-3 py-2 text-left">Probability</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {result.predictions.map((p, idx) => (
                          <tr key={idx} className="hover:bg-muted/50">
                            <td className="px-3 py-2 font-mono text-muted-foreground">{idx + 1}</td>
                            <td className="px-3 py-2 font-semibold text-foreground">
                              {String(p.prediction)}
                            </td>
                            <td className="px-3 py-2 font-mono text-muted-foreground">
                              {p.probability !== undefined && p.probability !== null
                                ? String(p.probability)
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                  <p className="text-xs">No prediction generated yet.</p>
                  <p className="mt-1 text-[11px]">
                    Provide sample JSON on the left and click "Run Inference".
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
