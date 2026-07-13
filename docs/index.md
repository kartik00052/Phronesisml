---
hide:
  - navigation
---

<p align="center">
  <img src="../assets/banner.png" alt="AetherML" width="100%"/>
</p>

# AetherML

**A transparent, inspectable alternative to AutoML — the ML lifecycle modeled as a graph of cooperating agents.**

---

## Quick Start

=== "OOP API"

    ```python
    from aetherml import AetherML

    ml = AetherML("data/customers.csv")
    ml.run()
    print(ml.report())
    ```

=== "Simple API"

    ```python
    from aetherml import analyze, train

    profile = analyze("data.csv")
    print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")

    result = train("data.csv")
    print(f"Best model: {result.best_model_type}")
    ```

=== "CLI"

    ```bash
    pip install aetherml[cli]
    aetherml run data/customers.csv
    ```

### Installation

```bash
pip install aetherml
```

This installs everything you need for CSV, Excel (.xlsx), Parquet, JSON, and Feather files out of the box.

**Optional extras:**

```bash
pip install aetherml[api]       # FastAPI REST endpoints
pip install aetherml[cli]       # CLI commands
pip install aetherml[explain]   # SHAP explanations
pip install aetherml[all]       # everything
```

---

## What It Does

AetherML runs a complete ML pipeline through 11 cooperating agents:

1. **Upload** — Load your dataset (CSV, Excel, Parquet, JSON, Feather)
2. **ETL** — Clean nulls, cast types, encode categoricals
3. **Validation** — Check for empty data, zero columns, duplicates
4. **EDA** — Statistical summaries, distributions, correlations
5. **Target Detection** — Automatically identify the prediction target and task type
6. **Feature Engineering** — Encode, scale, handle outliers, select features
7. **Model Selection** — Evaluate candidates and pick the best model
8. **Evaluation** — Task-appropriate metrics (accuracy/F1 for classification, RMSE/R2 for regression)
9. **Explainability** — SHAP-based feature importance
10. **Reporting** — Markdown or HTML report
11. **Storage** — Save artifacts

Each stage is independently callable. Run the whole thing with `ml.run()`, or step through individually.

---

## Links

- [API Reference](api.md) — Every public method documented
- [Guides](guides/incremental.md) — Step-by-step tutorials
- [Limitations](limitations.md) — What AetherML does *not* do (honest list)
- [GitHub](https://github.com/kartik00052/AetherML) — Source code
- [PyPI](https://pypi.org/project/aetherml/) — Install package
