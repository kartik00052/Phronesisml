# Getting Started

This guide covers installation, your first run, and how to use PhronesisML efficiently.

---

## Installation

### Basic Install

```bash
pip install phronesisml
```

This installs everything you need for CSV, Excel (.xlsx), Parquet, JSON, and Feather files.

### With Extras

```bash
pip install phronesisml[cli]       # CLI commands
pip install phronesisml[all]       # everything
```

### Requirements

- **Python:** 3.11 or later
- **OS:** Linux, macOS, Windows
- **Memory:** Depends on dataset size (Pandas loads full dataset into RAM)

### Verify Installation

```bash
phronesisml info
```

---

## Your First Run

### The Simplest Possible Usage

```python
from phronesisml import Phronesis

ml = Phronesis("your_data.csv")
ml.run()
print(ml.report())
```

That's it. PhronesisML will:

1. Load the CSV
2. Clean nulls and encode types
3. Validate the data
4. Run statistical analysis
5. Detect the prediction target
6. Engineer features
7. Select and train the best model
8. Evaluate performance
9. Generate explanations
10. Create a report
11. Save artifacts

### What You Get Back

```python
# The full report as Markdown
report = ml.report()

# The trained model (scikit-learn compatible)
model = ml.get_model()

# Evaluation metrics
metrics = ml.evaluate()

# The original data
df = ml.get_data()

# The cleaned data
cleaned = ml.get_cleaned_data()

# The engineered features
features = ml.get_features()
```

---

## Choosing the Right API

### Simple API — One-Liners

Best for quick exploration and scripting:

```python
from phronesisml import analyze, train, clean

# Profile a dataset
profile = analyze("data.csv")
print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")

# Clean data
result = clean("data.csv", null_strategy="fill")

# Train a model
result = train("data.csv")
print(f"Best model: {result.best_model_type}")
```

### OOP API — Method Chaining

Best for interactive exploration and Jupyter notebooks:

```python
from phronesisml import Phronesis

ml = Phronesis("data.csv")
ml.run()

# Step through stages
ml.load()
print(ml.summary())

ml.clean(null_strategy="fill")
ml.validate()
ml.eda()

target = ml.detect_target()
print(f"Target: {target.column} ({target.task_type})")

features = ml.engineer_features()
model = ml.train(model_type="random_forest")
```

### Advanced API — Full Control

Best for production pipelines and custom workflows:

```python
import asyncio
from phronesisml import run_pipeline, PhronesisConfig

async def main():
    config = PhronesisConfig()
    config.engine.preferred = "polars"

    result = await run_pipeline(
        data_path="data.csv",
        config=config,
        stages=["upload", "etl", "validation", "eda",
                "target_detection", "feature_engineering"],
    )
    print(result)

asyncio.run(main())
```

---

## Choosing an Engine

PhronesisML auto-selects the best engine based on data size:

| Data Size | Engine | Why |
|-----------|--------|-----|
| < 2 MB | Pandas | Fast startup, familiar API |
| 2–500 MB | Polars | 2-10x faster, lower memory |
| > 500 MB | Spark | Distributed computing |

### Force a Specific Engine

```python
from phronesisml import PhronesisConfig, Phronesis

config = PhronesisConfig()
config.engine.preferred = "polars"  # or "pandas" or "spark"

ml = Phronesis("data.csv", config)
ml.run()
```

### Or via Simple API

```python
from phronesisml import analyze

profile = analyze("data.csv", engine="polars")
```

---

## Null Handling Strategies

| Strategy | Behavior | Row Count | Best For |
|----------|----------|-----------|----------|
| `"drop"` (default) | Removes rows with nulls | Decreases | Clean datasets with few nulls |
| `"fill"` | Replaces nulls with a value | Preserves | When you need all rows |
| `"flag"` | Adds boolean indicator columns | Preserves | When nullity is informative |

```python
# Drop rows with nulls (default)
ml.clean(null_strategy="drop")

# Fill nulls
ml.clean(null_strategy="fill")

# Flag nulls as separate columns
ml.clean(null_strategy="flag")
```

---

## Training Specific Models

Skip auto-selection and train a specific algorithm:

```python
ml = Phronesis("data.csv")
ml.run()

# Train random forest directly
ml.train(model_type="random_forest")

# With cross-validation
ml.train(model_type="gradient_boosting", cv=5)
```

### Available Models

**Classification:** `logistic_regression`, `random_forest`, `gradient_boosting`

**Regression:** `linear_regression`, `random_forest`, `gradient_boosting`

---

## Using the CLI

```bash
# Install CLI extras
pip install phronesisml[cli]

# Run full pipeline
phronesisml run data/customers.csv

# With options
phronesisml run data.csv --engine polars --nulls fill --verbose

# Show version info
phronesisml info
```

---

## Efficiency Tips

### 1. Use Polars for Medium Datasets

Polars is 2-10x faster than Pandas for datasets that fit in memory:

```python
config = PhronesisConfig()
config.engine.preferred = "polars"
```

### 2. Skip Stages You Don't Need

Don't run the full pipeline if you only need analysis:

```python
# Just profile the data
from phronesisml import analyze
profile = analyze("data.csv")

# Just clean the data
from phronesisml import clean
result = clean("data.csv", null_strategy="fill")
```

### 3. Reuse the Phronesis Instance

After `run()`, you can call individual stages without re-running the full pipeline:

```python
ml = Phronesis("data.csv")
ml.run()

# Now experiment with different models
ml.train(model_type="random_forest")
ml.train(model_type="gradient_boosting")

# The data is already loaded and cleaned — no re-processing
```

### 4. Use Cross-Validation for Small Datasets

```python
ml.train(model_type="random_forest", cv=5)  # 5-fold CV
```

### 5. Force the Target Column

If auto-detection gets it wrong:

```python
# Run stages up to target detection
ml.load()
ml.clean()
ml.validate()
ml.eda()

# Manually set the target
# (The target detection agent will be skipped)
ml._state.target_column = "my_target_column"
ml._state.task_type = "classification"

# Continue from feature engineering
ml.engineer_features()
ml.train()
```

### 6. Cache the Graph

The LangGraph graph is cached automatically. Subsequent calls with the same configuration skip compilation:

```python
# First call: compiles the graph (~0.5s overhead)
ml1 = Phronesis("data1.csv")
ml1.run()

# Second call: reuses cached graph (no overhead)
ml2 = Phronesis("data2.csv")
ml2.run()
```

---

## Supported File Formats

| Format | Extensions | Read | Write |
|--------|-----------|------|-------|
| CSV | `.csv`, `.tsv` | Yes | Yes |
| Parquet | `.parquet`, `.pq` | Yes | Yes |
| JSON | `.json`, `.jsonl`, `.ndjson` | Yes | Yes |
| Feather | `.feather`, `.arrow` | Yes | Yes |
| Excel | `.xlsx` | Yes | No |
| Excel (legacy) | `.xls` | Yes* | No |
| IPC | `.ipc` | Yes (Polars only) | Yes (Polars only) |

\* Requires `pip install xlrd`

---

## What's Next?

- [Architecture](architecture.md) — How the system is built
- [Design Decisions](design-decisions.md) — Why we made the choices we did
- [Examples](examples.md) — Real-world code templates
- [API Reference](api.md) — Every public method documented
