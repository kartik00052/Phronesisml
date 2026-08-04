# Root Cause Analysis — preflight report key vocabulary drift

> **File:** `docs/root_cause/NEW-08_preflight_key_vocabulary.md` · **Date:** 2026-08-04 · **ID:** NEW-08

## Issue Summary
The target-detection preflight report used `n_rows`/`n_cols` while `WorkflowState`
uses `row_count`/`column_count`. Two vocabulary families for the same concept invited
reader confusion and key-mismatch bugs in downstream reporting.

## Root Cause
The preflight report predates (or ignored) the `WorkflowState` field-ownership map and
used the generic `n_rows`/`n_cols` naming instead of the state vocabulary.

## Affected Components
- `phronesisml/ml/target_detection/detector.py` (`validate_target_safety` return dict)
- consumers: `agents/target_detection/agent.py`, `workflow/nodes.py` (read only
  `safe`/`warnings`/`blockers` — unaffected)

## Affected APIs
- none public (preflight dict is internal metadata)

## Affected SDK Functions
- none

## Affected CLI
- none

## Affected REST (removed in v0.3.0)
- none (no longer applicable; the REST layer was removed in v0.3.0)

## Fix Applied
- Preflight return keys renamed `n_rows` → `row_count`, `n_cols` → `column_count`,
  matching `WorkflowState`.

## Regression Test Added
- Full suite 270 passed (no test asserted the old keys).

## Future Prevention
- Any report/dict that mirrors state must use `WorkflowState` field names verbatim.
- Add a helper (`_row_count`/`_column_count` in `ml/reports/io.py`) rather than
  introducing new key names.
