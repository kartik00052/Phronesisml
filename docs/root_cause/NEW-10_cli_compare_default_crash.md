# Root Cause Analysis — CLI `compare` crashes with no `-m` flag

> **File:** `docs/root_cause/NEW-10_cli_compare_default_crash.md` · **Date:** 2026-08-05 · **ID:** NEW-10

## Issue Summary
`phronesisml compare <data>` with no `--model/-m` flag crashes with
`TypeError: 'NoneType' object is not iterable` (exit code 1). The same call works
through the SDK (`Phronesis.compare()` / `simple.compare(data_path)`), so the CLI
is the only broken surface. Discovered in QA Phase 6.

## Root Cause
`phronesisml/interfaces/cli/app.py:403`:

```python
result = api_compare(data_path, list(model) or None, ...)
```

The `model` option is declared `typer.Option(None, "--model", "-m", ...)` with
`list[str]` annotation, so when the user omits `-m` typer passes `None`.
`list(None)` raises `TypeError` *before* the `or None` fallback can apply. The
intent was clearly "pass None when no models requested so the API auto-selects
from the catalog", but the guard is written backwards.

## Affected Components
- `phronesisml/interfaces/cli/app.py:385-407` (`compare` command)

## Affected APIs
- CLI `compare` command (only; SDK `Phronesis.compare` and `simple.compare` are unaffected)

## Affected SDK Functions
- none

## Affected CLI
- `phronesisml compare <file>` (default path) — crash; `-m random_forest` works

## Fix Applied
- None in this QA pass — recommended fix documented below. Not yet implemented.

### Recommended Fix (choke point)
`interfaces/cli/app.py:403` — guard before iterating:

```python
models = list(model) if model else None
result = api_compare(data_path, models, engine=engine, null_strategy=null_strategy, cv=cv)
```

## Regression Test Added
- None yet. Required: invoke `compare` with no `-m` (or assert the guard logic);
  must fail pre-fix with `'NoneType' object is not iterable` and pass post-fix
  producing a ranked `ModelComparison`.

## Future Prevention
- Every repeatable typer option that maps to `list[...]` with default `None` must
  be normalized with `list(x) if x else None` before use. Audit the other
  repeatable options in `app.py` for the same pattern.
