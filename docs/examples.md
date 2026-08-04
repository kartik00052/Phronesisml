# Examples

Real-world code templates for common use cases. Copy, paste, adapt.

---

## Tabular Classification

### Binary Classification (Churn Prediction)

```python
from phronesisml import Phronesis, PhronesisConfig

config = PhronesisConfig()
config.engine.preferred = "polars"

ml = Phronesis("customer_churn.csv", config)
ml.run()

# Inspect results
print(ml.report())
print(f"Target: {ml._state.target_column}")
print(f"Task: {ml._state.task_type}")

# Get the trained model
model = ml.get_model()
print(f"Model type: {type(model).__name__}")

# Predict on new data
import pandas as pd
new_data = pd.read_csv("new_customers.csv")
predictions = model.predict(ml.get_features())
```

### Multi-Class Classification

```python
from phronesisml import analyze, train

# Profile first
profile = analyze("iris.csv")
print(f"Classes: {profile.shape[1]} columns")
print(f"Numeric: {len(profile.numeric_columns)} columns")

# Train
result = train("iris.csv")
print(f"Best model: {result.best_model_type}")
print(f"Accuracy: {result.best_score:.4f}")
```

---

## Tabular Regression

### House Price Prediction

```python
from phronesisml import Phronesis

ml = Phronesis("house_prices.csv")
ml.run()

# The pipeline auto-detects regression
print(f"Task type: {ml._state.task_type}")

# Evaluate with regression metrics
metrics = ml.evaluate()
print(f"RMSE: {metrics.get('rmse', 'N/A')}")
print(f"R²: {metrics.get('r2', 'N/A')}")
```

### With Feature Selection Tuning

```python
from phronesisml import PhronesisConfig, Phronesis

config = PhronesisConfig()
config.feature_selection.variance_threshold = 0.05  # Drop low-variance features
config.feature_selection.correlation_threshold = 0.1  # Drop low-correlation features
config.feature_selection.min_features = 5  # Keep at least 5 features

ml = Phronesis("housing.csv", config)
ml.run()
print(ml.report())
```

---

## Data Profiling

### Quick Dataset Profile

```python
from phronesisml import analyze

profile = analyze("data.csv")

print(f"Shape: {profile.shape}")
print(f"Memory: {profile.memory_usage_bytes / 1024:.1f} KB")
print(f"Numeric columns: {profile.numeric_columns}")
print(f"Categorical columns: {profile.categorical_columns}")
```

### Profile with Specific Engine

```python
from phronesisml import analyze

# Use Polars for faster profiling on medium datasets
profile = analyze("medium_dataset.csv", engine="polars")

# Use Pandas for compatibility
profile = analyze("data.csv", engine="pandas")
```

---

## Data Cleaning

### Clean with Different Strategies

```python
from phronesisml import clean

# Drop rows with nulls
result = clean("messy_data.csv", null_strategy="drop")
print(f"Rows after cleaning: {result.shape[0]}")

# Fill nulls with column median
result = clean("messy_data.csv", null_strategy="fill", fill_value=0)
print(f"Rows preserved: {result.shape[0]}")

# Flag nulls as separate columns
result = clean("messy_data.csv", null_strategy="flag")
print(f"Columns added for null flags: {result.shape[1]}")
```

---

## Incremental Pipeline

### Step-by-Step with Inspection

```python
from phronesisml import Phronesis

ml = Phronesis("data.csv")

# 1. Load
ml.load()
summary = ml.summary()
print(f"Loaded: {summary.rows} rows, {summary.columns} columns")
print(f"Memory: {summary.memory_mb:.1f} MB")

# 2. Clean
ml.clean(null_strategy="fill", fill_value=0)
cleaned = ml.get_cleaned_data()
print(f"After cleaning: {cleaned.shape}")

# 3. Validate
validation = ml.validate()
if not validation.passed:
    print(f"Validation issues: {validation.null_columns}")

# 4. EDA
eda = ml.eda()
print(f"Numeric columns: {eda.numeric_columns}")
print(f"Categorical columns: {eda.categorical_columns}")

# 5. Target detection
target = ml.detect_target()
print(f"Detected target: {target.column}")
print(f"Task type: {target.task_type}")
print(f"Confidence: {target.confidence:.2f}")

# 6. Feature engineering
features = ml.engineer_features()
print(f"Features engineered: {features.n_features}")

# 7. Train
model = ml.train(model_type="random_forest")
print(f"Model: {model.model_type}, score: {model.score:.4f}")

# 8. Evaluate
metrics = ml.evaluate()
print(f"Metrics: {metrics}")

# 9. Explain
explanation = ml.explain()
print(f"Top features: {list(explanation.feature_importance.keys())[:5]}")

# 10. Report
print(ml.report())
```

---

## CLI Usage

### Basic Commands

```bash
# Run full pipeline
phronesisml run data/customers.csv

# With engine selection
phronesisml run data.csv --engine polars

# With null strategy
phronesisml run data.csv --nulls fill

# Verbose output
phronesisml run data.csv -v

# Show version info
phronesisml info
```

---

## Configuration Templates

### Minimal Config

```python
from phronesisml import PhronesisConfig

config = PhronesisConfig()
# All defaults — Pandas auto-select, drop nulls, standard thresholds
```

### Performance Config

```python
from phronesisml import PhronesisConfig

config = PhronesisConfig()
config.engine.preferred = "polars"
config.data.max_memory_bytes = 1_000_000_000  # 1 GB threshold for Spark
```

### Conservative Config

```python
from phronesisml import PhronesisConfig

config = PhronesisConfig()
config.feature_selection.variance_threshold = 0.01
config.feature_selection.correlation_threshold = 0.05
config.feature_selection.min_features = 10  # Keep at least 10 features
```

### Aggressive Config

```python
from phronesisml import PhronesisConfig

config = PhronesisConfig()
config.feature_selection.variance_threshold = 0.1
config.feature_selection.correlation_threshold = 0.2
config.feature_selection.min_features = 3  # Keep at least 3 features
```

---

## Advanced Patterns

### Parallel Model Comparison

```python
from phronesisml import Phronesis

ml = Phronesis("data.csv")
ml.run()

# Train multiple models and compare
models = {}
for model_type in ["random_forest", "gradient_boosting", "logistic_regression"]:
    ml.train(model_type=model_type)
    metrics = ml.evaluate()
    models[model_type] = metrics

# Compare results
for name, metrics in models.items():
    print(f"{name}: {metrics}")
```

### Custom Feature Engineering

```python
from phronesisml import Phronesis

ml = Phronesis("data.csv")

# Run up to target detection
ml.load()
ml.clean()
ml.validate()
ml.eda()
target = ml.detect_target()

# Get the state and customize
state = ml._state

# Add custom features manually
import pandas as pd
df = state.validated_data.copy()
df["custom_feature"] = df["col1"] * df["col2"]
df["log_transform"] = np.log1p(df["col3"])

# Set the modified data back
state.processed_data = df

# Continue with default feature engineering
ml.engineer_features()
ml.train()
print(ml.report())
```

### Exporting Results

```python
from phronesisml import Phronesis
import json

ml = Phronesis("data.csv")
ml.run()

# Export report
with open("report.md", "w") as f:
    f.write(ml.report())

# Export metrics
metrics = ml.evaluate()
with open("metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

# Export model
import joblib
joblib.dump(ml.get_model(), "model.pkl")

# Export features
features = ml.get_features()
features.to_csv("engineered_features.csv", index=False)
```
