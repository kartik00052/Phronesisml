# Incremental Usage

Instead of running the full pipeline with `ml.run()`, you can execute stages individually and inspect intermediate results. This is useful for debugging, experimentation, and understanding how each stage transforms your data.

---

## Step-by-Step Example

```python
from phronesisml import Phronesis

ml = Phronesis("data/customers.csv")

# 1. Load and inspect
ml.load()
summary = ml.summary()
print(f"{summary.rows} rows, {summary.columns} columns")
print(f"Memory: {summary.memory_mb:.1f} MB")

# 2. Clean
ml.clean(null_strategy="fill")
cleaned = ml.get_cleaned_data()
print(f"After cleaning: {cleaned.shape}")

# 3. Validate
validation = ml.validate()
if not validation.passed:
    print(f"Issues: {validation.null_columns}")

# 4. EDA
eda = ml.eda()
print(f"Numeric columns: {eda.numeric_columns}")
print(f"Categorical columns: {eda.categorical_columns}")

# 5. Target detection
target = ml.detect_target()
print(f"Target: {target.column} ({target.task_type})")
print(f"Confidence: {target.confidence:.2f}")

# 6. Feature engineering
features = ml.engineer_features()
print(f"{features.n_features} features engineered")

# 7. Train a specific model (skip auto-selection)
model = ml.train(model_type="random_forest")
print(f"Model: {model.model_type}, score: {model.score:.4f}")

# 8. Evaluate
metrics = ml.evaluate()
print(f"Accuracy: {metrics.accuracy:.4f}")

# 9. Generate report
print(ml.report())
```

---

## Stage Reference

| # | Method | What It Does | Returns |
|---|--------|-------------|---------|
| 1 | `load()` | Load data from file | `self` |
| 2 | `summary()` | Get shape, memory, columns | `DatasetSummary` |
| 3 | `clean(null_strategy)` | ETL: nulls, types, encoding | `self` |
| 4 | `validate()` | Check data quality | `ValidationReport` |
| 5 | `eda()` | Statistical profiling | `EDAReport` |
| 6 | `detect_target()` | Find prediction target | `TargetInfo` |
| 7 | `engineer_features()` | Transform features | `FeatureReport` |
| 8 | `train(model_type, cv)` | Train a model | `ModelInfo` |
| 9 | `evaluate()` | Compute metrics | `EvaluationMetrics` |
| 10 | `explain()` | SHAP feature importance | `ExplanationReport` |
| 11 | `report()` | Generate Markdown report | `str` |

---

## Using `model_type` Override

Pass `model_type` to `train()` or `recommend_model()` to skip model selection and train a specific algorithm directly:

```python
ml = Phronesis("data.csv")
ml.run()  # or call stages incrementally

# Train a specific model instead of auto-selecting
ml.train(model_type="random_forest")
```

### Available Model Types

**Classification:**

| Model | Type | Best For |
|-------|------|----------|
| `logistic_regression` | Linear | Small datasets, interpretability |
| `random_forest` | Ensemble | General purpose, robust |
| `gradient_boosting` | Ensemble | High performance |

**Regression:**

| Model | Type | Best For |
|-------|------|----------|
| `linear_regression` | Linear | Simple relationships |
| `random_forest` | Ensemble | General purpose, robust |
| `gradient_boosting` | Ensemble | High performance |

---

## Cross-Validation

Enable k-fold cross-validation by passing `cv`:

```python
model = ml.train(cv=5)  # 5-fold cross-validation
```

### When to Use CV

- **Small datasets (< 500 rows):** Always use CV for reliable estimates
- **Medium datasets (500–5000 rows):** CV is helpful but not critical
- **Large datasets (> 5000 rows):** Single train/test split is usually sufficient

---

## Method Chaining

`load()` and `clean()` return `self`, so those stages can be chained:

```python
ml = (Phronesis("data.csv")
    .load()
    .clean())
validation = ml.validate()
eda = ml.eda()
target = ml.detect_target()
features = ml.engineer_features()
```

!!! note
    `validate()`, `eda()`, `detect_target()`, and `engineer_features()` return typed
    result objects rather than `self`; chain only the `self`-returning stages
    (`load`, `clean`). When chaining, the pipeline runs each stage on every method
    call. If you've already called `run()`, subsequent stage calls are deduplicated
    and won't re-run completed stages.

---

## Inspecting Intermediate Results

After each stage, you can inspect the data:

```python
ml = Phronesis("data.csv")

# Before and after each stage
ml.load()
raw = ml.get_data()
print(f"Raw: {raw.shape}")

ml.clean(null_strategy="fill")
cleaned = ml.get_cleaned_data()
print(f"Cleaned: {cleaned.shape}")

ml.validate()
ml.eda()
ml.detect_target()

# Get the target info
target = ml._state.target_column
task = ml._state.task_type
confidence = ml._state.target_detection_confidence
print(f"Target: {target} ({task}, confidence={confidence:.2f})")

ml.engineer_features()
features = ml.get_features()
print(f"Features: {features.shape}")

ml.train()
model = ml.get_model()
print(f"Model: {type(model).__name__}")
```

---

## Debugging with Incremental Usage

When `ml.run()` fails, use incremental usage to find the failing stage:

```python
ml = Phronesis("data.csv")

# Run each stage and check for errors
try:
    ml.load()
    print("✓ load")
except Exception as e:
    print(f"✗ load: {e}")
    raise

try:
    ml.clean()
    print("✓ clean")
except Exception as e:
    print(f"✗ clean: {e}")
    raise

try:
    ml.validate()
    print("✓ validate")
except Exception as e:
    print(f"✗ validate: {e}")
    raise

# ... continue for each stage
```

---

## Complete Example: Custom Pipeline

```python
from phronesisml import Phronesis, PhronesisConfig

# Configure
config = PhronesisConfig()
config.engine.preferred = "polars"
config.feature_selection.variance_threshold = 0.05

# Build pipeline step by step
ml = Phronesis("data.csv", config)

# Stage 1-2: Load and clean
ml.load()
ml.clean(null_strategy="flag")  # Flag nulls instead of dropping

# Stage 3: Validate
validation = ml.validate()
if not validation.passed:
    print(f"Warning: {validation.null_columns}")

# Stage 4-5: EDA and target detection
ml.eda()
target = ml.detect_target()
print(f"Detected: {target.column} ({target.task_type})")

# Stage 6: Feature engineering
features = ml.engineer_features()

# Stage 7: Train with cross-validation
ml.train(model_type="gradient_boosting", cv=5)

# Stage 8-9: Evaluate and explain
metrics = ml.evaluate()
explanation = ml.explain()

# Stage 10-11: Report and save
report = ml.report()
print(report)

# Access the trained model
model = ml.get_model()
print(f"Final model: {type(model).__name__}")
```
