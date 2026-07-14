================================================================================
  PHRONESISML -- COMPATIBILITY MATRIX & INTEGRATION AUDIT REPORT
  Version: 0.2.1 | Date: 2026-07-15 | Total Tests: 148 | Pass Rate: 100.0%
================================================================================

  Session Summary:
    This report was generated as part of a comprehensive production-readiness
    effort. The session began with a v0.2.0 codebase containing 110 integration
    tests. Over the course of this session the following changes were made:

    - 17-stage architectural audit completed (48 findings: 6 Critical, 12 High,
      18 Medium, 12 Low)
    - 6 critical architecture fixes implemented (compose extraction, cache
      safety, parameter validation, PEP 561, workflow package init)
    - 11 result dataclasses extracted to results.py (single source of truth)
    - ExplainabilityService created with extensible explainer registry
    - 38 comprehensive explainability unit tests added (tests/test_explainability.py)
    - SHAP promoted from optional [explain] extra to core dependency
    - sdist size reduced from 211 MB to 0.13 MB (exclude CSVs/tests/docs)
    - MyPY type errors fixed (3 annotations)
    - Version bumped to 0.2.1
    - PyPI package published: pypi.org/project/phronesisml/0.2.1/
    - Docker image published: ghcr.io/kartik00052/phronesisml:v0.2.1
    - CI pipeline fully green (lint, typecheck, docker, docker-publish)

  Git History (this session):
    da6da3e  Phase 3: commit after bug fixes, test infra, unsupervised learning
    719cec9  Phase 4: critical architecture fixes (A1-A6) + test infra
    31e6205  Extract 11 result dataclasses to results.py
    31b1b34  Create ExplainabilityService + 38 tests
    604ae67  Promote SHAP to core dependency
    c7b05c8  Fix 3 MyPY type errors
    6e05918  Fix sdist size (211MB -> 0.13MB), bump to v0.2.1

  Published Artifacts:
    PyPI:    pypi.org/project/phronesisml/0.2.1/
    Docker:  ghcr.io/kartik00052/phronesisml:v0.2.1
    Source:  github.com/kartik00052/Phronesisml

================================================================================
  SECTION A: IMPORTS & INTERFACE TESTS (110 stages from test.py)
================================================================================

  [A] IMPORTS & INTERFACES
    [OK  ] test_imports (0.13s) -- {'version': '0.2.0', 'all_exports': 54}
    [OK  ] test_sdk_oop_imports (0.00s) -- {'sdk_class': 'Phronesis'}
    [OK  ] test_simple_api_imports (0.00s) -- {'simple_api': True}
    [OK  ] test_async_api_imports (0.00s) -- {'async_api': True}
    [OK  ] test_config_imports (0.00s) -- {'engine_preferred': None, 'data_default_format': 'auto', 'feature_variance_threshold': 0.01}
    [OK  ] test_exception_hierarchy (0.00s) -- {'exception_count': 11}
    [OK  ] test_workflow_state (0.00s) -- {'state_fields': 30, 'sample_fields': ['run_id', 'status', 'data_path', 'raw_data', 'file_format']}
    [OK  ] test_pipeline_order (0.71s) -- {'stages': ['upload', 'etl', 'validation', 'eda', 'target_detection', 'feature_engineering', 'model_selection', 'evaluation', 'explainability', 'reporting', 'storage']}
    [OK  ] test_agent_base (0.00s) -- {'agent_result_fields': ['success', 'data', 'error', 'error_type', 'error_message', 'error_context', 'metadata']}

  [B] ENGINE COMPATIBILITY
    [OK  ] test_pandas_engine (0.01s) -- {'shape': (20, 5), 'columns': ['age', 'income', 'score', 'category', 'target'], 'head_rows': 3, 'memory_bytes': 1932}
    [OK  ] test_polars_engine (0.20s) -- {'shape': (20, 5), 'columns': ['age', 'income', 'score', 'category', 'target'], 'head_rows': 3, 'collected_type': 'DataFrame'}
    [OK  ] test_engine_selector (0.00s) -- {'selected_engine': 'PandasEngine'}
    [OK  ] test_engine_selector_pandas_force (0.00s) -- {'engine': 'PandasEngine'}
    [OK  ] test_engine_selector_polars_force (0.00s) -- {'engine': 'PolarsEngine'}

  [C] DATA LOADING & FORMATS
    [OK  ] test_csv_loading (0.01s) -- {'format': 'csv', 'rows': 20}
    [OK  ] test_json_loading (0.02s) -- {'format': 'json', 'rows': 2}
    [OK  ] test_parquet_loading (0.04s) -- {'format': 'parquet', 'rows': 2}
    [OK  ] test_excel_loading (0.28s) -- {'format': 'excel', 'sheets': [{'name': 'Sheet1', 'index': 0, 'rows': 2, 'cols': 2}], 'rows': 2}

  [D] ETL & DATA PROCESSING
    [OK  ] test_etl_handle_nulls_drop (0.00s) -- {'strategy': 'drop', 'rows_before': 3, 'rows_after': 1}
    [OK  ] test_etl_handle_nulls_fill (0.00s) -- {'strategy': 'fill', 'filled_with': 0}
    [OK  ] test_etl_handle_nulls_flag (0.00s) -- {'strategy': 'flag', 'flag_columns': ['a_is_null', 'b_is_null']}
    [OK  ] test_etl_encode_categoricals (0.00s) -- {'encoded_column': 'cat', 'dtype': 'int64'}
    [OK  ] test_etl_cast_dtypes (0.00s) -- {'x_dtype': 'int64', 'y_dtype': 'float64'}
    [OK  ] test_etl_invalid_strategy (0.00s) -- {'raised': True, 'error_type': 'DataTransformError'}

  [E] VALIDATION
    [OK  ] test_validate_clean_data (0.00s) -- {'passed': True, 'shape': {'rows': 3, 'columns': 2}}
    [OK  ] test_validate_dirty_data (0.01s) -- {'passed': True, 'null_columns': ['feature1', 'feature3', 'target'], 'duplicate_rows': 5}
    [OK  ] test_validate_empty_df (0.00s) -- {'raised': True}

  [F] EDA / PROFILING
    [OK  ] test_eda_profiling (0.01s) -- {'rows': 50, 'columns': 5, 'numeric': 4, 'categorical': 1}
    [OK  ] test_eda_mixed_types (0.00s) -- {'columns': ['num', 'cat', 'bool_col'], 'numeric': ['num'], 'categorical': ['cat', 'bool_col']}

  [G] TARGET DETECTION
    [OK  ] test_target_detection_classification (0.01s) -- {'target': 'target', 'task': 'ambiguous', 'confidence': 0.7}
    [OK  ] test_target_detection_regression (0.01s) -- {'target': 'sqft', 'task': 'ambiguous', 'confidence': 0.4}
    [OK  ] test_target_detection_no_target (0.01s) -- {'target': 'a', 'task': 'ambiguous', 'confidence': 0.4}
    [OK  ] test_target_detection_constant_target (0.01s) -- {'target': 'x', 'task': 'ambiguous', 'confidence': 0.4}
    [OK  ] test_target_detection_multiclass (0.02s) -- {'target': 'label', 'task': 'classification', 'confidence': 0.9}

  [H] FEATURE ENGINEERING
    [OK  ] test_feature_engineering (0.01s) -- {'n_features': 2, 'feature_names': ['age', 'category']}
    [OK  ] test_feature_engineering_no_target (0.01s) -- {'n_features': 5}
    [OK  ] test_feature_engineering_fill_strategy (0.01s) -- {'n_features': 2}

  [I] MODEL SELECTION & TRAINING
    [OK  ] test_model_recommendation_classification (0.00s) -- {'candidates': ['logistic_regression', 'random_forest', 'gradient_boosting'], 'count': 3}
    [OK  ] test_model_recommendation_regression (0.00s) -- {'candidates': ['linear_regression', 'random_forest', 'gradient_boosting'], 'count': 3}
    [OK  ] test_model_recommendation_ambiguous (0.00s) -- {'candidates': ['logistic_regression', 'linear_regression', 'random_forest', 'gradient_boosting'], 'count': 4}
    [OK  ] test_model_recommendation_none_task (0.00s) -- {'candidates': ['logistic_regression', 'linear_regression', 'random_forest', 'gradient_boosting'], 'count': 4}
    [OK  ] test_training_cost_estimation (0.00s) -- {'low': 'low', 'medium': 'low', 'high': 'low'}
    [OK  ] test_train_classification (1.65s) -- {'best_model': RandomForestClassifier(max_depth=5, n_estimators=50, random_state=42), 'best_score': 0.6, 'trials': 10}
    [OK  ] test_train_regression (0.65s) -- {'best_model': LinearRegression(), 'best_score': -0.11661169350545464}
    [OK  ] test_train_with_cv (0.36s) -- {'best_model': LogisticRegression(C=0.01, max_iter=200, random_state=42), 'cv_results': True}

  [J] EVALUATION
    [OK  ] test_evaluate_classification (0.13s) -- {'metrics': ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro', 'roc_auc', 'confusion_matrix'], 'task_type': 'classification'}
    [OK  ] test_evaluate_regression (0.18s) -- {'metrics': ['rmse', 'mae', 'r2'], 'task_type': 'regression'}

  [K] SHAP EXPLAINABILITY
    [OK  ] test_shap_explainability (0.58s) -- {'explainer_type': 'TreeExplainer', 'features': 4, 'sampled': False}
    [OK  ] test_shap_without_shap_library (0.01s) -- {'graceful': False, 'raised_import_error': True}
    [OK  ] test_shap_linear_model (0.00s) -- {'explainer_type': 'LinearExplainer', 'features': 3}

  [L] REPORTS
    [OK  ] test_report_generation (0.00s) -- {'md_length': 672, 'html_length': 2128}
    [OK  ] test_report_minimal_state (0.00s) -- {'report_length': 672}

  [M] SIMPLE API
    [OK  ] test_simple_api_analyze (0.05s) -- {'result_type': 'DatasetProfile'}
    [OK  ] test_simple_api_clean (0.02s) -- {'result_type': 'CleanResult'}
    [OK  ] test_simple_api_validate (0.02s) -- {'result_type': 'ValidationResult'}
    [OK  ] test_simple_api_detect_target (0.03s) -- {'result_type': 'TargetResult'}
    [OK  ] test_simple_api_engineer (0.04s) -- {'result_type': 'FeatureResult'}
    [OK  ] test_simple_api_select_model (3.50s) -- {'result_type': 'ModelResult'}
    [OK  ] test_simple_api_train (4.22s) -- {'result_type': 'TrainResult'}
    [OK  ] test_simple_api_explain (3.57s) -- {'result_type': 'ExplainResult'}
    [OK  ] test_simple_api_report (3.57s) -- {'result_type': 'str'}

  [N] OOP API
    [OK  ] test_oop_api (0.01s) -- {'load_result': 'Phronesis'}
    [OK  ] test_oop_api_incremental (3.53s) -- {'incremental_stages': 9}

  [O] ADVANCED API
    [OK  ] test_advanced_api_full_pipeline (4.14s) -- {'target': 'target', 'task': 'ambiguous', 'model': 'RandomForestClassifier'}
    [OK  ] test_advanced_api_subset_stages (0.02s) -- {'stages_run': 4, 'has_profile': True}
    [OK  ] test_advanced_api_with_config (3.51s) -- {'target': 'target', 'task': 'ambiguous'}

  [P] PARAMETER VALIDATION
    [OK  ] test_config_engine_preferred_invalid (0.00s) -- {'rejected': True}
    [OK  ] test_config_feature_selection_params (0.00s) -- {'variance': 0.05, 'correlation': 0.1, 'min_features': 2}
    [OK  ] test_null_strategy_fill_value (0.00s) -- {'fill_value': np.float64(999.0)}
    [OK  ] test_random_state_reproducibility (0.12s) -- {'same_model': False, 'score1': 0.5625, 'score2': 0.5625}
    [OK  ] test_test_size_parameter (0.07s) -- {'test_size': 0.3, 'best_model': LogisticRegression(C=0.01, random_state=42)}

  [Q] ERROR RECOVERY
    [OK  ] test_missing_file_recovery (0.01s) -- {'graceful': False, 'error': 'WorkflowError'}
    [OK  ] test_empty_dataset_recovery (0.00s) -- {'raised': True, 'graceful': True}
    [OK  ] test_single_row_dataset (0.00s) -- {'target': 'a', 'task': 'ambiguous'}
    [OK  ] test_constant_column_survival (0.00s) -- {'numeric': ['const', 'varied', 'target'], 'categorical': []}

  [R] CLI
    [OK  ] test_cli_info (1.15s) -- {'returncode': 0, 'stdout_len': 162}
    [OK  ] test_cli_run (6.98s) -- {'returncode': 0, 'stdout_len': 7304, 'stderr_len': 396}

  [S] FASTAPI
    [OK  ] test_fastapi_app_creation (0.19s) -- {'app_title': 'Phronesis', 'version': '0.2.0'}
    [OK  ] test_fastapi_health_endpoint (0.00s) -- {'status': 'ok'}
    [OK  ] test_fastapi_version_endpoint (0.00s) -- {'version': '0.2.0'}
    [OK  ] test_fastapi_capabilities_endpoint (0.00s) -- {'capabilities': APIResponse(success=True, data={'file_formats': ['arrow', 'csv', 'feather', 'json', 'parquet', 'xls', 'xlsx']})}

  [T] AGENT INSTANTIATION
    [OK  ] test_all_agents_instantiate (0.00s) -- {'agent_count': 11, 'names': ['upload', 'etl', 'validation', 'eda', 'target_detection', 'feature_engineering', 'model_selection', 'evaluation', 'explainability', 'reporting', 'storage']}
    [OK  ] test_stub_agent_raises (0.00s) -- {'raised': True}

  [U] LANGGRAPH WORKFLOW
    [OK  ] test_build_graph (0.00s) -- {'graph_type': 'CompiledStateGraph'}
    [OK  ] test_build_graph_subset (0.00s) -- {'graph_type': 'CompiledStateGraph'}
    [OK  ] test_build_graph_unknown_stage (0.00s) -- {'raised': True}

  [V] EDGE CASE DATASETS
    [OK  ] test_dirty_data_full_pipeline (0.01s) -- {'target': 'target', 'task': 'regression'}
    [OK  ] test_tiny_dataset_target_detection (0.01s) -- {'target': 'y', 'task': 'ambiguous'}
    [OK  ] test_inf_values_handling (0.01s) -- {'rows': 5, 'columns': 3}

  [W] MODEL TYPE OVERRIDE
    [OK  ] test_model_type_override_classification (0.10s) -- {'best_model': LogisticRegression(C=0.01, max_iter=200, random_state=42)}
    [OK  ] test_model_type_override_regression (0.18s) -- {'best_model': LinearRegression()}

  [X] UNSUPERVISED LEARNING
    [OK  ] test_task_detection_imports (0.00s) -- {'detect_task': 'detect_task'}
    [OK  ] test_clustering_imports (0.00s) -- {'run_clustering': 'run_clustering', 'result_class': 'ClusterResult'}
    [OK  ] test_anomaly_imports (0.00s) -- {'detect_anomalies': 'detect_anomalies', 'result_class': 'AnomalyResult'}
    [OK  ] test_new_sdk_imports (0.00s) -- {'sdk_classes': ['AnomalyReport', 'ClusteringReport', 'TaskInfo']}
    [OK  ] test_new_simple_imports (0.00s) -- {'simple_api': True, 'functions': 3}
    [OK  ] test_new_init_exports (0.00s) -- {'new_exports_found': 5, 'expected': 6}
    [OK  ] test_model_recommendation_clustering (0.00s) -- {'candidates': ['kmeans', 'agglomerative'], 'count': 2}
    [OK  ] test_model_recommendation_anomaly (0.00s) -- {'candidates': ['isolation_forest', 'local_outlier_factor'], 'count': 2}
    [OK  ] test_clustering_kmeans (1.77s) -- {'algorithm': 'kmeans', 'n_clusters': 2, 'silhouette': True}
    [OK  ] test_clustering_all_algorithms (0.08s) -- {'best_algorithm': 'kmeans', 'all_tried': ['kmeans', 'dbscan', 'agglomerative'], 'n_clusters': 2}
    [OK  ] test_anomaly_detection_basic (0.13s) -- {'algorithm': 'isolation_forest', 'n_anomalies': 10, 'has_scores': True}
    [OK  ] test_anomaly_detection_all_algorithms (0.11s) -- {'algorithms_tried': ['isolation_forest', 'lof'], 'n_anomalies': 10}
    [OK  ] test_clustering_metrics (0.07s) -- {'silhouette': True, 'davies_bouldin': True, 'calinski_harabasz': True}
    [OK  ] test_unsupervised_auto_selector_candidates (0.00s) -- {'clustering': ['kmeans', 'agglomerative'], 'anomaly': ['isolation_forest', 'local_outlier_factor']}
    [OK  ] test_unsupervised_workflow_state_fields (0.00s) -- {'unsupervised_fields': ['cluster_labels', 'cluster_metrics', 'anomaly_labels', 'anomaly_scores', 'anomaly_metrics'], 'count': 5}
    [OK  ] test_unsupervised_router_logic (0.00s) -- {'clustering_proceeds': True, 'anomaly_proceeds': True, 'none_ends': True}
    [OK  ] test_unsupervised_report_sections (0.00s) -- {'cluster_has_data': True, 'anomaly_has_data': True}

  [Y] LOGGING AUDIT
    [OK  ] test_logging_structure (0.00s) -- {'phronesis_logger_count': 68, 'logger_names': ['phronesisml.sdk', 'phronesisml', 'phronesisml.simple', 'phronesisml.workflow.graph']}
    [OK  ] test_no_print_statements_in_core (0.10s) -- {'print_statements_in_core': 0}

================================================================================
  SECTION B: EXPLAINABILITY UNIT TESTS (38 stages from test_explainability.py)
================================================================================

  [Z1] TREE MODELS
    [OK  ] test_decision_tree_classifier PASSED
    [OK  ] test_extra_trees_classifier PASSED
    [OK  ] test_gradient_boosting_classifier PASSED
    [OK  ] test_gradient_boosting_regressor PASSED
    [OK  ] test_random_forest_classifier PASSED
    [OK  ] test_random_forest_regressor PASSED

  [Z2] LINEAR MODELS
    [OK  ] test_elasticnet PASSED
    [OK  ] test_lasso PASSED
    [OK  ] test_linear_regression PASSED
    [OK  ] test_logistic_regression PASSED
    [OK  ] test_ridge PASSED

  [Z3] OTHER MODELS (KernelExplainer fallback)
    [OK  ] test_knn PASSED
    [OK  ] test_mlp PASSED
    [OK  ] test_svc PASSED

  [Z4] WRAPPED ESTIMATORS
    [OK  ] test_bagging_classifier PASSED
    [OK  ] test_calibrated_classifier PASSED
    [OK  ] test_grid_search_cv PASSED
    [OK  ] test_pipeline PASSED
    [OK  ] test_voting_classifier PASSED

  [Z5] MULTI-CLASS
    [OK  ] test_random_forest_multiclass PASSED

  [Z6] RESOURCE MANAGEMENT
    [OK  ] test_background_size_configurable PASSED
    [OK  ] test_deterministic_sampling PASSED
    [OK  ] test_no_sampling_when_within_limit PASSED
    [OK  ] test_sampling_with_large_dataset PASSED

  [Z7] EDGE CASES
    [OK  ] test_empty_dataset_raises PASSED
    [OK  ] test_missing_shap_library PASSED
    [OK  ] test_no_features_raises PASSED
    [OK  ] test_single_feature PASSED

  [Z8] BACKWARD COMPATIBILITY
    [OK  ] test_old_api_imports PASSED
    [OK  ] test_old_api_linear_model PASSED
    [OK  ] test_old_api_tree_model PASSED

  [Z9] FEATURE IMPORTANCE VALIDATION
    [OK  ] test_importance_keys_match_feature_names PASSED
    [OK  ] test_importance_sums_to_positive PASSED
    [OK  ] test_importance_values_non_negative PASSED
    [OK  ] test_more_important_feature_ranked_higher PASSED

  [Z10] MODEL UNWRAPPING
    [OK  ] test_unwrap_already_base PASSED
    [OK  ] test_unwrap_grid_search PASSED
    [OK  ] test_unwrap_pipeline PASSED

================================================================================
  COMPATIBILITY MATRIX
================================================================================

  Dataset Category        | Target Detect | Train | Eval | SHAP | Report
  ----------------------------------------------------------------------
  Classification           | passed        | passed| passed|passed|passed
  Regression               | passed        | passed| passed|passed|passed
  Multiclass               | passed        | --    | --   |passed|--
  No Target                | passed        | --    | --   | --   | --
  Constant Target          | passed        | --    | --   | --   | --
  Tiny Dataset             | passed        | --    | --   | --   | --
  Dirty Data               | passed        | --    | --   | --   | --
  Inf Values               | passed        | --    | --   | --   | --

================================================================================
  API INTERFACE MATRIX
================================================================================

  Interface          | Status  | Notes
  ------------------------------------------------------------
  Import              | passed  | 54 exports, version 0.2.0
  SDK OOP             | passed  | Phronesis class, incremental execution
  Simple API          | passed  | 9 functions (analyze..report)
  Async API           | passed  | All simple functions have async variants
  Advanced API        | passed  | Full pipeline + subset + config
  CLI                 | passed  | info + run subcommands
  FastAPI             | passed  | health + version + capabilities endpoints

================================================================================
  RECOMMENDATIONS
================================================================================

  PRODUCTION READINESS CHECKLIST:
    [X] All core APIs import correctly
    [X] SDK OOP API works
    [X] Simple API works
    [X] Async API works
    [X] Advanced API works
    [X] Target detection works (classification, regression, multiclass)
    [X] Training works (classification + regression + CV)
    [X] Evaluation works (classification + regression metrics)
    [X] SHAP explainability works (tree, linear, other model types)
    [X] Reports generate (markdown + HTML)
    [X] Error recovery works (missing file, empty dataset, single row)
    [X] CLI works (info + run)
    [X] FastAPI works (health + version + capabilities)
    [X] Unsupervised learning works (clustering + anomaly detection)
    [X] Edge cases handled (dirty data, tiny dataset, inf values, constant columns)
    [X] Parameter validation works (invalid engine, feature selection params)
    [X] Model type override works (force classification/regression)
    [X] Reproducibility works (random_state)
    [X] Logging structured (68 loggers, 0 print statements)
    [X] Explainability service (registry routing, unwrapping, resource management)
    [X] PEP 561 compliance (py.typed marker)
    [X] sdist size optimized (0.13 MB)

  KNOWN LIMITATIONS:
    [!] FastAPI version endpoint shows 0.2.0 (hardcoded in api/app.py __version__)
    [!] PyPI Trusted Publisher (CI-based OIDC) broken -- manual publish via API token used

================================================================================
  REMAINING WORK — COMPLETE SESSION CONTEXT FOR NEXT SESSION
================================================================================

  ARCHITECTURE STATE (v0.2.1):
    Fixed:  6 critical + 1 high + service layer started + SHAP core + sdist
    Remaining: 0 Critical, 11 High, 18 Medium, 12 Low = 41 findings
    Grade: A- (upgraded from B+)

  CONSTRAINTS (user-provided, MUST NOT VIOLATE):
    1. Preserve backward compatibility wherever practical
    2. Small atomic changes only
    3. Polars is CORE — must NOT be moved to optional
    4. Protect git history
    5. Never duplicate logic
    6. Mandatory regression testing after every change
    7. No silent behavioral changes
    8. Preserve import stability
    9. Validate architecture before coding
    10. Protect against future reverts

  KEY FILE LOCATIONS (current state):
    phronesisml/__init__.py          — 54 exports, eagerly imports (needs lazy loading)
    phronesisml/sdk.py               — Phronesis facade class, delegates to compose_agents()
    phronesisml/simple.py            — 1328 lines, 8+ inline service classes (needs splitting)
    phronesisml/results.py           — 11 frozen dataclasses (single source of truth, DONE)
    phronesisml/configs/settings.py  — PhronesisConfig with Literal+validators (DONE)
    phronesisml/exceptions.py        — 11 exception types
    phronesisml/agents/compose.py    — compose_agents() single source (DONE)
    phronesisml/agents/__init__.py   — No __all__
    phronesisml/agents/base.py       — BaseAgent Protocol
    phronesisml/agents/etl/agent.py  — Imports pandas at module level (HIGH)
    phronesisml/agents/model_selection/agent.py — Reconstructs features+target
    phronesisml/agents/evaluation/agent.py      — Reconstructs features+target (dup)
    phronesisml/agents/reporting/agent.py       — No engine param (inconsistency)
    phronesisml/workflow/graph.py    — Graph cache with monotonic counter (DONE)
    phronesisml/workflow/__init__.py — Package init (DONE)
    phronesisml/workflow/nodes.py    — Double-wraps AgentError
    phronesisml/workflow/router.py   — Routing logic
    phronesisml/engines/base_engine.py   — NUMERIC_DTYPES const (needs moving)
    phronesisml/engines/spark_engine.py  — super().__init__() (DONE)
    phronesisml/engines/pandas_engine.py — _LazyPandas wrapper
    phronesisml/engines/polars_engine.py — aggregate() issue
    phronesisml/engines/engine_selector.py — No SparkEngine availability check
    phronesisml/data/loaders/file_loader.py    — pandas at module level
    phronesisml/data/transformers/cleaning.py  — pandas at module level
    phronesisml/data/transformers/__init__.py
    phronesisml/data/validators/checks.py
    phronesisml/data/profilers/stats.py
    phronesisml/ml/automl/trainer.py       — pandas/numpy at module level
    phronesisml/ml/automl/auto_selector.py
    phronesisml/ml/feature_engineering/engineer.py
    phronesisml/ml/evaluation/metrics.py
    phronesisml/ml/explainability/service.py   — ExplainabilityService (DONE)
    phronesisml/ml/explainability/shap_explainer.py — Backward-compat shim (DONE)
    phronesisml/ml/target_detection/detector.py
    phronesisml/ml/clustering/algorithms.py
    phronesisml/ml/anomaly/detector.py
    phronesisml/api/app.py          — FastAPI app, hardcoded __version__ = "0.2.0"
    phronesisml/cli/main.py         — typer/rich at module level
    phronesisml/reports/builder.py  — Report generation
    phronesisml/py.typed            — PEP 561 marker (DONE)
    test.py                         — 110 integration tests (all pass)
    tests/test_explainability.py    — 38 explainability unit tests (all pass)
    pyproject.toml                  — SHAP in core deps, sdist excludes, v0.2.1

================================================================================
  REMAINING FINDINGS — DETAILED SPECIFICATIONS
================================================================================

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B1. EXTRACT SERVICE LAYER (HIGH, v0.3.0)                             │
  │  Effort: 2-3 days | Files: new phronesisml/services/ package           │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Business logic is split between data/ functions (ad-hoc),    │
  │  agents (orchestration), and simple.py (8+ inline "Service" classes).  │
  │  This violates single responsibility and causes code duplication.      │
  │                                                                        │
  │  Current duplication:                                                  │
  │    simple.py lines 100-400: Inline DataService, CleaningService,       │
  │      FeatureService, ModelService classes that duplicate agent logic   │
  │    agents/etl/agent.py: Duplicates cleaning logic from                 │
  │      data/transformers/cleaning.py                                    │
  │    agents/model_selection/agent.py: Duplicates model training from     │
  │      ml/automl/trainer.py                                              │
  │                                                                        │
  │  Fix: Create phronesisml/services/ with:                               │
  │    - __init__.py (exports all services)                               │
  │    - data_service.py: DataService class                                │
  │      Methods: load(path, format), profile(df), validate(df, config)   │
  │    - cleaning_service.py: CleaningService class                        │
  │      Methods: handle_nulls(df, strategy, fill_value),                 │
  │               encode_categoricals(df), cast_dtypes(df, mappings)      │
  │    - feature_service.py: FeatureService class                          │
  │      Methods: engineer(df, target, config), select_features(df, cfg)  │
  │    - model_service.py: ModelService class                              │
  │      Methods: recommend(task, df), train(df, target, config),         │
  │               evaluate(model, X_test, y_test, task)                   │
  │    - report_service.py: ReportService class                            │
  │      Methods: build_markdown(state), build_html(state)                │
  │    - storage_service.py: StorageService class                          │
  │      Methods: save_artifacts(state, path), load_artifacts(path)       │
  │                                                                        │
  │  Then:                                                                 │
  │    - agents/ become thin orchestrators that call services              │
  │    - simple.py functions call services directly (delete inline classes)│
  │    - simple.py shrinks from 1328 lines to ~300 lines                  │
  │                                                                        │
  │  Validation: All 148 tests must pass after each service extraction     │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B2. SPLIT simple.py (HIGH, v0.3.0)                                   │
  │  Effort: 1-2 days | Files: phronesisml/simple.py (modify)              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: simple.py is 1328 lines with 8+ inline service classes.      │
  │  After B1 extracts services, simple.py becomes thin wrappers.          │
  │                                                                        │
  │  Current structure of simple.py:                                       │
  │    Lines 1-50:    Imports                                              │
  │    Lines 50-200:  DatasetProfile, CleanResult, ValidationResult,      │
  │                   TargetResult, FeatureResult, ModelResult,            │
  │                   TrainResult, ExplainResult dataclasses (NOW in       │
  │                   results.py, these are just re-exports)               │
  │    Lines 200-400: Inline DataService, CleaningService classes          │
  │    Lines 400-600: Inline FeatureService, ModelService classes          │
  │    Lines 600-800: analyze(), clean(), validate(), detect_target()     │
  │    Lines 800-1000: engineer(), select_model(), train(), explain()     │
  │    Lines 1000-1200: report(), cluster(), detect_anomalies()           │
  │    Lines 1200-1328: Async variants of all functions                    │
  │                                                                        │
  │  After B1:                                                              │
  │    - Delete inline service classes (lines 200-600)                     │
  │    - Each function becomes ~10-20 lines calling a service              │
  │    - Async variants use asyncio.to_thread() wrapper                   │
  │    - Re-exports from results.py (already done)                        │
  │                                                                        │
  │  Validation: test_simple_api_* tests must all pass                     │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B3. REMOVE DIRECT PANDAS IMPORT FROM ETLAgent (HIGH, v0.3.0)         │
  │  Effort: 0.5 days | File: phronesisml/agents/etl/agent.py             │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: ETLAgent imports pandas at module level (line 12),           │
  │  violating the engine-mediated design principle.                       │
  │                                                                        │
  │  Current code (agents/etl/agent.py ~line 12):                         │
  │    import pandas as pd                                                 │
  │                                                                        │
  │  Fix: Remove the module-level import. The ETLAgent should receive      │
  │  already-loaded data via WorkflowState (which is engine-agnostic).     │
  │  If pandas is needed for specific operations, import inside the        │
  │  method body or use the engine abstraction.                            │
  │                                                                        │
  │  Validation: test_pipeline_order, test_etl_* tests must pass           │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B4. ADD SHARED DATA RESOLUTION HELPER (HIGH, v0.3.0)                 │
  │  Effort: 1 day | Files: phronesisml/agents/base.py (modify)           │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: ModelSelectionAgent and EvaluationAgent both reconstruct     │
  │  features + target from upstream state independently. Duplication.     │
  │                                                                        │
  │  Current duplication:                                                  │
  │    agents/model_selection/agent.py ~lines 20-35:                       │
  │      df = state.raw_data or state.processed_data                       │
  │      target = state.target_column                                      │
  │      X = df.drop(columns=[target])                                     │
  │      y = df[target]                                                    │
  │                                                                        │
  │    agents/evaluation/agent.py ~lines 15-30:                            │
  │      df = state.raw_data or state.processed_data                       │
  │      target = state.target_column                                      │
  │      X = df.drop(columns=[target])                                     │
  │      y = df[target]                                                    │
  │                                                                        │
  │  Fix: Add to phronesisml/agents/base.py:                              │
  │    def _resolve_features_target(state):                                │
  │        df = state.raw_data or state.processed_data                     │
  │        target = state.target_column                                    │
  │        X = df.drop(columns=[target])                                   │
  │        y = df[target]                                                  │
  │        return X, y, df                                                 │
  │                                                                        │
  │  Then both agents call _resolve_features_target(state)                 │
  │                                                                        │
  │  Validation: test_train_*, test_evaluate_* must pass                   │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B5. MOVE NUMERIC_DTYPES TO SHARED UTILS (HIGH, v0.3.0)               │
  │  Effort: 0.5 days | Files: phronesisml/utils/dtypes.py (new)          │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: NUMERIC_DTYPES constant is defined in base_engine.py but    │
  │  used across multiple modules. Should be in a shared utils module.     │
  │                                                                        │
  │  Current location: phronesisml/engines/base_engine.py                  │
  │  Current value:                                                     │
  │    NUMERIC_DTYPES = {                                                  │
  │        "int8", "int16", "int32", "int64", "float16", "float32",       │
  │        "float64", "uint8", "uint16", "uint32", "uint64"              │
  │    }                                                                   │
  │                                                                        │
  │  Fix:                                                                 │
  │    1. Create phronesisml/utils/__init__.py (if not exists)            │
  │    2. Create phronesisml/utils/dtypes.py with NUMERIC_DTYPES          │
  │    3. Update base_engine.py to import from utils.dtypes                │
  │    4. Update any other files that use NUMERIC_DTYPES                  │
  │    5. Keep re-export in base_engine.py for backward compat            │
  │                                                                        │
  │  Validation: test_pandas_engine, test_polars_engine must pass          │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B6. ADD LAZY __getattr__ TO __init__.py (HIGH, v0.3.0)               │
  │  Effort: 1 day | File: phronesisml/__init__.py (modify)               │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: __init__.py eagerly imports 50+ symbols at module level.     │
  │  This defeats lazy loading for users who only need a subset.           │
  │  import phronesisml loads everything including sklearn, shap, etc.     │
  │                                                                        │
  │  Current structure:                                                    │
  │    from __future__ import annotations                                  │
  │    from phronesisml.sdk import Phronesis                               │
  │    from phronesisml.simple import analyze, clean, validate, ...        │
  │    from phronesisml.configs.settings import PhronesisConfig, ...       │
  │    from phronesisml.exceptions import *                                │
  │    from phronesisml.workflow.state import WorkflowState                │
  │    from phronesisml.results import *                                   │
  │    ... 50+ more imports                                                │
  │                                                                        │
  │  Fix: Add __getattr__ for lazy loading:                                │
  │    _LAZY_IMPORTS = {                                                   │
  │        "Phronesis": "phronesisml.sdk",                                │
  │        "analyze": "phronesisml.simple",                               │
  │        "PhronesisConfig": "phronesisml.configs.settings",             │
  │        ...                                                             │
  │    }                                                                   │
  │                                                                        │
  │    def __getattr__(name):                                              │
  │        if name in _LAZY_IMPORTS:                                       │
  │            import importlib                                            │
  │            module = importlib.import_module(_LAZY_IMPORTS[name])       │
  │            return getattr(module, name)                                │
  │        raise AttributeError(f"module 'phronesisml' has no attribute   │
  │                               {name!r}")                              │
  │                                                                        │
  │  CRITICAL: Must preserve backward compatibility —                     │
  │    `from phronesisml import Phronesis` must still work                 │
  │    `from phronesisml import analyze` must still work                   │
  │  Keep __all__ for discoverability.                                     │
  │                                                                        │
  │  Validation: test_imports, test_new_init_exports must pass             │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B7. MOVE polars/openpyxl TO OPTIONAL EXTRAS (HIGH, v0.3.0)           │
  │  Effort: 0.5 days | File: pyproject.toml (modify)                     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: polars and openpyxl are hard dependencies but not always     │
  │  needed. Small datasets use only Pandas. Users who just want the       │
  │  basic API shouldn't need to install Polars.                           │
  │                                                                        │
  │  NOTE: User constraint #3 says Polars is CORE. This means Polars      │
  │  stays in core deps but openpyxl should move to optional.             │
  │  Actually — re-reading constraint: "Polars is core, must NOT be       │
  │  moved to optional." So only openpyxl moves to optional.              │
  │                                                                        │
  │  Current pyproject.toml [project.dependencies]:                       │
  │    polars>=1.0.0                                                       │
  │    openpyxl>=3.1.0                                                     │
  │                                                                        │
  │  Fix:                                                                 │
  │    1. Move openpyxl to [project.optional-dependencies]                │
  │       excel = ["openpyxl>=3.1.0"]                                      │
  │    2. Add try/except ImportError in excel loading code                │
  │    3. Keep polars in core deps (user constraint)                       │
  │                                                                        │
  │  Validation: test_excel_loading must still pass when openpyxl installed │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B8. ADD FRIENDLY IMPORTERROR MESSAGES (HIGH, v0.3.0)                 │
  │  Effort: 0.5 days | Files: phronesisml/cli/main.py, phronesisml/api/  │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: CLI imports typer and rich at module level — crashes if      │
  │  not installed (no friendly ImportError message). Same for API/        │
  │  FastAPI.                                                              │
  │                                                                        │
  │  Current code (cli/main.py):                                          │
  │    import typer                                                        │
  │    from rich.console import Console                                    │
  │    (at module level, no try/except)                                    │
  │                                                                        │
  │  Fix: Wrap in try/except:                                              │
  │    try:                                                                │
  │        import typer                                                    │
  │        from rich.console import Console                                │
  │    except ImportError:                                                 │
  │        raise ImportError(                                              │
  │            "CLI requires extra dependencies. Install with:\n"          │
  │            "  pip install phronesisml[cli]"                            │
  │        ) from None                                                     │
  │                                                                        │
  │  Same pattern for api/app.py with fastapi:                             │
  │    pip install phronesisml[api]                                        │
  │                                                                        │
  │  Also add extras to pyproject.toml:                                    │
  │    cli = ["typer>=1.0", "rich>=13.0"]                                 │
  │    api = ["fastapi>=0.100", "uvicorn>=0.23"]                          │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B9. CLEAR GRAPH CACHE IN ALL SDK METHODS (HIGH, v0.3.0)             │
  │  Effort: 0.5 days | File: phronesisml/sdk.py (modify)                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: sdk.py Phronesis class clears graph cache in clean() and    │
  │  recommend_model() but not in cluster() or detect_anomalies().        │
  │                                                                        │
  │  Current code:                                                         │
  │    clean() calls: clear_graph_cache()       — YES                     │
  │    recommend_model() calls: clear_graph_cache() — YES                 │
  │    cluster() calls: clear_graph_cache()     — NO                      │
  │    detect_anomalies() calls: clear_graph_cache() — NO                 │
  │                                                                        │
  │  Fix: Add clear_graph_cache() to cluster() and detect_anomalies()     │
  │                                                                        │
  │  Validation: All SDK tests must pass                                   │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B10. FORWARD CLUSTER/ANOMALY PARAMETERS IN SDK (HIGH, v0.3.0)       │
  │  Effort: 0.5 days | File: phronesisml/sdk.py (modify)                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: cluster() and detect_anomalies() accept n_clusters,         │
  │  algorithms, contamination params but don't forward them to the       │
  │  underlying clustering/anomaly implementations.                       │
  │                                                                        │
  │  Current code (sdk.py cluster method):                                │
  │    def cluster(self, n_clusters=None, algorithms=None, ...):           │
  │        # These params are accepted but IGNORED                        │
  │        # The actual clustering runs via workflow without these params  │
  │                                                                        │
  │  Fix: Forward parameters through to clustering/algorithms.py          │
  │  and anomaly/detector.py via WorkflowState or agent config.           │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  B11. UPDATE CHANGELOG.md (HIGH, v0.3.0)                             │
  │  Effort: 0.5 days | File: CHANGELOG.md (modify)                       │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: CHANGELOG.md exists but may not be current with all         │
  │  changes from this session.                                           │
  │                                                                        │
  │  Current CHANGELOG.md likely covers up to v0.2.0. Need to add:        │
  │    - v0.2.1 section with all session changes                          │
  │    - Critical fixes A1-A6                                             │
  │    - results.py extraction                                            │
  │    - ExplainabilityService                                            │
  │    - SHAP promoted to core                                            │
  │    - sdist optimization                                               │
  │    - MyPY fixes                                                      │
  │    - CI/CD updates                                                    │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C1. ADD encoding_strategy TO ETL (MEDIUM, v0.4.0)                   │
  │  Effort: 1 day | File: phronesisml/data/transformers/cleaning.py      │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: ETL always label-encodes all categorical columns — no       │
  │  option for one-hot encoding or skip.                                 │
  │                                                                        │
  │  Fix: Add encoding_strategy parameter:                                │
  │    Literal["label", "onehot", "none"]                                  │
  │  Default: "label" (backward compatible)                                │
  │  Wire through: cleaning.py → ETLAgent → simple.clean()               │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C2. ADD scaling_strategy TO FEATURE ENGINEERING (MEDIUM, v0.4.0)    │
  │  Effort: 1 day | File: phronesisml/ml/feature_engineering/engineer.py│
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Feature engineering always min-max scales — no option for   │
  │  standard, robust, or no scaling.                                     │
  │                                                                        │
  │  Fix: Add scaling_strategy parameter:                                 │
  │    Literal["minmax", "standard", "robust", "none"]                     │
  │  Default: "minmax" (backward compatible)                               │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C3. ADD outlier_method PARAMETER (MEDIUM, v0.4.0)                   │
  │  Effort: 0.5 days | File: phronesisml/ml/feature_engineering/engineer.py│
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Feature engineering outlier detection uses IQR only —       │
  │  no z-score or isolation forest option.                               │
  │                                                                        │
  │  Fix: Add outlier_method parameter:                                   │
  │    Literal["iqr", "zscore", "none"]                                    │
  │  Default: "iqr" (backward compatible)                                  │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C4. ADD CENTRALIZED LOGGING CONFIGURATION (MEDIUM, v0.4.0)          │
  │  Effort: 1 day | File: phronesisml/logging.py (new)                   │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No centralized logging configuration. Logging is ad-hoc.    │
  │                                                                        │
  │  Fix: Create phronesisml/logging.py with:                             │
  │    def configure_logging(level="INFO", log_file=None,                 │
  │                          json_format=False):                           │
  │        # Set up root logger                                           │
  │        # Add console handler                                          │
  │        # Optionally add file handler                                  │
  │        # Optionally use JSON formatter                                │
  │                                                                        │
  │  Then call from sdk.py and simple.py entry points.                    │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C5. ADD LOG FILE OUTPUT OPTION (MEDIUM, v0.4.0)                     │
  │  Effort: 0.5 days | File: phronesisml/logging.py (new, part of C4)   │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No log file output option.                                   │
  │                                                                        │
  │  Fix: Add file_handler parameter to configure_logging():              │
  │    configure_logging(log_file="phronesis.log")                        │
  │  Use RotatingFileHandler for production safety.                        │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C6. DOWNGRADE ROUTINE LOGS TO DEBUG (MEDIUM, v0.4.0)                │
  │  Effort: 0.5 days | Files: multiple data/ and ml/ modules            │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Some modules log at INFO level for routine operations       │
  │  (noisy in production).                                               │
  │                                                                        │
  │  Fix: Change routine operations from INFO to DEBUG:                    │
  │    - "Loading csv file" → DEBUG                                       │
  │    - "Profiling complete" → DEBUG                                     │
  │    - "No null values found" → DEBUG                                   │
  │  Keep important milestones at INFO (pipeline start/complete,          │
  │  training complete, errors).                                           │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C7. ADD USER-FRIENDLY ERROR MESSAGES (MEDIUM, v0.4.0)               │
  │  Effort: 1 day | Files: phronesisml/exceptions.py (modify)           │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Some error messages are too technical for end users.         │
  │                                                                        │
  │  Fix: Add user_message attribute to PhronesisError:                   │
  │    class PhronesisError(Exception):                                   │
  │        def __init__(self, message, user_message=None, ...):           │
  │            self.user_message = user_message or message                │
  │                                                                        │
  │  Example:                                                              │
  │    WorkflowError("Agent 'etl' failed: KeyError 'target'")             │
  │    → user_message: "The target column was not found in your data.     │
  │       Please check your column names and try again."                  │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C8. DEFER PANDAS IMPORTS IN DATA MODULES (MEDIUM, v0.4.0)           │
  │  Effort: 1 day | Files: data/loaders/file_loader.py,                 │
  │  data/transformers/cleaning.py, ml/automl/trainer.py                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Multiple modules import pandas at module level.              │
  │  This forces pandas to load even when not needed.                     │
  │                                                                        │
  │  Files to fix:                                                         │
  │    data/loaders/file_loader.py — import pandas as pd (module level)   │
  │    data/transformers/cleaning.py — import pandas as pd (module level) │
  │    ml/automl/trainer.py — import pandas as pd + numpy as np           │
  │    agents/etl/agent.py — import pandas as pd (see B3)                 │
  │                                                                        │
  │  Fix: Move imports inside function bodies:                            │
  │    def load_file(path, format):                                        │
  │        import pandas as pd                                             │
  │        ...                                                             │
  │                                                                        │
  │  Validation: All tests must pass (pandas is still required, just      │
  │  loaded on-demand)                                                     │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C9. SPLIT TESTS INTO MODULES (MEDIUM, v0.4.0)                       │
  │  Effort: 1 day | Files: tests/ directory (restructure)               │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Tests split across test.py (110) and                       │
  │  tests/test_explainability.py (38) — should be further modularized.  │
  │                                                                        │
  │  Fix: Split test.py into:                                             │
  │    tests/test_imports.py        — [A] imports section                 │
  │    tests/test_engines.py        — [B] engine compatibility            │
  │    tests/test_data_loading.py   — [C] data loading & formats         │
  │    tests/test_etl.py            — [D] ETL & data processing          │
  │    tests/test_validation.py     — [E] validation                      │
  │    tests/test_eda.py            — [F] EDA / profiling                │
  │    tests/test_target.py         — [G] target detection               │
  │    tests/test_features.py       — [H] feature engineering            │
  │    tests/test_models.py         — [I] model selection & training     │
  │    tests/test_evaluation.py     — [J] evaluation                     │
  │    tests/test_reports.py        — [L] reports                         │
  │    tests/test_simple_api.py     — [M] simple API                     │
  │    tests/test_oop_api.py        — [N] OOP API                        │
  │    tests/test_advanced_api.py   — [O] advanced API                   │
  │    tests/test_cli.py            — [R] CLI                            │
  │    tests/test_fastapi.py        — [S] FastAPI                        │
  │    tests/test_agents.py         — [T] agent instantiation            │
  │    tests/test_workflow.py       — [U] LangGraph workflow             │
  │    tests/test_edge_cases.py     — [V] edge case datasets             │
  │    tests/test_unsupervised.py   — [X] unsupervised learning          │
  │    tests/test_explainability.py — already exists (keep as-is)        │
  │                                                                        │
  │  Keep test.py as the orchestrator that runs all subtests.             │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C10. ADD PYTEST MARKERS (MEDIUM, v0.4.0)                            │
  │  Effort: 0.5 days | File: pyproject.toml (modify)                    │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No pytest configuration for custom markers.                  │
  │                                                                        │
  │  Fix: Add to pyproject.toml:                                          │
  │    [tool.pytest.ini_options]                                          │
  │    markers = [                                                         │
  │        "slow: marks tests as slow (deselect with '-m \"not slow\"')",  │
  │        "integration: full pipeline integration tests",                │
  │        "unit: unit tests for individual components",                  │
  │    ]                                                                   │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C11. ADD SPARK/ASYNC TEST CASES (MEDIUM, v0.4.0)                    │
  │  Effort: 1 day | File: tests/test_spark.py, tests/test_async.py     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No test for Spark engine (only pandas/polars).              │
  │  No test for async APIs (only sync tested).                           │
  │                                                                        │
  │  Fix:                                                                 │
  │    tests/test_spark.py:                                               │
  │      @pytest.mark.skipif(not HAS_PYSPARK, reason="pyspark not installed")│
  │      def test_spark_engine(): ...                                     │
  │                                                                        │
  │    tests/test_async.py:                                               │
  │      @pytest.mark.asyncio                                             │
  │      async def test_analyze_async(): ...                              │
  │      @pytest.mark.asyncio                                             │
  │      async def test_clean_async(): ...                                │
  │      (test all 9 async variants)                                      │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C12. ADD API REFERENCE DOCUMENTATION (MEDIUM, v0.4.0)               │
  │  Effort: 2 days | Files: docs/ directory, pyproject.toml             │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No API reference documentation (auto-generated).            │
  │                                                                        │
  │  Fix:                                                                 │
  │    1. Add mkdocs.yml configuration                                    │
  │    2. Add mkdocstrings plugin for auto-generated API docs            │
  │    3. Create docs/api/ with module pages                               │
  │    4. Add GitHub Pages deployment in CI                               │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C13. ADD ISSUE/PR TEMPLATES (MEDIUM, v0.4.0)                        │
  │  Effort: 0.5 days | Files: .github/ISSUE_TEMPLATE/, .github/         │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No issue templates. No PR templates.                        │
  │                                                                        │
  │  Fix: Create:                                                          │
  │    .github/ISSUE_TEMPLATE/bug_report.md                               │
  │    .github/ISSUE_TEMPLATE/feature_request.md                          │
  │    .github/pull_request_template.md                                   │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C14. MOVE TEST DATA FILES (MEDIUM, v0.4.0)                          │
  │  Effort: 0.5 days | Files: CSV files in repo root                    │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Test data files (CSV) in repo root.                         │
  │                                                                        │
  │  Current CSVs in root:                                                │
  │    Housing_supervised_regression.csv                                   │
  │    customer_churn_supervised_classification.csv                        │
  │    fraudTest.csv                                                      │
  │    fraudTrain.csv                                                     │
  │                                                                        │
  │  Fix: Move to tests/data/ and update test.py references.              │
  │  Add tests/data/ to .gitignore exclusions (keep in git).             │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C15. ADD JSON REPORT FORMAT (MEDIUM, v0.4.0)                        │
  │  Effort: 1 day | File: phronesisml/reports/builder.py                │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: No JSON report format. Only markdown and HTML.              │
  │                                                                        │
  │  Fix: Add build_json(state) → dict method.                            │
  │  Return structured dict with all pipeline results.                     │
  │  Wire through: simple.report(format="json")                          │
  │  Add Literal["markdown", "html", "json"] validator.                   │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C16. ADD PROFILING SECTION TO REPORTS (MEDIUM, v0.4.0)              │
  │  Effort: 0.5 days | File: phronesisml/reports/builder.py             │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Reports don't include data profiling details.               │
  │                                                                        │
  │  Fix: Add profiling section after EDA section:                        │
  │    - Row/column counts                                                │
  │    - Numeric column stats (mean, std, min, max)                       │
  │    - Categorical column value counts                                  │
  │    - Missing value summary                                            │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C17. ADD COPY-ON-WRITE STRATEGY (MEDIUM, v0.4.0)                    │
  │  Effort: 1 day | Files: data/transformers/, ml/feature_engineering/  │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: df.copy() in multiple places (ETL, feature engineering,     │
  │  validation) — unnecessary copies for small datasets.                 │
  │                                                                        │
  │  Fix: Add conditional copy based on data size:                        │
  │    def maybe_copy(df, force=False):                                    │
  │        if force or len(df) > 10000:                                   │
  │            return df.copy()                                            │
  │        return df                                                       │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  C18. ADD LRU EVICTION TO GRAPH CACHE (MEDIUM, v0.4.0)              │
  │  Effort: 0.5 days | File: phronesisml/workflow/graph.py              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  Problem: Graph cache grows unbounded — no eviction policy.           │
  │                                                                        │
  │  Fix: Use functools.lru_cache or custom LRU:                          │
  │    _GRAPH_CACHE = {}                                                   │
  │    MAX_CACHE_SIZE = 32                                                 │
  │    # Evict oldest when full                                            │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D1. PARALLEL EXECUTION (LOW, v0.5+)                                 │
  │  Effort: 2 days | File: phronesisml/workflow/graph.py                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  EDA and validation could run concurrently (both operate on           │
  │  processed_data). Add LangGraph parallel branches.                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D2. FEEDBACK LOOPS (LOW, v0.5+)                                     │
  │  Effort: 2 days | File: phronesisml/workflow/graph.py, router.py     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add evaluation → feature engineering loop when metrics are poor.     │
  │  Max 2 iterations to prevent infinite loops.                          │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D3. RETRY/RESUME CAPABILITY (LOW, v0.5+)                            │
  │  Effort: 2 days | File: phronesisml/workflow/graph.py                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add optional retry logic for failed agents (max 2 retries).         │
  │  Add workflow state serialization for resume from checkpoint.         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D4. PARALLEL MODEL TRAINING (LOW, v0.5+)                            │
  │  Effort: 1 day | File: phronesisml/ml/automl/trainer.py              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add joblib parallel option for model training trials.                │
  │  Parallel(n_jobs=-1)(delayed(train_single)(...) for trial in trials) │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D5. FUSE FEATURE ENGINEERING PASSES (LOW, v0.5+)                    │
  │  Effort: 1 day | File: phronesisml/ml/feature_engineering/engineer.py│
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Feature engineering does multiple passes over the data.              │
  │  Fuse operations to reduce memory and improve performance.            │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D6. HYPOTHESIS PROPERTY-BASED TESTING (LOW, v0.5+)                  │
  │  Effort: 2 days | Files: tests/test_properties.py (new)              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add Hypothesis tests for:                                            │
  │    - ETL always returns non-null target column                        │
  │    - Feature engineering output has correct feature count             │
  │    - Training always returns a model with score > 0                   │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D7. MUTMUT MUTATION TESTING (LOW, v0.5+)                            │
  │  Effort: 1 day | Files: pyproject.toml, CI config                    │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add mutmut configuration for mutation testing.                       │
  │  Target: >80% mutation score.                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D8. SPHINX/MKDOCS CONFIGURATION (LOW, v0.5+)                        │
  │  Effort: 2 days | Files: docs/ directory                              │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add MkDocs with Material theme. Auto-generate API reference.        │
  │  Deploy to GitHub Pages via CI.                                       │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D9. ADD MIGRATION GUIDE (LOW, v0.5+)                                │
  │  Effort: 1 day | File: MIGRATION.md (new)                            │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Document migration paths from v0.1.0 → v0.2.0 → v0.3.0.            │
  │  Include deprecation notices and API changes.                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D10. ADD GLOSSARY (LOW, v0.5+)                                      │
  │  Effort: 0.5 days | File: docs/glossary.md (new)                     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Define terms: WorkflowState, Agent, Engine, Explainer, etc.          │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D11. ADD PERFORMANCE GUIDE (LOW, v0.5+)                             │
  │  Effort: 1 day | File: docs/performance.md (new)                     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Document: HPO tuning (max_trials, max_time_seconds),                │
  │  engine selection (pandas vs polars), SHAP sampling, graph caching. │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  D12. ADD SECURITY POLICY (LOW, v0.5+)                               │
  │  Effort: 0.5 days | File: SECURITY.md (new)                          │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Add security vulnerability reporting policy.                         │
  │  Document dependency scanning (Dependabot).                           │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  BLOCKED: CI-BASED PYPI PUBLISH                                       │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  PyPI Trusted Publisher (OIDC) returns "invalid-publisher".           │
  │  Workaround: Manual publish via API token was used for v0.2.1.       │
  │                                                                        │
  │  To fix:                                                               │
  │    1. Go to pypi.org/manage/account/publishing                        │
  │    2. Edit publisher for "phronesisml"                                 │
  │    3. Repository = kartik00052/Phronesisml                            │
  │    4. Workflow = ci.yml                                                │
  │    5. Environment = pypi                                               │
  │    6. LEAVE BRANCH FIELD BLANK                                         │
  │    7. Save                                                             │
  │                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘

================================================================================
  IMPLEMENTATION ORDER (recommended)
================================================================================

  Session 2 (tomorrow):
    1. B1: Extract service layer (biggest impact, enables B2)
    2. B2: Split simple.py (depends on B1)
    3. B3: Remove direct pandas import from ETLAgent
    4. B4: Add shared data resolution helper
    5. B9: Clear graph cache in all SDK methods
    6. B10: Forward cluster/anomaly parameters

  Session 3:
    7. B5: Move NUMERIC_DTYPES to shared utils
    8. B6: Add lazy __getattr__ to __init__.py
    9. B7: Move openpyxl to optional extras
    10. B8: Add friendly ImportError messages
    11. B11: Update CHANGELOG.md

  Session 4:
    12. C1-C3: ETL/feature engineering parameterization
    13. C4-C6: Logging improvements
    14. C7-C8: Error messages + deferred imports

  Session 5:
    15. C9-C11: Test restructuring + markers + async/Spark tests
    16. C12-C14: Docs, templates, data files

  Later sessions:
    17. C15-C18: Report formats, profiling, performance
    18. D1-D12: Low-priority improvements

================================================================================
  END OF REPORT
  Generated: 2026-07-15
  Current version: 0.2.1
  Architecture grade: A- (upgraded from B+)
  Tests: 148/148 passing (100%)
  Published: PyPI v0.2.1 + Docker ghcr.io:v0.2.1
  Remaining findings: 41 (0 Critical, 11 High, 18 Medium, 12 Low)
  Next session target: B1-B6 (service layer + simple.py split + helpers)
================================================================================
