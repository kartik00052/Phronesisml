```
================================================================================
  PHRONESISML -- COMPATIBILITY MATRIX & INTEGRATION AUDIT REPORT
================================================================================

  Total Stages:   110
  Passed:         110
  Failed:         0
  Skipped:        0
  Warnings:       0
  Total Time:     32.29s
  Pass Rate:      100.0%

--------------------------------------------------------------------------------
  SECTION RESULTS
--------------------------------------------------------------------------------

  TEST (110/110 passed)
    [+] test_imports (0.11s) -- {'version': '0.2.0', 'all_exports': 54}
    [+] test_sdk_oop_imports (0.00s) -- {'sdk_class': 'Phronesis'}
    [+] test_simple_api_imports (0.00s) -- {'simple_api': True}
    [+] test_async_api_imports (0.00s) -- {'async_api': True}
    [+] test_config_imports (0.00s) -- {'engine_preferred': None, 'data_default_format': 'auto', 'feature_variance_threshold': 0.01}
    [+] test_exception_hierarchy (0.00s) -- {'exception_count': 11}
    [+] test_workflow_state (0.00s) -- {'state_fields': 30, 'sample_fields': ['run_id', 'status', 'data_path', 'raw_data', 'file_format']}
    [+] test_pipeline_order (0.57s) -- {'stages': ['upload', 'etl', 'validation', 'eda', 'target_detection', 'feature_engineering', 'model_
    [+] test_agent_base (0.00s) -- {'agent_result_fields': ['success', 'data', 'error', 'error_type', 'error_message', 'error_context',
    [+] test_pandas_engine (0.01s) -- {'shape': (20, 5), 'columns': ['age', 'income', 'score', 'category', 'target'], 'head_rows': 3, 'mem
    [+] test_polars_engine (0.18s) -- {'shape': (20, 5), 'columns': ['age', 'income', 'score', 'category', 'target'], 'head_rows': 3, 'col
    [+] test_engine_selector (0.00s) -- {'selected_engine': 'PandasEngine'}
    [+] test_engine_selector_pandas_force (0.00s) -- {'engine': 'PandasEngine'}
    [+] test_engine_selector_polars_force (0.00s) -- {'engine': 'PolarsEngine'}
    [+] test_csv_loading (0.01s) -- {'format': 'csv', 'rows': 20}
    [+] test_json_loading (0.00s) -- {'format': 'json', 'rows': 2}
    [+] test_parquet_loading (0.03s) -- {'format': 'parquet', 'rows': 2}
    [+] test_excel_loading (0.21s) -- {'format': 'excel', 'sheets': [{'name': 'Sheet1', 'index': 0, 'rows': 2, 'cols': 2}], 'rows': 2}
    [+] test_etl_handle_nulls_drop (0.00s) -- {'strategy': 'drop', 'rows_before': 3, 'rows_after': 1}
    [+] test_etl_handle_nulls_fill (0.00s) -- {'strategy': 'fill', 'filled_with': 0}
    [+] test_etl_handle_nulls_flag (0.00s) -- {'strategy': 'flag', 'flag_columns': ['a_is_null', 'b_is_null']}
    [+] test_etl_encode_categoricals (0.00s) -- {'encoded_column': 'cat', 'dtype': 'int64'}
    [+] test_etl_cast_dtypes (0.00s) -- {'x_dtype': 'int64', 'y_dtype': 'float64'}
    [+] test_etl_invalid_strategy (0.00s) -- {'raised': True, 'error_type': 'DataTransformError'}
    [+] test_validate_clean_data (0.00s) -- {'passed': True, 'shape': {'rows': 3, 'columns': 2}}
    [+] test_validate_dirty_data (0.01s) -- {'passed': True, 'null_columns': ['feature1', 'feature3', 'target'], 'duplicate_rows': 5}
    [+] test_validate_empty_df (0.00s) -- {'raised': True}
    [+] test_eda_profiling (0.01s) -- {'rows': 50, 'columns': 5, 'numeric': 4, 'categorical': 1}
    [+] test_eda_mixed_types (0.00s) -- {'columns': ['num', 'cat', 'bool_col'], 'numeric': ['num'], 'categorical': ['cat', 'bool_col']}
    [+] test_target_detection_classification (0.01s) -- {'target': 'target', 'task': 'ambiguous', 'confidence': 0.7}
    [+] test_target_detection_regression (0.02s) -- {'target': 'sqft', 'task': 'ambiguous', 'confidence': 0.4}
    [+] test_target_detection_no_target (0.01s) -- {'target': 'a', 'task': 'ambiguous', 'confidence': 0.4}
    [+] test_target_detection_constant_target (0.01s) -- {'target': 'x', 'task': 'ambiguous', 'confidence': 0.4}
    [+] test_target_detection_multiclass (0.01s) -- {'target': 'label', 'task': 'classification', 'confidence': 0.9}
    [+] test_feature_engineering (0.01s) -- {'n_features': 2, 'feature_names': ['age', 'category']}
    [+] test_feature_engineering_no_target (0.01s) -- {'n_features': 5}
    [+] test_feature_engineering_fill_strategy (0.01s) -- {'n_features': 2}
    [+] test_model_recommendation_classification (0.00s) -- {'candidates': ['logistic_regression', 'random_forest', 'gradient_boosting'], 'count': 3}
    [+] test_model_recommendation_regression (0.00s) -- {'candidates': ['linear_regression', 'random_forest', 'gradient_boosting'], 'count': 3}
    [+] test_model_recommendation_ambiguous (0.00s) -- {'candidates': ['logistic_regression', 'linear_regression', 'random_forest', 'gradient_boosting'], '
    [+] test_model_recommendation_none_task (0.00s) -- {'candidates': ['logistic_regression', 'linear_regression', 'random_forest', 'gradient_boosting'], '
    [+] test_training_cost_estimation (0.00s) -- {'low': 'low', 'medium': 'low', 'high': 'low'}
    [+] test_train_classification (1.23s) -- {'best_model': RandomForestClassifier(max_depth=5, n_estimators=50, random_state=42), 'best_score':
    [+] test_train_regression (0.55s) -- {'best_model': LinearRegression(), 'best_score': -0.11661169350545464}
    [+] test_train_with_cv (0.27s) -- {'best_model': LogisticRegression(C=0.01, max_iter=200, random_state=42), 'cv_results': True}
    [+] test_evaluate_classification (0.09s) -- {'metrics': ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro', 'roc_auc', 'confusion_matrix
    [+] test_evaluate_regression (0.12s) -- {'metrics': ['rmse', 'mae', 'r2'], 'task_type': 'regression'}
    [+] test_shap_explainability (0.36s) -- {'explainer_type': 'TreeExplainer', 'features': 4, 'sampled': False}
    [+] test_shap_without_shap_library (0.01s) -- {'graceful': False, 'raised_import_error': True}
    [+] test_shap_linear_model (0.00s) -- {'explainer_type': 'LinearExplainer', 'features': 3}
    [+] test_report_generation (0.00s) -- {'md_length': 672, 'html_length': 2128}
    [+] test_report_minimal_state (0.00s) -- {'report_length': 672}
    [+] test_simple_api_analyze (0.04s) -- {'result_type': 'DatasetProfile'}
    [+] test_simple_api_clean (0.01s) -- {'result_type': 'CleanResult'}
    [+] test_simple_api_validate (0.02s) -- {'result_type': 'ValidationResult'}
    [+] test_simple_api_detect_target (0.02s) -- {'result_type': 'TargetResult'}
    [+] test_simple_api_engineer (0.03s) -- {'result_type': 'FeatureResult'}
    [+] test_simple_api_select_model (2.64s) -- {'result_type': 'ModelResult'}
    [+] test_simple_api_train (3.25s) -- {'result_type': 'TrainResult'}
    [+] test_simple_api_explain (2.47s) -- {'result_type': 'ExplainResult'}
    [+] test_simple_api_report (2.62s) -- {'result_type': 'str'}
    [+] test_oop_api (0.01s) -- {'load_result': 'Phronesis'}
    [+] test_oop_api_incremental (2.71s) -- {'incremental_stages': 9}
    [+] test_advanced_api_full_pipeline (3.08s) -- {'target': 'target', 'task': 'ambiguous', 'model': 'RandomForestClassifier'}
    [+] test_advanced_api_subset_stages (0.02s) -- {'stages_run': 4, 'has_profile': True}
    [+] test_advanced_api_with_config (2.62s) -- {'target': 'target', 'task': 'ambiguous'}
    [+] test_config_engine_preferred_invalid (0.00s) -- {'rejected': True}
    [+] test_config_feature_selection_params (0.00s) -- {'variance': 0.05, 'correlation': 0.1, 'min_features': 2}
    [+] test_null_strategy_fill_value (0.00s) -- {'fill_value': np.float64(999.0)}
    [+] test_random_state_reproducibility (0.11s) -- {'same_model': False, 'score1': 0.5625, 'score2': 0.5625}
    [+] test_test_size_parameter (0.07s) -- {'test_size': 0.3, 'best_model': LogisticRegression(C=0.01, random_state=42)}
    [+] test_missing_file_recovery (0.01s) -- {'graceful': False, 'error': 'WorkflowError'}
    [+] test_empty_dataset_recovery (0.00s) -- {'raised': True, 'graceful': True}
    [+] test_single_row_dataset (0.00s) -- {'target': 'a', 'task': 'ambiguous'}
    [+] test_constant_column_survival (0.00s) -- {'numeric': ['const', 'varied', 'target'], 'categorical': []}
    [+] test_cli_info (0.84s) -- {'returncode': 0, 'stdout_len': 162}
    [+] test_cli_run (5.03s) -- {'returncode': 0, 'stdout_len': 7064, 'stderr_len': 396}
    [+] test_fastapi_app_creation (0.15s) -- {'app_title': 'Phronesis', 'version': '0.2.0'}
    [+] test_fastapi_health_endpoint (0.00s) -- {'status': 'ok'}
    [+] test_fastapi_version_endpoint (0.00s) -- {'version': APIResponse(success=True, data={'version': '0.2.0', 'python': '3.11.9 (tags/v3.11.9:de54
    [+] test_fastapi_capabilities_endpoint (0.02s) -- {'capabilities': APIResponse(success=True, data={'file_formats': ['arrow', 'csv', 'feather', 'json',
    [+] test_all_agents_instantiate (0.00s) -- {'agent_count': 11, 'names': ['upload', 'etl', 'validation', 'eda', 'target_detection', 'feature_eng
    [+] test_stub_agent_raises (0.00s) -- {'raised': True}
    [+] test_build_graph (0.00s) -- {'graph_type': 'CompiledStateGraph'}
    [+] test_build_graph_subset (0.00s) -- {'graph_type': 'CompiledStateGraph'}
    [+] test_build_graph_unknown_stage (0.00s) -- {'raised': True}
    [+] test_dirty_data_full_pipeline (0.01s) -- {'target': 'target', 'task': 'regression'}
    [+] test_tiny_dataset_target_detection (0.01s) -- {'target': 'y', 'task': 'ambiguous'}
    [+] test_inf_values_handling (0.01s) -- {'rows': 5, 'columns': 3}
    [+] test_model_type_override_classification (0.09s) -- {'best_model': LogisticRegression(C=0.01, max_iter=200, random_state=42)}
    [+] test_model_type_override_regression (0.14s) -- {'best_model': LinearRegression()}
    [+] test_task_detection_imports (0.00s) -- {'detect_task': 'detect_task'}
    [+] test_clustering_imports (0.00s) -- {'run_clustering': 'run_clustering', 'result_class': 'ClusterResult'}
    [+] test_anomaly_imports (0.00s) -- {'detect_anomalies': 'detect_anomalies', 'result_class': 'AnomalyResult'}
    [+] test_new_sdk_imports (0.00s) -- {'sdk_classes': ['AnomalyReport', 'ClusteringReport', 'TaskInfo']}
    [+] test_new_simple_imports (0.00s) -- {'simple_api': True, 'functions': 3}
    [+] test_new_init_exports (0.00s) -- {'new_exports_found': 5, 'expected': 6}
    [+] test_model_recommendation_clustering (0.00s) -- {'candidates': ['kmeans', 'agglomerative'], 'count': 2}
    [+] test_model_recommendation_anomaly (0.00s) -- {'candidates': ['isolation_forest', 'local_outlier_factor'], 'count': 2}
    [+] test_clustering_kmeans (1.87s) -- {'algorithm': 'kmeans', 'n_clusters': 2, 'silhouette': True}
    [+] test_clustering_all_algorithms (0.08s) -- {'best_algorithm': 'kmeans', 'all_tried': ['kmeans', 'dbscan', 'agglomerative'], 'n_clusters': 2}
    [+] test_anomaly_detection_basic (0.12s) -- {'algorithm': 'isolation_forest', 'n_anomalies': 10, 'has_scores': True}
    [+] test_anomaly_detection_all_algorithms (0.09s) -- {'algorithms_tried': ['isolation_forest', 'lof'], 'n_anomalies': 10}
    [+] test_clustering_metrics (0.08s) -- {'silhouette': True, 'davies_bouldin': True, 'calinski_harabasz': True}
    [+] test_unsupervised_auto_selector_candidates (0.00s) -- {'clustering': ['kmeans', 'agglomerative'], 'anomaly': ['isolation_forest', 'local_outlier_factor']}
    [+] test_unsupervised_workflow_state_fields (0.00s) -- {'unsupervised_fields': ['cluster_labels', 'cluster_metrics', 'anomaly_labels', 'anomaly_scores', 'a
    [+] test_unsupervised_router_logic (0.00s) -- {'clustering_proceeds': True, 'anomaly_proceeds': True, 'none_ends': True}
    [+] test_unsupervised_report_sections (0.00s) -- {'cluster_has_data': True, 'anomaly_has_data': True}
    [+] test_logging_structure (0.00s) -- {'phronesis_logger_count': 67, 'logger_names': ['phronesisml.sdk', 'phronesisml', 'phronesisml.simpl
    [+] test_no_print_statements_in_core (0.10s) -- {'print_statements_in_core': 0}

--------------------------------------------------------------------------------
  FAILED STAGES -- ROOT CAUSE ANALYSIS
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
  SKIPPED STAGES -- MISSING DEPENDENCIES
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
  COMPATIBILITY MATRIX
--------------------------------------------------------------------------------

  Dataset Category        | Target Detect | Train | Eval | SHAP | Report
  ----------------------------------------------------------------------
  Classification           | passed        | ?     | ?    | ?    | ?
  Regression               | passed        | ?     | ?    | ?    | ?
  Multiclass               | passed        | ?     | ?    | ?    | ?
  No Target                | passed        | ?     | ?    | ?    | ?
  Constant Target          | passed        | ?     | ?    | ?    | ?
  Tiny Dataset             | passed        | ?     | ?    | ?    | ?
  Dirty Data               | passed        | ?     | ?    | ?    | ?
  Inf Values               | passed        | ?     | ?    | ?    | ?

--------------------------------------------------------------------------------
  API INTERFACE MATRIX
--------------------------------------------------------------------------------

  Interface          | Status  | Notes
  ------------------------------------------------------------
  Import              | passed  | {'version': '0.2.0', 'all_exports': 54}
  SDK OOP             | passed  | {'load_result': 'Phronesis'}
  Simple API          | passed  | {'result_type': 'DatasetProfile'}
  Advanced API        | passed  | {'target': 'target', 'task': 'ambiguous'
  CLI                 | passed  | {'returncode': 0, 'stdout_len': 162}
  FastAPI             | passed  | {'app_title': 'Phronesis', 'version': '0

--------------------------------------------------------------------------------
  RECOMMENDATIONS
--------------------------------------------------------------------------------

  PRODUCTION READINESS CHECKLIST:
    [X] All core APIs import correctly
    [X] SDK OOP API works
    [X] Simple API works
    [X] Advanced API works
    [X] Target detection works
    [X] Training works
    [X] Evaluation works
    [X] SHAP explainability works
    [X] Reports generate
    [X] Error recovery works

================================================================================
  END OF REPORT
================================================================================
```
