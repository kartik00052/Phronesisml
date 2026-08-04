# Root Cause Analysis — stage-order constant triplication

> **File:** `docs/root_cause/NEW-03_stage_order_triplication.md` · **Date:** 2026-08-04 · **ID:** NEW-03

## Issue Summary
The canonical 11-stage pipeline order was hard-coded in three places
(`_stages.py` as 12 lists, `__init__.py` `_FULL_PIPELINE_STAGES`, and
`workflow/graph.py` `PIPELINE_ORDER`), any of which could be edited independently
and silently break stage ordering for the other consumers.

## Root Cause
Stage order was copied into each consumer rather than derived from one constant.
`AI_QUALITY_GATE.md` §6 already declared `_stages.py` / `_FULL_PIPELINE_STAGES` as the
single source, but the later-added `PIPELINE_ORDER` (graph) and the re-export in
`__init__.py` duplicated the literal instead of referencing it.

## Affected Components
- `phronesisml/_stages.py`
- `phronesisml/__init__.py`
- `phronesisml/workflow/graph.py`
- consumers: `simple.py`; `interfaces/api/routes.py` (removed in v0.3.0)

## Affected APIs
- `run_pipeline(stages=None)` (full-stage default)

## Affected SDK Functions
- `Phronesis` stage methods; all simple-API stage sets

## Affected CLI
- none (delegates)

## Affected REST (removed in v0.3.0)
- Obsolete: the `/capabilities` pipeline_stages listing was removed with the REST layer
  in v0.3.0.

## Fix Applied
- `_stages.py` now defines `_FULL_PIPELINE_STAGES` exactly once.
- Every `_STAGES_*` constant is a slice/alias of it; `_STAGES_EVALUATE` aliases
  `_STAGES_SELECT_MODEL`, `_STAGES_ANOMALY` aliases `_STAGES_CLUSTER`.
- `workflow/graph.py` `PIPELINE_ORDER = list(_FULL_PIPELINE_STAGES)`.
- `__init__.py` re-exports `_FULL_PIPELINE_STAGES` from `_stages`.

## Regression Test Added
- Full suite 270 passed (includes determinism, preflight, report-IO, and API tests
  that exercise the graph and route ordering).

## Future Prevention
- Any new stage must be added in `_stages.py` only; graph and `run_pipeline` pick it up.
- Never reintroduce a literal stage list in `simple.py`, `sdk.py`, `__init__.py`,
  or `interfaces/`.
