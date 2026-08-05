# Root Cause Analysis — no `evaluate` CLI command

> **File:** `docs/root_cause/NEW-12_cli_missing_evaluate.md` · **Date:** 2026-08-05 · **ID:** NEW-12

## Issue Summary
The CLI exposes 12 commands (`analyze, capabilities, compare, doctor, explain,
info, profile, report, run, train, validate, version`) but no `evaluate`
subcommand. `phronesisml evaluate <data>` exits with code 2 ("No such command").
The SDK and simple API both expose `evaluate()` (SDK surface checks in QA Phase 2
passed 18/18 on `evaluate`), so the CLI surface is asymmetric with the library.

## Root Cause
The CLI command set was built around the pipeline stages (`run`, `train`,
`validate`, ...) and was never given an `evaluate` command after `evaluate()`
was added to the simple API. NEW-01 fixed the *library* export orphan
(`evaluate`/`evaluate_async` missing from `__all__`) but the CLI registry in
`interfaces/cli/app.py` was not updated in the same pass, so the surface
divergence moved one layer down: library ✔, CLI ✘.

## Affected Components
- `phronesisml/interfaces/cli/app.py` (command registry — no `evaluate` entry)

## Affected APIs
- CLI only. `Phronesis.evaluate`, `simple.evaluate`/`evaluate_async` work correctly.

## Affected SDK Functions
- none

## Affected CLI
- `phronesisml evaluate` — missing command (exit 2)

## Fix Applied
- None in this QA pass — recommended fix documented below. Not yet implemented.

### Recommended Fix (choke point)
Add an `evaluate` command to `interfaces/cli/app.py` that mirrors the existing
`train`/`explain` commands (same options: `--engine/-e`, `--nulls/-n`, `--cv`,
`--verbose`), calling `phronesisml.evaluate(data_path, engine=..., null_strategy=...,
cv=...)` and printing the primary metric (mirror the `_fail` handling used
elsewhere). Update the CLI docs (see NEW-14) to the full command list.

## Regression Test Added
- None yet. Required: invoke `phronesisml evaluate <csv>` and assert exit code 0
  with a printed metric; must fail pre-fix (exit 2), pass post-fix.

## Future Prevention
- Every public library function with a stage equivalent should have a CLI command
  review checklist item. When the simple API gains a function, run
  `phronesisml --help` and diff the command set against the function matrix
  (`project_docs/MASTER_FUNCTION_MATRIX.md`).
