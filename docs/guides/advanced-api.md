# Advanced API

For users who need full control over the pipeline — custom stage ordering, configuration objects, and direct access to the LangGraph workflow.

## `run_pipeline()`

The primary advanced entry point. Runs the pipeline with full configurability:

```python
import asyncio
from aetherml import run_pipeline, AetherMLConfig

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
| `config` | `AetherMLConfig \| None` | `None` | Pre-built config object |

### Available Stages

```
upload, etl, validation, eda, target_detection,
feature_engineering, model_selection, evaluation,
explainability, reporting, storage
```

## `AetherMLConfig`

Configure feature selection, engine preferences, and more:

```python
from aetherml import AetherMLConfig

config = AetherMLConfig()
```

## `WorkflowState`

The internal state object passed between agents. Exposes all intermediate results:

- `raw_data` — Original loaded DataFrame
- `processed_data` — Post-ETL DataFrame
- `validated_data` — Post-validation DataFrame
- `data_profile` — EDA profile dict
- `target_column` — Detected target column name
- `task_type` — `"classification"` or `"regression"`
- `features` — Engineered feature DataFrame
- `feature_names` — List of feature column names
- `trained_model` — The fitted sklearn model
- `best_pipeline` — Dict with model_type, score, best_params
- `evaluation_report` — Metrics dict
- `final_report` — Markdown report string
