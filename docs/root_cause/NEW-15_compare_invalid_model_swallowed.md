# Root Cause Analysis — `compare()` silently drops invalid model names (v0.3.0)

> **File:** `docs/root_cause/NEW-15_compare_invalid_model_swallowed.md` · **Date:** 2026-08-05 · **ID:** NEW-15

## Issue Summary
`compare()` (SDK method, `simple.compare`, and the CLI `compare` command) with an
unknown model type did **not** raise. The model-selection agent correctly returned
`AgentResult(success=False, error="Model type 'xyz' not found. Available: [...]")`,
but the SDK caught the resulting `WorkflowError` and converted it into a metrics-less
entry that was then filtered out of the ranking. The invalid request was silently
dropped — only a log line recorded the failure. Users received a "successful"
comparison that silently omitted the requested model.

## Root Cause
In `phronesisml/sdk.py`, `_compare_one_core()` wrapped the nested pipeline run in a
broad `try/except WorkflowError` and returned a sentinel dict
(`{"model": ..., "metrics": {}, "error": ...}`). `_compare_core()` then built the
`evaluations` list with `if m.get("metrics")`, so the empty-metrics sentinel was
silently filtered out. Both a user validation error (unknown model name) and a
genuine training failure were converted into a hidden fallback, violating the
"no hidden fallbacks" rule.

## Reproduction Steps
```python
from phronesisml import compare

compare("data.csv", ["definitely_not_a_model"])
# Expected: WorkflowError.  Actual: returns a ModelComparison with the
# invalid model absent from ranking, no exception.
```

## Affected Components
- `phronesisml/sdk.py` — `_compare_one_core()`, `_compare_core()`
- `phronesisml/simple.py` — `compare()` / `compare_async()`
- `phronesisml/interfaces/cli/app.py` — `compare` command (exit code 0 on invalid model)

## Affected Public APIs
- `Phronesis.compare(model_types)`
- `simple.compare(path, model_types)`
- CLI `phronesisml compare -m <model>`

## Affected LangGraph Nodes
- `model_selection` agent node (raises `AgentError` → `WorkflowError`), which was
  previously caught by the SDK instead of propagating to the caller.

## Architecture Impact
Low. The LangGraph workflow and its error propagation are unchanged; the SDK
orchestration layer no longer suppresses `WorkflowError` from the graph. Error
semantics for `compare` are now consistent with the rest of the SDK: a failing
agent propagates to the caller.

## Fix Applied
Removed the broad `try/except WorkflowError` in `_compare_one_core()` so the
model-selection error propagates to the caller as a `WorkflowError` with the
agent's message ("Model type 'xyz' not found. Available: [...]"). `simple.compare`,
`Phronesis.compare`, and the CLI `compare` command now surface the failure
(CLI exits non-zero via `_fail`). No public signatures changed; no behavior other
than the hidden fallback was modified.

## Regression Test Added
`tests/test_regressions_v030.py`:
- `test_new15_compare_invalid_model_raises` — asserts `WorkflowError` with
  "not found" in the message. Verified to **fail before** the fix (returned a
  comparison) and **pass after**.
- `test_new15_compare_invalid_model_cli_nonzero` — asserts CLI exit code is
  non-zero and the message is printed.

## Future Prevention
- Keep `_compare_one_core` free of broad exception conversion; any per-candidate
  failure must either propagate or be explicitly documented as tolerated.
- Add a code-review gate that flags `except ...: return` fallbacks that drop
  error context in SDK orchestration layers.

## Verification Evidence
- Pre-fix: `simple.compare(ds, ["not_a_model_xyz"])` returned silently (no raise).
- Post-fix: raises `WorkflowError` ("Model type 'not_a_model_xyz' not found.
  Available: [...]"); valid compare (`["random_forest"]`) and default compare
  (`model_types=None`) still return correct rankings.
- `tests/test_regressions_v030.py::test_new15_*` 2 passed after fix, failed before.
- Full regression suite: 318 + 2 = 320 passed, 0 failed.
