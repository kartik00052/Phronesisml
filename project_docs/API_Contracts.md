# PhronesisML — API Contracts

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Public contract reference. Rendering source: `../docs/api.md` (mkdocstrings). Signatures must match the code — verify before changing. Contract rule: once a field ships, it is frozen; new fields are additive-only.

## 1. Package exports

```python
import phronesisml                      # cheap (~16 ms); lazy sdk/simple via __getattr__
from phronesisml import analyze, train  # simple API (sync)
from phronesisml import analyze_async, train_async  # async twins
from phronesisml import Phronesis, PhronesisConfig, run_pipeline, WorkflowState
from phronesisml.sdk import Phronesis
from phronesisml.simple import *        # 12 functions + result dataclasses
from phronesisml.exceptions import (
    PhronesisError, DataLoadError, DataTransformError, DataValidationError,
    EngineError, EngineSelectionError, WorkflowError, AgentError, ConfigurationError,
)
```

## 2. Simple API (sync + `*_async`)

`analyze, clean, validate, detect_target, detect_task, engineer, select_model, evaluate, explain, report, train, cluster, detect_anomalies`

Returns frozen dataclasses: `DatasetProfile, CleanResult, ValidationResult, TargetResult, FeatureResult, ModelResult, ExplainResult, TrainResult`.

Key params: `engine=` (pandas/polars/spark/auto), `null_strategy=` (`drop`/`fill`/`flag`), `fill_value=`, `stages=`. Sync functions use `asyncio.run()` internally — do not call from a running event loop; use `*_async`.

## 3. OOP API (`Phronesis`)

Stage methods (all return `self` unless noted): `load`, `summary` (→`DatasetSummary`), `clean`, `validate` (→`ValidationReport`), `eda` (→`EDAReport`), `detect_target` (→`TargetInfo`), `engineer_features` (→`FeatureReport`), `recommend_model` (→`ModelInfo`), `train` (→`ModelInfo`), `evaluate` (→`EvaluationMetrics`), `explain` (→`ExplanationReport`), `report` (→`str`), `generate_report(format)` (markdown/html), `run`, `get_data`, `get_cleaned_data`, `get_features`, `get_model`.

## 4. Advanced API

```python
run_pipeline(data_path, engine_preference=None, null_strategy="drop",
             stages=None, config=None, sampling_config=None) -> dict
```

`PhronesisConfig` sub-configs: `engine` (`preferred`, `spark_master="local[*]"`), `data` (`default_format="auto"`, `max_memory_bytes=500MB`, `max_file_size_bytes=2GB`), `feature_selection` (`variance_threshold=0.01`, `correlation_threshold=0.05`, `min_features`), `sampling`, `explain` (`max_samples=100`, `max_features=50`).

`WorkflowState` fields: `raw_data`, `processed_data`, `validated_data`, `data_profile`, `target_column`, `task_type` (`classification`/`regression`/`ambiguous`), `target_detection_confidence`, `features`, `feature_names`, `trained_model`, `best_pipeline` (with `params` + `best_params`), `evaluation_report`, `explanation_report`, `final_report`, `run_id`, `status`.

## 5. CLI

```
phronesisml run <dataset> [--engine/-e pandas|polars|spark] [--nulls/-n drop|fill|flag] [--verbose/-v]
phronesisml info
```
Exit codes: 0 success, 1 pipeline failed, 2 invalid arguments.

## 6. Engine-light data/ML modules (added 2026-08-04)

Exported through package `__init__.py` — see `MASTER_FUNCTION_MATRIX.md` for the full inventory. Notable contracts:

- `data/validation.py::generate_validation_report(df, target_column=None) -> dict` — numeric/categorical/datetime type maps are informational; schema/missing/duplicates/target contribute violations.
- `data/etl.py` + `feature_engineering/construction.py` transforms return `(result_df, log_dict)`.
- `ml/evaluation/report.py::compare_models(evaluations, higher_is_better=True) -> dict`.
- `ml/explainability/summary.py::explanation_summary(explanation, top_n=10) -> dict`.
- `services/storage.py::save_artifact(data, name, base_dir, fmt)` + `load_artifact(path)` + `list_artifacts(base_dir)` + `build_artifact_manifest(artifacts, run_id=None)`.

## 7. Error handling contract

- All SDK/simple exceptions subclass `PhronesisError`.
- Agents return `AgentResult(success, data, error, error_type, error_message, error_context)`; they MUST NOT raise for expected failures.
- `AgentError.error_type` / `.error_context` carry diagnostics to the boundary; raw tracebacks never leak through the SDK/CLI envelopes.

## 8. Determinism contract

Same dataset + config + seed → same metrics, best model, report, artifacts. Seeded RNG in sampling (`seed=42`), HPO, and explainability (`ExplainConfig.random_seed=42`).
