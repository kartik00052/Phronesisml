# PhronesisML — Workflow

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** How a run flows end-to-end + contributor workflow. Graph mechanics: `../docs/architecture.md`, `phronesisml/workflow/`. Doc reading order for contributors: `AI_QUALITY_GATE.md` → `project_state.json` → this file → relevant code.

## 1. The pipeline (11 stages)

```
upload → etl → validation → eda → target_detection → feature_engineering
→ model_selection → evaluation → explainability → reporting → storage
```

Routing: conditional routers return `"proceed"` or `"__end__"` (`workflow/router.py`). Storage has no router. Pre-flight sampling node can be inserted before EDA, FE, target detection, model selection, explainability.

Fail-safe: partial results are preserved when a later stage fails.

## 2. Data flow (field ownership)

| Stage | Writes to `WorkflowState` |
|---|---|
| upload | `raw_data` |
| etl | `processed_data` |
| validation | `validated_data` |
| eda | `data_profile` |
| target_detection | `target_column`, `task_type`, `target_detection_confidence`, `ambiguity_reason` |
| feature_engineering | `features`, `feature_names`, `feature_report` |
| model_selection | `best_pipeline`, `trained_model` |
| evaluation | `evaluation_report` |
| explainability | `explanation_report` |
| reporting | `final_report` |
| storage | artifacts on disk (`<base>/<run_id>/`) |
| metadata | `run_id`, `status` (populated since BUG-05) |

The full ownership map lives in `workflow/state.py`.

## 3. Graph caching

Compiled graphs are cached by `(agent_names, stages, agent_ids)`. Cached compile ≈ 4 µs vs ≈ 2.2 ms cold (`benchmarks/baseline.json`). `clear_all_caches()` is called on agent replacement in `clean()`/`recommend_model()`.

## 4. Contributor workflow

1. Branch: `feat/<name>` / `fix/<name>` / `docs/<name>` off `main`.
2. Read the gate + state file; ground every claim in the tree (§11 rules).
3. Implement; add regression tests for defects (§5 of gate).
4. Run the gate (§9): `ruff check .` → `ruff format --check .` → `mypy phronesisml/ --ignore-missing-imports` → `pytest -q`.
5. Update docs in the same change (see `Known_Issues.md` §3 for open drift to fix).
6. Regenerate `project_state.json`.
7. Conventional commit message; PR from feature branch.

## 5. Run-scoped dataset analysis report

Per the master charter, every pipeline execution produces a dataset analysis report under `../docs/runs/<run_id>.md` (dataset info, target/task, engine, sampling, models tried/rejected with reasons, best model + why, hyperparameters, metrics, SHAP explainer + feature importance, warnings/errors, runtime, artifacts, recommendations). See `phronesisml/ml/reports/` — `run_report` generator (Tranche 2).

## 6. Root-cause workflow

On any defect: reproduce → isolate the boundary → classify (correctness / contract / liveness / docs-packaging) → fix at the choke point (single source of truth) → prove with a regression test → check for siblings → record in `project_state.json` and `docs/root_cause/<issue>.md`.
