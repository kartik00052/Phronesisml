# Root Cause Analysis — resource_estimation.json is a placeholder in the SDK path

> **File:** `docs/root_cause/NEW-11_resource_estimation_placeholder.md` · **Date:** 2026-08-05 · **ID:** NEW-11

## Issue Summary
The artifact `resource_estimation.json` contains only
`{"status": "pre-flight resource estimation did not run"}` in every run produced
by the SDK (`Phronesis.run`), `simple.run`, and the CLI `run`/`train` commands —
even though the full `preflight` stage is present in the pipeline. Verified across
`BankChurners.csv`, `heart.csv`, and `diabetes_prediction_dataset.csv` (QA Phase 5).

## Root Cause
The sampling/preflight node is wired into the workflow graph at only one
composition root: `phronesisml/__init__.py:298-303`, where `run_pipeline` passes
`sampling_config` and an `engine` instance to `build_graph(...)`. The SDK path
bypasses this root: `Phronesis._run_stages` builds its graph with
`build_graph(agents, stages=needed)` (`sdk.py:514`) and never passes
`sampling_config`/`engine`, so `build_graph` omits the `sampling_node` and the
`ResourceEstimator` inside it never executes. The storage writer then emits the
hard-coded placeholder. All three public surfaces (SDK, `simple`, CLI) funnel
through `sdk._run_stages`, hence the placeholder everywhere.

## Affected Components
- `phronesisml/sdk.py:514` (`_run_stages` — build_graph without sampling config)
- `phronesisml/__init__.py:298-303` (`run_pipeline` — the only wired path)
- `phronesisml/workflow/graph.py` (`build_graph` + `_SAMPLING_PRECEDENCE_STAGES`)
- `phronesisml/workflow/sampling_node.py` (node that runs `ResourceEstimator`)

## Affected APIs
- `Phronesis.run`, `simple.run`, CLI `run`/`train` — artifact contract says
  `resource_estimation.json` should carry estimates

## Affected SDK Functions
- `Phronesis.run`, `Phronesis.train`, `simple.run`/`run_async`

## Affected CLI
- `phronesisml run <file>`, `phronesisml train <file>` (storage output)

## Fix Applied
- None in this QA pass — recommended fix documented below. Not yet implemented.

### Recommended Fix (choke point)
Make `build_graph`'s sampling wiring available to the SDK root. Pass the same
`sampling_config` + `engine` from `sdk._run_stages` (and `simple`) that
`run_pipeline` already passes:

```python
graph = build_graph(
    agents,
    stages=needed,
    sampling_config=self._config.sampling,
    engine=self._eng,
)
```

Note: `_run_stages` is called incrementally (once per method), so the sampling
node must be idempotent or only trigger on the stage set that includes `preflight`.

## Regression Test Added
- None yet. Required: run a full pipeline on a small CSV and assert
  `resource_estimation.json` contains real estimates (not the placeholder).
  Must fail pre-fix, pass post-fix.

## Future Prevention
- All composition roots that build the workflow graph must use one shared helper
  that resolves sampling config + engine, so no root can silently omit a node.
  Audit `grep build_graph(` across the repo after the fix.
