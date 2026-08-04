# PhronesisML

**A transparent, inspectable alternative to AutoML — the ML lifecycle modeled as a graph of cooperating agents.**

---

## What is PhronesisML?

PhronesisML is a Python SDK that runs a complete machine learning pipeline through **11 cooperating agents**, each responsible for one stage of the ML lifecycle. Unlike black-box AutoML tools, every decision is inspectable, every stage is independently callable, and the entire pipeline operates on a typed, shared `WorkflowState`.

```python tab="OOP API"
from phronesisml import Phronesis

ml = Phronesis("data/customers.csv")
ml.run()
print(ml.report())
```

```python tab="Simple API"
from phronesisml import analyze, train

profile = analyze("data.csv")
print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")

result = train("data.csv")
print(f"Best model: {result.best_model_type}")
```

```python tab="CLI"
pip install phronesisml[cli]
phronesisml run data/customers.csv
```

---

## Why PhronesisML?

| | Notebooks | AutoML Tools | **PhronesisML** |
|:---|:---:|:---:|:---:|
| Structure | Ad hoc, cell-by-cell | Fixed, opaque | **Modular agents on typed state** |
| Transparency | High, but unorganized | Low — black box | **High — every decision is inspectable** |
| Overridable | N/A | Rarely | **Yes — imputation, encoding, model choice** |
| Reusable | Low | Low | **High — same pipeline, swap the data** |
| Works offline | Yes | Rarely | **Yes — by design** |

---

## The 11 Agents

PhronesisML models the ML lifecycle as a directed graph of cooperating agents:

```
Upload → ETL → Validation → EDA → Target Detection →
Feature Engineering → Model Selection → Evaluation →
Explainability → Reporting → Storage
```

| # | Agent | What It Does |
|---|-------|-------------|
| 1 | **Upload** | Loads CSV, Excel, Parquet, JSON, or Feather files |
| 2 | **ETL** | Cleans nulls, casts types, encodes categoricals |
| 3 | **Validation** | Checks for empty data, zero columns, duplicates |
| 4 | **EDA** | Statistical summaries, distributions, correlations |
| 5 | **Target Detection** | Automatically identifies the prediction target and task type |
| 6 | **Feature Engineering** | Encodes, scales, handles outliers, selects features |
| 7 | **Model Selection** | Evaluates candidates and picks the best model |
| 8 | **Evaluation** | Task-appropriate metrics (accuracy/F1 or RMSE/R2) |
| 9 | **Explainability** | SHAP-based feature importance |
| 10 | **Reporting** | Generates Markdown or HTML reports |
| 11 | **Storage** | Saves artifacts to disk |

Each stage is independently callable. Run the whole thing with `ml.run()`, or step through individually.

---

## Engine Abstraction

PhronesisML supports three computation backends, auto-selected based on data size:

| Engine | Best For | When Selected |
|--------|----------|---------------|
| **Pandas** | Small datasets (< 2 MB) | Default for quick exploration |
| **Polars** | Medium datasets (2–500 MB) | Fast, memory-efficient |
| **Spark** | Large datasets (> 500 MB) | Distributed computing |

```python
# Force a specific engine
from phronesisml import PhronesisConfig, Phronesis

config = PhronesisConfig()
config.engine.preferred = "polars"

ml = Phronesis("data.csv", config)
ml.run()
```

---

## Installation

```bash
# Core — CSV, Excel, Parquet, JSON, Feather
pip install phronesisml

# With extras
pip install phronesisml[cli]       # CLI commands
pip install phronesisml[all]       # everything
```

**Requirements:** Python 3.11+

---

## Quick Start

=== "Step 1: Install"

    ```bash
    pip install phronesisml
    ```

=== "Step 2: Run"

    ```python
    from phronesisml import Phronesis

    ml = Phronesis("your_data.csv")
    ml.run()
    ```

=== "Step 3: Inspect"

    ```python
    # View the report
    print(ml.report())

    # Get the trained model
    model = ml.get_model()

    # Get evaluation metrics
    metrics = ml.evaluate()
    print(metrics)
    ```

=== "Step 4: Customize"

    ```python
    from phronesisml import PhronesisConfig

    config = PhronesisConfig()
    config.engine.preferred = "polars"
    config.feature_selection.variance_threshold = 0.05

    ml = Phronesis("data.csv", config)
    ml.clean(null_strategy="fill", fill_value=0)
    ml.train(model_type="random_forest", cv=5)
    print(ml.report())
    ```

---

## What's Inside

<div class="grid cards" markdown>

-   **:material-school:{ .lg .middle } Learning Pipeline**

    ---

    11-stage ML pipeline with automatic target detection, model selection, and evaluation.

    [:octicons-arrow-right-24: Architecture](architecture.md)

-   **:material-cog:{ .lg .middle } Engine Abstraction**

    ---

    Pandas, Polars, or Spark — auto-selected by data size, or forced by config.

    [:octicons-arrow-right-24: Design Decisions](design-decisions.md)

-   **:material-api:{ .lg .middle } Three APIs**

    ---

    Simple one-liners, OOP method chaining, or full pipeline control.

    [:octicons-arrow-right-24: Guides](guides/simple-api.md)

-   **:material-server:{ .lg .middle } CLI**

    ---

    Typer CLI — the same SDK underneath.

    [:octicons-arrow-right-24: CLI](guides/cli.md)

</div>

---

## Links

- [:fontawesome-brands-github: GitHub](https://github.com/kartik00052/PhronesisML) — Source code
- [:fontawesome-brands-python: PyPI](https://pypi.org/project/phronesisml/) — Install package
- [:material-api: API Reference](api.md) — Every public method documented
- [:material-book: Guides](guides/incremental.md) — Step-by-step tutorials
- [:material-alert: Limitations](limitations.md) — What PhronesisML does *not* do (honest list)
