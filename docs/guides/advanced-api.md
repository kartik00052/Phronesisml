# Advanced API

For users who need full control over the pipeline — custom stage ordering, configuration objects, and direct access to the LangGraph workflow.

---

## `run_pipeline()`

The primary advanced entry point. Runs the pipeline with full configurability:

```python
import asyncio
from phronesisml import run_pipeline, PhronesisConfig

async def main():
    result = await run_pipeline(
        data_path="data/customers.csv",
        engine_preference="polars",
        null_strategy="fill",
        stages=["upload", "etl", "validation", "eda", "target_detection",
                "feature_engineering", "model_selection", "evaluation"],
    )
    print(result)

asyncio.run(main())
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data_path` | `str` | *(required)* | Path to dataset |
| `engine_preference` | `str \| None` | `None` | Force `"pandas"`, `"polars"`, or `"spark"` |
| `null_strategy` | `str` | `"drop"` | Null handling: `"drop"`, `"fill"`, `"flag"` |
| `stages` | `list[str] \| None` | `None` | Subset of stages to run (default: all 11) |
| `config` | `PhronesisConfig \| None` | `None` | Pre-built config object |

### Available Stages

```
upload, etl, validation, eda, target_detection,
feature_engineering, model_selection, evaluation,
explainability, reporting, storage
```

### Running a Subset of Stages

```python
# Just upload and ETL
result = await run_pipeline(
    data_path="data.csv",
    stages=["upload", "etl"],
)

# Everything except explainability and storage
result = await run_pipeline(
    data_path="data.csv",
    stages=["upload", "etl", "validation", "eda", "target_detection",
            "feature_engineering", "model_selection", "evaluation",
            "reporting"],
)
```

---

## `PhronesisConfig`

Configure feature selection, engine preferences, and more:

```python
from phronesisml import PhronesisConfig

config = PhronesisConfig()
```

### Full Configuration Reference

#### Engine Configuration

```python
config.engine.preferred = "polars"  # "pandas", "polars", "spark", or None (auto)
config.engine.spark_master = "local[*]"  # Spark master URL
```

#### Data Configuration

```python
config.data.default_format = "auto"  # "auto", "csv", "parquet", "json"
config.data.max_memory_bytes = 500 * 1024 * 1024  # 500 MB threshold for Spark
config.data.max_file_size_bytes = 2 * 1024 * 1024 * 1024  # 2 GB max upload
```

#### Feature Selection Configuration

```python
config.feature_selection.variance_threshold = 0.01  # Drop features below this variance
config.feature_selection.correlation_threshold = 0.05  # Drop features below this correlation
config.feature_selection.min_features = 1  # Keep at least this many features
```

### Configuration Templates

#### Minimal (Defaults)

```python
config = PhronesisConfig()
```

#### Performance-Tuned

```python
config = PhronesisConfig()
config.engine.preferred = "polars"
config.data.max_memory_bytes = 1_000_000_000  # 1 GB
```

#### Conservative (Keep More Features)

```python
config = PhronesisConfig()
config.feature_selection.variance_threshold = 0.001
config.feature_selection.correlation_threshold = 0.01
config.feature_selection.min_features = 10
```

#### Aggressive (Drop More Features)

```python
config = PhronesisConfig()
config.feature_selection.variance_threshold = 0.1
config.feature_selection.correlation_threshold = 0.2
config.feature_selection.min_features = 3
```

---

## `WorkflowState`

The internal state object passed between agents. Exposes all intermediate results:

### State Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw_data` | `DataFrame \| None` | Original loaded DataFrame |
| `processed_data` | `DataFrame \| None` | Post-ETL DataFrame |
| `validated_data` | `DataFrame \| None` | Post-validation DataFrame |
| `data_profile` | `dict \| None` | EDA profile (statistics, distributions) |
| `target_column` | `str \| None` | Detected target column name |
| `task_type` | `str \| None` | `"classification"`, `"regression"`, or `"ambiguous"` |
| `target_detection_confidence` | `float \| None` | Confidence score (0.0–1.0) |
| `features` | `DataFrame \| None` | Engineered feature DataFrame |
| `feature_names` | `list[str] \| None` | Feature column names |
| `trained_model` | `Any \| None` | The fitted scikit-learn model |
| `best_pipeline` | `dict \| None` | Model type, score, best params |
| `evaluation_report` | `dict \| None` | Metrics (accuracy, F1, RMSE, etc.) |
| `final_report` | `str \| None` | Markdown report string |

### Accessing State After `run()`

```python
ml = Phronesis("data.csv")
ml.run()

# Access internal state
state = ml._state

print(f"Raw data: {state.raw_data.shape}")
print(f"Target: {state.target_column}")
print(f"Task: {state.task_type}")
print(f"Model: {type(state.trained_model).__name__}")
```

---

## OOP API — Method Chaining

`load()` and `clean()` return `self`, so those stages can be chained:

```python
from phronesisml import Phronesis

# Chain the self-returning stages
ml = (Phronesis("data.csv")
    .load()
    .clean(null_strategy="fill"))
validation = ml.validate()
eda = ml.eda()
target = ml.detect_target()
features = ml.engineer_features()
model = ml.train(model_type="random_forest")
metrics = ml.evaluate()
report = ml.report()

print(report)
```

### Individual Stage Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `load()` | `self` | Load data from file |
| `summary()` | `DatasetSummary` | Shape, memory, column info |
| `clean(null_strategy)` | `self` | ETL: null handling, type casting |
| `validate()` | `ValidationReport` | Data quality checks |
| `eda()` | `EDAReport` | Statistical profiling |
| `detect_target()` | `TargetInfo` | Target column and task type |
| `engineer_features()` | `FeatureReport` | Feature engineering results |
| `recommend_model()` | `ModelInfo` | Model selection (no training) |
| `train(model_type, cv)` | `ModelInfo` | Train a specific model |
| `evaluate()` | `EvaluationMetrics` | Task-appropriate metrics |
| `explain()` | `ExplanationReport` | SHAP feature importance |
| `report()` | `str` | Full Markdown report |
| `generate_report(format)` | `str` | Report in specific format |

---

## Error Handling

The advanced API provides structured error information:

```python
from phronesisml import run_pipeline
from phronesisml.exceptions import (
    PhronesisError,
    DataLoadError,
    DataValidationError,
    EngineError,
    WorkflowError,
    AgentError,
)

try:
    result = await run_pipeline(data_path="data.csv")
except DataLoadError as e:
    print(f"Failed to load: {e}")
except DataValidationError as e:
    print(f"Validation failed: {e}")
except EngineError as e:
    print(f"Engine error: {e}")
except WorkflowError as e:
    print(f"Pipeline failed: {e}")
except AgentError as e:
    print(f"Agent failed: {e}")
    print(f"Error type: {e.error_type}")
    print(f"Context: {e.error_context}")
except PhronesisError as e:
    print(f"Phronesis error: {e}")
```

---

## Complete Example

```python
import asyncio
from phronesisml import run_pipeline, PhronesisConfig

async def main():
    # Configure
    config = PhronesisConfig()
    config.engine.preferred = "polars"
    config.feature_selection.variance_threshold = 0.05
    config.feature_selection.min_features = 5

    # Run pipeline
    result = await run_pipeline(
        data_path="data/customers.csv",
        config=config,
        stages=["upload", "etl", "validation", "eda",
                "target_detection", "feature_engineering",
                "model_selection", "evaluation", "reporting"],
    )

    # Inspect results
    print(f"Target: {result.get('target_column')}")
    print(f"Task: {result.get('task_type')}")
    print(f"Model: {result.get('best_pipeline', {}).get('model_type')}")
    print(f"Report:\n{result.get('final_report', '')[:500]}")

asyncio.run(main())
```
