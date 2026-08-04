# TASK_SUMMARY — <task title>

> **Date:** <date> · **Version:** <__version__> · **Branch:** <branch>

## Files Changed
- `<path>` — <what changed, one line>

## Why
<1–3 sentences: problem/goal grounded in project_state.json or code>

## Architecture Impact
<SDK / CLI / Workflow / Engine / Public API surface — or "none (engine-light, additive)">

## Tests Passed
`pytest -q` → **<N> passed, 0 failed** · `ruff check .` clean · `ruff format --check .` clean · mypy: <count> errors, documented stub category only

## Coverage
<test files added/changed + counts; which new functions are covered>

## Known Risks
<none | list with severity and mitigation>

## Performance Impact
<import time / runtime deltas if measured; else "none — pure/engine-light helpers">

## Future Work
<links to Roadmap items / next tranche>
