# Simple API

Zero-friction one-liner functions. Each runs the relevant pipeline stages and returns a frozen dataclass. No setup, no configuration — just call a function.

---

## Available Functions

| Function | Stages Run | Returns | Use Case |
|---|---|---|---|
| `analyze(path)` | Upload → ETL → Validation → EDA | `DatasetProfile` | Quick data profiling |
| `clean(path)` | Upload → ETL | `CleanResult` | Data cleaning only |
| `validate(path)` | Upload → ETL → Validation | `ValidationResult` | Quality checks |
| `detect_target(path)` | Upload → ... → Target Detection | `TargetResult` | Find prediction target |
| `engineer(path)` | Upload → ... → Feature Engineering | `FeatureResult` | Feature pipeline |
| `select_model(path)` | Upload → ... → Model Selection + Evaluation | `ModelResult` | Model comparison |
| `explain(path)` | Upload → ... → Explainability | `ExplainResult` | Feature importance |
| `report(path)` | Upload → ... → Reporting | `str` (Markdown) | Full report |
| `train(path)` | All 11 stages | `TrainResult` | Complete pipeline |

---

## Basic Usage

### Profile a Dataset

```python
from phronesisml import analyze

profile = analyze("data.csv")
print(f"Shape: {profile.shape}")
print(f"Memory: {profile.memory_usage_bytes / 1024:.1f} KB")
print(f"Numeric columns: {profile.numeric_columns}")
print(f"Categorical columns: {profile.categorical_columns}")
```

### Train a Model

```python
from phronesisml import train

result = train("data.csv")
print(f"Best model: {result.best_model_type}")
print(f"Score: {result.best_score:.4f}")
print(result.report[:500])  # First 500 chars of the report
```

### Clean Data

```python
from phronesisml import clean

result = clean("messy_data.csv", null_strategy="fill")
print(f"Shape after cleaning: {result.shape}")
```

---

## Engine Selection

Force a specific engine with the `engine` parameter:

```python
# Use Polars for faster processing
profile = analyze("data.csv", engine="polars")

# Use Pandas for compatibility
result = train("data.csv", engine="pandas")

# Use Spark for large datasets
profile = analyze("huge_data.csv", engine="spark")
```

**Auto-selection (default):**

| Data Size | Engine |
|-----------|--------|
| < 2 MB | Pandas |
| 2–500 MB | Polars |
| > 500 MB | Spark |

---

## Null Handling

Control how nulls are handled during the ETL stage:

```python
# Drop rows with nulls (default)
result = clean("data.csv", null_strategy="drop")

# Fill nulls with a specific value
result = clean("data.csv", null_strategy="fill", fill_value=0)

# Flag nulls as separate columns
result = clean("data.csv", null_strategy="flag")
```

### Strategy Comparison

| Strategy | Row Count | Columns | Best For |
|----------|-----------|---------|----------|
| `"drop"` | Decreases | Same | Clean datasets |
| `"fill"` | Preserves | Same | When you need all rows |
| `"flag"` | Preserves | Increases | When nullity is informative |

---

## Result Types

Each function returns a specific frozen dataclass:

### DatasetProfile (from `analyze`)

```python
profile = analyze("data.csv")

profile.shape              # (rows, columns)
profile.memory_usage_bytes # int
profile.numeric_columns    # list[str]
profile.categorical_columns # list[str]
profile.preview            # str (first 5 rows as text)
```

### TrainResult (from `train`)

```python
result = train("data.csv")

result.best_model_type     # str (e.g. "random_forest")
result.best_score          # float
result.report              # str (full Markdown report)
```

### ModelResult (from `select_model`)

```python
result = select_model("data.csv")

result.best_model_type     # str
result.best_score          # float
result.candidates          # list[dict] (all evaluated models)
```

---

## Async Variants

Every function has an `_async` variant for use inside a running async context (e.g. Jupyter async cells, your own asyncio app):

```python
from phronesisml import analyze_async, train_async

# In an async context
profile = await analyze_async("data.csv")
result = await train_async("data.csv")
```

!!! warning
    The sync functions use `asyncio.run()` internally. Do not call them from inside a running event loop (Jupyter async cells). Use the `_async` variants instead.

---

## Error Handling

All functions raise `PhronesisError` subclasses on failure:

```python
from phronesisml import analyze
from phronesisml.exceptions import DataLoadError, DataValidationError

try:
    profile = analyze("data.csv")
except DataLoadError as e:
    print(f"Failed to load data: {e}")
except DataValidationError as e:
    print(f"Data validation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Complete Example

```python
from phronesisml import analyze, clean, train, detect_target

# Step 1: Profile
profile = analyze("customers.csv", engine="polars")
print(f"Dataset: {profile.shape[0]} rows, {profile.shape[1]} columns")

# Step 2: Clean
result = clean("customers.csv", null_strategy="fill")
print(f"Cleaned: {result.shape[0]} rows")

# Step 3: Detect target
target = detect_target("customers.csv")
print(f"Target: {target.column} ({target.task_type})")

# Step 4: Train
result = train("customers.csv")
print(f"Best model: {result.best_model_type} (score: {result.best_score:.4f})")
```
