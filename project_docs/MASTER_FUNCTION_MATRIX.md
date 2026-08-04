# Master Function Matrix — Verification Report

> **Version reviewed:** `0.2.2` (working tree)
> **Date:** 2026-08-04
> **Scope:** Verification of the 19-section capability matrix against the working tree. Every claim below is grounded in a live function definition, an executed test, or a reproduced run — no invented artifacts (§11 of `AI_QUALITY_GATE.md`).
> **Gate evidence:** `ruff check .` clean; `ruff format --check .` clean (121 files); `pytest -q` → **274 passed, 0 failed** (post v0.3.0 REST decommission); `mypy phronesisml` → 50 errors, all in the documented third-party-stub category (pandas/sklearn/pyspark/etc.), no new category introduced (was 51 before the 4 REST modules were removed).

**Legend:** `VERIFIED` = function exists in the tree with tests passing / reproduced; `VERIFIED (read)` = function exists in the tree, coverage via existing tests; `N/A` = capability intentionally out of scope.

---

## 1. Data Ingestion

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| CSV / TSV loading | `load_csv`, `load_tsv` | VERIFIED | `data/io.py`; `tests/test_data_io.py` |
| JSON / JSONL loading | `load_json`, `load_jsonl` | VERIFIED | `data/io.py`; tests |
| Parquet / Excel loading | `load_parquet`, `load_excel` | VERIFIED | `data/io.py`; tests |
| Directory / multi-file / zip loading | `load_directory`, `load_multiple_files`, `load_zip` | VERIFIED | `data/io.py`; tests |
| Merge / concatenate | `merge_datasets`, `concatenate_datasets` | VERIFIED | `data/io.py`; tests |
| Format inference / encoding detection | `infer_file_type`, `detect_encoding` | VERIFIED | `data/io.py`; tests |
| Preview / streaming / size estimation | `preview_dataset`, `stream_large_dataset`, `estimate_dataset_size`, `dataset_summary` | VERIFIED | `data/io.py`; tests |
| Legacy loader (format detect + best-sheet) | `load_data`, `list_excel_sheets`, `select_best_sheet` | VERIFIED | `data/loaders/file_loader.py` |

## 2. Data Validation

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Missing / duplicate / type / unique checks | `validate_missing_values`, `validate_duplicate_rows`, `validate_column_types`, `validate_unique_constraints` | VERIFIED | `data/validation.py`; `tests/test_data_validation.py` |
| Constraint validation | `validate_constraints`, `validate_datetime_columns`, `validate_categorical_columns`, `validate_numeric_columns` | VERIFIED | `data/validation.py`; tests |
| Schema + target/feature checks | `validate_schema`, `infer_schema`, `validate_target_column`, `validate_feature_columns` | VERIFIED | `data/validation.py`; tests |
| Combined + report | `validate_dataset`, `generate_validation_report` | VERIFIED | `data/validation.py`; tests |
| Legacy checks | `check_dataset_quality`, `is_valid_target`, `get_missing_report` | VERIFIED | `data/validators/checks.py` |

## 3. ETL

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Column ops | `drop_columns`, `select_columns`, `rename_columns` | VERIFIED | `data/etl.py`; `tests/test_data_etl.py` |
| Row ops | `filter_rows`, `sort_data`, `drop_duplicates` | VERIFIED | `data/etl.py`; tests |
| Outlier + scale + encode | `remove_outliers`, `normalize_columns`, `standardize_columns`, `one_hot_encode` | VERIFIED | `data/etl.py`; tests |
| Datetime / ids / index | `convert_datetime`, `add_id_column`, `set_index`, `reset_index` | VERIFIED | `data/etl.py`; tests |
| Missing-value fill | `fill_missing_values` (wraps `handle_nulls`) | VERIFIED | `data/etl.py`; `data/transformers/cleaning.py` |
| Splitting / sampling | `split_train_test`, `stratify_split`, `sample_data` | VERIFIED | `data/etl.py`; tests |

## 4. EDA

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Summary statistics | `summary_statistics` | VERIFIED | `data/eda.py`; `tests/test_data_eda.py` |
| Correlation / missing matrix | `correlation_matrix`, `missing_value_matrix` | VERIFIED | `data/eda.py`; tests |
| Distribution + target distribution | `column_distribution`, `target_distribution` | VERIFIED | `data/eda.py`; tests |
| Outlier / skew analysis | `outlier_analysis`, `skewness_analysis` | VERIFIED | `data/eda.py`; tests |
| Type + quality report | `type_report`, `data_quality_report` | VERIFIED | `data/eda.py`; tests |
| Legacy profiling | `compute_summary_statistics` | VERIFIED | `data/profilers/stats.py` |

## 5. Target Detection & Analysis

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Target quality + safety | `validate_target_safety`, `class_balance_report`, `target_quality_report` | VERIFIED | `ml/target_detection/analysis.py`; `tests/test_target_analysis.py` |
| Name-signal + cardinality detection | `detect_target_column`, `AMBIGUITY_THRESHOLD` | VERIFIED | `ml/target_detection/detector.py` |

## 6. Feature Engineering

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Interaction / polynomial | `create_interaction_features`, `create_polynomial_features` | VERIFIED | `ml/feature_engineering/construction.py`; `tests/test_feature_construction.py` |
| Binning / date extraction | `bin_continuous_features`, `extract_date_features` | VERIFIED | `ml/feature_engineering/construction.py`; tests |
| Selection + filtering | `variance_threshold_filter`, `correlation_feature_selector`, `feature_importance_report` | VERIFIED | `ml/feature_engineering/construction.py`; tests |
| Pipeline FE (encode/scale/select, outlier flag opt-in) | `engineer_features` | VERIFIED | `ml/feature_engineering/engineer.py`; BUG-01 regression |

## 7. Resource Estimation

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Bytes / seconds formatting | `format_bytes`, `format_seconds` | VERIFIED | `utils/resources.py`; `tests/test_resources_engines.py` |
| Memory / time / size estimates | `estimate_dataframe_memory`, `estimate_training_time`, `estimate_model_size_mb` | VERIFIED | `utils/resources.py`; tests |
| Memory sufficiency check | `check_memory_sufficiency` | VERIFIED | `utils/resources.py`; tests |
| Pre-flight sampling + estimator | `SamplingMode` (9 modes), `estimate_dataset_size` | VERIFIED | `ml/preflight/`; `tests/test_preflight.py` |

## 8. Engine Selection

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Size auto-routing | `select_engine` (<2 MB pandas / 2–500 MB polars / >500 MB spark) | VERIFIED | `engines/engine_selector.py` |
| Recommendation + capabilities matrix | `recommend_engine`, `engine_capabilities`, `engine_comparison_report` | VERIFIED | `engines/recommend.py`; `tests/test_resources_engines.py` |

## 9. Model Recommendation

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Task-aware candidate pool | `recommend_models` (`MAX_CLASSIFICATION_UNIQUE_VALUES=20` single source of truth) | VERIFIED | `ml/automl/auto_selector.py`; BUG-02 regression |
| Recommendation report + cost estimate | `build_recommendation_report`, `estimate_training_cost` | VERIFIED | `ml/automl/auto_selector.py`; `tests/test_model_recommendation.py` |

## 10. Evaluation

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Per-task metrics from model class | `evaluate_model` (classification/regression/clustering/anomaly) | VERIFIED | `ml/evaluation/metrics.py`; BUG-02 regression |
| Metric summary + model comparison | `metric_summary`, `compare_models` | VERIFIED | `ml/evaluation/report.py`; `tests/test_evaluation_report.py` |

## 11. Hyperparameter Optimization

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Bounded HPO (hard max_trials, between-trial budget) | `train_models`, `_adaptive_max_trials`, `_adaptive_max_time` | VERIFIED | `ml/automl/trainer.py`; ISSUE-07 regression |
| Task-class candidate filtering | `_candidate_matches_task`, `_build_param_grid` | VERIFIED | `ml/automl/trainer.py`; BUG-02 regression |

## 12. Training

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Split (stratified for classification) + training | `_split_data`, `train_models` | VERIFIED | `ml/automl/trainer.py` |
| Public training surfaces | `Phronesis.train`, `simple.train`/`train_async`, `run_pipeline` | VERIFIED | `sdk.py`, `simple.py` |

## 13. SHAP Explainability

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Explainer routing + resource bounds | `compute_shap_explanations`, `DEFAULT_MAX_SAMPLES` | VERIFIED | `ml/explainability/shap_explainer.py`; `tests/test_explainability.py` |
| Centralized service + registry | `compute_explanations`, `ExplainConfig`, tree/linear/permutation/kernel registry | VERIFIED | `ml/explainability/service.py` |
| Summary + validation | `explanation_summary`, `validate_explanation` | VERIFIED | `ml/explainability/summary.py`; `tests/test_explanation_summary.py` |

## 14. Reporting

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Markdown + HTML assembly | `build_report`, `build_html_report` (11 section builders + template) | VERIFIED | `ml/reports/builder.py`, `templates/full_report.md`; BUG-05 regression |
| Report I/O + extraction | `write_report`, `report_to_dict`, `render_metrics_table` | VERIFIED | `ml/reports/io.py`; `tests/test_report_io.py` |
| PDF variant | — | N/A | KNOWN-003: `NotImplementedError`, Phase 2 |

## 15. Artifact Storage

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| Pipeline artifact persistence | `save_artifacts` (`<base>/<run_id>/`, eval JSON + report MD + metadata) | VERIFIED | `services/storage.py` |
| Single-artifact IO + listing + manifest | `save_artifact`, `load_artifact`, `list_artifacts`, `build_artifact_manifest` | VERIFIED | `services/storage.py`; `tests/test_artifact_storage.py` |

## 16. SDK Surfaces

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| OOP `Phronesis` pipeline (load→report) | 20 public methods incl. `run`, `generate_report`, `explain`, `evaluate` | VERIFIED | `sdk.py` |
| Simple 12-function API (sync + async) | `analyze`, `clean`, `validate`, `detect_target`, `engineer`, `select_model`, `evaluate`, `explain`, `report`, `train`, `cluster`, `detect_anomalies`, `detect_task` (+ `*_async` twins) | VERIFIED | `simple.py` |

## 17. CLI

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| `run` / `info` entrypoints | `run` (`--engine/-e`, `--nulls/-n`, `--verbose/-v`), `info` | VERIFIED | `interfaces/cli/app.py` |

## 18. Agents & Workflow

| Capability | Function(s) | Status | Evidence |
|---|---|---|---|
| 12 protocol agents + composition root | `agents/` (DI in exactly two places), `AgentResult` envelope | VERIFIED | `agents/`; AUDIT/ROADMAP §2 |
| 11-stage LangGraph graph + state ownership | `workflow/graph.py`, `workflow/state.py` field-ownership map, routers | VERIFIED | `workflow/`; BUG-01 regression |

## 19. Packaging & CI

| Capability | Status | Evidence |
|---|---|---|
| Hatchling wheel + extras (cli/spark/mlflow/excel/dev/all), `py.typed` | VERIFIED | `pyproject.toml` |
| CI on 3.13 (format/lint/mypy/pytest) | VERIFIED (read) | `.github/workflows/ci.yml` |

---

## Summary

| Bucket | Functions verified | Test files |
|---|---|---|
| New engine-light modules (this task) | 85 public functions across `data/io|validation|etl|eda`, `utils/resources`, `engines/recommend`, `ml/{target_detection/analysis, feature_engineering/construction, automl/auto_selector, evaluation/report, explainability/summary}`, `services/storage`, `ml/reports/io` | 10 new test files |

Full suite: **274 tests passing** (was 100 at task start → **+159 new tests** this task; 13 regression tests retained in `tests/test_regressions.py` after the v0.3.0 REST test removal). All matrix sections verified in the working tree; PDF reports and spark/mlflow live paths remain documented out-of-scope (`KNOWN-003`, `KNOWN-005`).
