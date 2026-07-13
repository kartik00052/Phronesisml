# Simple API

The Simple API provides one-liner functions that run relevant pipeline stages and return frozen dataclasses. No setup, no configuration — just call a function.

## Functions

| Function | What it does | Returns |
|---|---|---|
| `analyze(path)` | Upload → ETL → Validation → EDA | `DatasetProfile` |
| `clean(path)` | Upload → ETL | `CleanResult` |
| `validate(path)` | Upload → ETL → Validation | `ValidationResult` |
| `detect_target(path)` | Upload → ... → Target Detection | `TargetResult` |
| `engineer(path)` | Upload → ... → Feature Engineering | `FeatureResult` |
| `select_model(path)` | Upload → ... → Model Selection + Evaluation | `ModelResult` |
| `explain(path)` | Upload → ... → Explainability | `ExplainResult` |
| `report(path)` | Upload → ... → Reporting | `str` (Markdown) |
| `train(path)` | Full pipeline (all 11 stages) | `TrainResult` |

## Basic Usage

```python
from phronesisml import analyze, train

# Profile a dataset
profile = analyze("data.csv")
print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")
print(f"Memory: {profile.memory_usage_bytes / 1024:.1f} KB")

# Train a full model
result = train("data.csv")
print(f"Best model: {result.best_model_type}")
print(f"Score: {result.best_score:.4f}")
print(result.report[:500])
```

## Choosing an Engine

Force a specific engine with the `engine` parameter:

```python
profile = analyze("data.csv", engine="polars")
```

## Null Handling

Control how nulls are handled:

```python
result = clean("data.csv", null_strategy="fill")
```

Strategies: `"drop"` (default), `"fill"`, `"flag"`.

## Async Variants

Every function has an `_async` variant for use inside FastAPI or Jupyter async mode:

```python
from phronesisml import analyze_async

profile = await analyze_async("data.csv")
```

!!! warning
    The sync functions use `asyncio.run()` internally. Do not call them from inside a running event loop (FastAPI handlers, Jupyter async cells). Use the `_async` variants instead.
