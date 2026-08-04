# TASK_SUMMARY — v0.2.2 → v1.0 gap closure

> **Date:** 2026-08-04 · **Version:** 0.2.2 · **Branch:** main

## Files Changed

**Function-coverage gaps (engine-light, additive):**
- `phronesisml/data/io.py`, `validation.py`, `etl.py`, `eda.py` — 17/14/18/9 engine-light data functions (new)
- `phronesisml/utils/resources.py` — 6 resource-estimation functions (new)
- `phronesisml/engines/recommend.py` — engine recommendation + capabilities matrix (new)
- `phronesisml/ml/target_detection/analysis.py` — target/feature analysis (new)
- `phronesisml/ml/feature_engineering/construction.py` — 7 feature-construction functions (new)
- `phronesisml/ml/evaluation/report.py`, `explainability/summary.py` — report + SHAP summary helpers (new)
- `phronesisml/ml/evaluation/metrics.py` — ROC/PR curves + `roc_auc`/`average_precision` via best-effort `predict_proba` (extended)
- `phronesisml/ml/reports/io.py` — `build_json_report`, `build_run_report` (new)
- All exported via package `__init__.py` files

**Tests added:** `test_data_io/validation/etl/eda`, `test_target_analysis`, `test_feature_construction`, `test_resources_engines`, `test_model_recommendation`, `test_evaluation_report`, `test_explanation_summary`, `test_artifact_storage`, `test_report_io`, `test_curve_metrics`, `test_run_report`, `test_determinism` (+110 → 269 total)

**Docs (Tranche 1, charter-mandated):** `{Architecture,Coding_Standards,Known_Issues,Testing,Workflow,Release_Process,Decision_Log,API_Contracts,Roadmap}.md`, `templates/`, `../docs/root_cause/README.md`, `../docs/runs/README.md`

## Why
Close every documented function-coverage gap in the master function matrix (19 sections after the v0.3.0 REST removal) and produce the charter-required engineering documentation set, so the SDK can be verified and reviewed end-to-end at the v1.0 quality gate.

## Architecture Impact
Additive engine-light modules under `data/`, `utils/`, `engines/`, `ml/*`; extended `metrics.py` and new `reports/io.py`; no changes to SDK/CLI/REST/LangGraph/public-API signatures. Fixed `metrics.py` mypy `no-any-return` (np.asarray). `ml/reports/io.py` `build_run_report` consumes `WorkflowState`-shaped dicts (full state-driven use deferred to Phase 2 per Decision Log).

## Tests Passed
`pytest -q` → **274 passed, 0 failed** (post v0.3.0 REST decommission) · `ruff check .` clean · `ruff format --check .` clean (121 files) · mypy: 50 errors, documented third-party-stub category only (was 51 before the 4 REST modules were removed)

## Coverage
- 12 new test files; curve metrics (4), run report (5), determinism contract (1)
- Determinism test proves identical metrics/best model/report across repeated runs; run identifier is the sole permitted difference (AI_QUALITY_GATE §1.3)

## Known Risks
- `ml/reports/io.py` `build_run_report` takes a state-like dict today; wiring to real `WorkflowState` happens in Phase 2 (documented in `Decision_Log.md`)
- mypy 50 stub-category errors remain (pandas/sklearn/mlflow/pyspark) — Phase 3 P3-5
- Full suite 59.6s; determinism test runs the full 11-stage pipeline twice (~9s) by design

## Performance Impact
None measured — all new modules are pure/engine-light helpers; curve points are capped and JSON-able.

## Future Work
Phase 2 roadmap (see `Roadmap.md`): schema validation (P2-1), user HPO grids (P2-8), data-drift API (P2-3), local run ledger (P2-4), PDF reports (P2-7). *(REST items P2-5/P2-6 removed with the REST subsystem in v0.3.0.)*
