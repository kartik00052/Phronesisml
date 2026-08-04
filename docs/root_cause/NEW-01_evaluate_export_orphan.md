# Root Cause Analysis — evaluate_async export orphan

> **File:** `docs/root_cause/NEW-01_evaluate_export_orphan.md` · **Date:** 2026-08-04 · **ID:** NEW-01

## Issue Summary
`phronesisml.evaluate_async` was implemented and used by the REST layer but missing
from the public namespace (`__all__` / `_LAZY_IMPORTS`), and no sync `evaluate`
existed — the API surface silently diverged from the implementation.

## Root Cause
Export symmetry was maintained by convention, not by a guard. When `evaluate_async`
was added to `simple.py`, the corresponding `__init__.py` registries were not updated,
and the sync/async pair convention was not enforced.

## Affected Components
- `phronesisml/simple.py` (`evaluate_async`)
- `phronesisml/__init__.py` (`__all__`, `_LAZY_IMPORTS`)
- `phronesisml/interfaces/api/routes.py:396` (only consumer; removed in v0.3.0)

## Affected APIs
- Public simple API: `evaluate`, `evaluate_async`

## Affected SDK Functions
- none

## Affected CLI
- none

## Affected REST (removed in v0.3.0)
- Obsolete: the `/train` job path that resolved `evaluate_async` by name was removed
  with the REST layer in v0.3.0.

## Fix Applied
- Added sync `evaluate()` to `simple.py`; `evaluate_async` now delegates to
  `select_model_async` (identical stage set `_STAGES_SELECT_MODEL == _STAGES_EVALUATE`).
- Exported both names in `__all__` and `_LAZY_IMPORTS`.
- Single source of truth for stage sets: `_stages.py` (RCA NEW-03).

## Regression Test Added
- Smoke-verified `evaluate`/`evaluate_async`/`select_model` with `cv=3` (sync + async).
- Full suite: 270 passed. A dedicated API-contract test asserting
  `__all__` ↔ `_LAZY_IMPORTS` symmetry is recommended (see `../../project_docs/PUBLIC_API_AUDIT.md` §4).

## Future Prevention
- Add an API-contract test iterating `__all__` and resolving every name.
- Prefer shared stage-set constants over bespoke lists so alias functions delegate
  instead of re-implementing.
