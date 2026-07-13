# Incremental Usage

Instead of running the full pipeline with `ml.run()`, you can execute stages individually and inspect intermediate results.

## Step-by-Step Example

```python
from aetherml import AetherML

ml = AetherML("data/customers.csv")

# 1. Load and inspect
ml.load()
summary = ml.summary()
print(f"{summary.rows} rows, {summary.columns} columns")
print(f"Memory: {summary.memory_mb:.1f} MB")

# 2. Clean
ml.clean(null_strategy="fill", fill_value=0)
cleaned = ml.get_cleaned_data()

# 3. Validate
validation = ml.validate()
if not validation.passed:
    print(f"Issues: {validation.null_columns}")

# 4. EDA
eda = ml.eda()
print(f"Numeric columns: {eda.numeric_columns}")

# 5. Target detection
target = ml.detect_target()
print(f"Target: {target.column} ({target.task_type})")

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

## Using `model_type` Override

Pass `model_type` to `train()` or `recommend_model()` to skip model selection and train a specific algorithm directly:

```python
ml = AetherML("data.csv")
ml.run()  # or call stages incrementally

# Train a specific model instead of auto-selecting
ml.train(model_type="random_forest")
```

Supported model types include `random_forest`, `logistic_regression`, `gradient_boosting`, `svc`, and more. Pass any model name that scikit-learn supports.

## Cross-Validation

Enable k-fold cross-validation by passing `cv`:

```python
model = ml.train(cv=5)  # 5-fold cross-validation
```

## Method Chaining

All stage methods return `self`, so you can chain calls:

```python
result = AetherML("data.csv").load().clean().validate().eda().detect_target().engineer_features()
```

!!! note
    When chaining, the pipeline runs each stage on every method call. If you've already called `run()`, subsequent stage calls are deduplicated and won't re-run completed stages.
