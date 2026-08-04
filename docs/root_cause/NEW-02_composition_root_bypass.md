# Root Cause Analysis — composition-root bypass in simple.py

> **File:** `docs/root_cause/NEW-02_composition_root_bypass.md` · **Date:** 2026-08-04 · **ID:** NEW-02

## Issue Summary
`select_model_async(cv=…)` and `train_async(cv=…, model_type=…)` constructed a
`ModelSelectionAgent` directly and overwrote `ml._agents["model_selection"]`,
bypassing the canonical composition root (`agents/compose.py`).

## Root Cause
The `cv`/`model_type` tuning knobs were treated as a special case needing a different
agent, so the simple API reached past the `Phronesis` abstraction instead of expressing
configuration through the composition root. This violated AI_QUALITY_GATE §2.7
(single composition point) and made future agent wiring changes unsafe.

## Affected Components
- `phronesisml/simple.py` (`select_model_async`, `train_async`)
- `phronesisml/sdk.py` (`Phronesis`, `_make_agents`)
- `phronesisml/agents/compose.py` (`compose_agents`)

## Affected APIs
- `select_model` / `select_model_async` / `train` / `train_async` with `cv`/`model_type`

## Affected SDK Functions
- `Phronesis.__init__` (new `agent_overrides` parameter, additive)

## Affected CLI
- none (delegates to the same simple functions)

## Affected REST (removed in v0.3.0)
- none (no longer applicable; the REST layer was removed in v0.3.0)

## Fix Applied
- `compose_agents` gained a validated `agent_overrides` mapping (constructor-kwarg
  overrides merged per agent; unknown names raise `ValueError`).
- `Phronesis` stores and forwards `agent_overrides` through `_make_agents`.
- `simple.py` passes `{"model_selection": {"cv": …}}` / `{"model_type": …}` through
  the constructor — all instantiation now flows through the composition root.

## Regression Test Added
- Smoke run with `select_model(cv=3)`, `evaluate(cv=3)`, `evaluate_async(cv=3)`,
  and `Phronesis(..., agent_overrides={"model_selection": {"cv": 5}})` — all pass;
  agent map still contains all 11 agents. Full suite 270 passed.

## Future Prevention
- Audit new simple-API kwargs: any knobs affecting agents must be expressed via
  config or `agent_overrides`, never by mutating `_agents` in callers.
- Keep `compose_agents` the only place importing concrete agent classes.
