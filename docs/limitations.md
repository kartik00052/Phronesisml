# Limitations

PhronesisML is honest about what it does and does not support. This page lists the current known limitations — none of these are hidden or softened.

---

## Current Limitations

| Area | Limitation | Details | Workaround |
|------|-----------|---------|------------|
| **PDF Reports** | Not supported | `generate_report(format="pdf")` raises `NotImplementedError`. Only Markdown and HTML formats work. | Export Markdown, convert with pandoc or a Markdown-to-PDF tool. |
| **Clustering** | Limited | Clustering is supported via `cluster()` but lacks advanced options (e.g., custom distance metrics, density-based clustering). Anomaly detection and dimensionality reduction are also supported. | Use scikit-learn directly for advanced unsupervised needs. |
| **Time-series** | Not supported | No special handling for temporal features, forecasting, seasonal decomposition, or time-based train/test splits. | Use dedicated time-series libraries (Prophet, statsmodels). |
| **Plugin system** | Not implemented | The `plugins/` directory and entry-points-based discovery mechanism are planned but not built. | Extend the SDK via subclassing or use the OOP API. |
| **Storage backends** | Local only | Only local filesystem storage is implemented. S3, GCS, and Azure Blob backends are planned. | Save artifacts locally, then upload manually. |
| **Legacy Excel (.xls)** | Requires manual install | `.xls` files (pre-2007 Excel) require `pip install xlrd`. The base install only supports `.xlsx` via `openpyxl`. | Convert to `.xlsx` or install xlrd. |
| **GPU acceleration** | Not supported | All training runs on CPU via scikit-learn. No GPU-accelerated model training (e.g., XGBoost GPU, PyTorch). | Use the trained model with a GPU-accelerated framework. |
| **Custom models** | Not supported | Model candidates are hardcoded in the selection agent. You cannot add custom model classes without modifying the source code. | Use `train(model_type=...)` to train a specific model. |
| **Streaming data** | Not supported | The pipeline requires a complete file on disk. No support for streaming, incremental, or online learning. | Collect data first, then run the pipeline. |
| **Larger-than-memory (non-Spark)** | Limited | The pandas engine loads the entire dataset into memory. For datasets larger than RAM, use the Spark engine (`pip install phronesisml[spark]`). The Polars engine handles memory more efficiently but is not truly distributed. | Use `engine="spark"` for large datasets. |
| **Multi-output** | Not supported | Only single-target prediction. Multi-output regression or multi-label classification is not implemented. | Train separate models for each output. |
| **Natural language** | Not supported | No NLP preprocessing, tokenization, or text-specific feature engineering. | Preprocess text externally, then feed to PhronesisML. |
| **Image data** | Not supported | No image loading, augmentation, or CNN-based models. | Extract features externally (e.g., with a pre-trained CNN), then feed to PhronesisML. |

---

## What PhronesisML *Is* vs. *Is Not*

| PhronesisML is | PhronesisML is not |
|---|---|
| An ML pipeline **SDK** | A full MLOps platform |
| A transparent, inspectable pipeline | A black-box AutoML tool |
| Good for tabular supervised learning | A solution for images, text, or time-series |
| Designed for **exploration and prototyping** | A production model serving system |
| A developer tool with a clean Python API | A no-code/low-code platform |
| Offline-first by design | A cloud-native platform |
| A starting point for ML projects | A replacement for domain expertise |

---

## Known Issues

### Performance

- **First-run overhead:** The first `run()` call compiles the LangGraph graph (~0.5s). Subsequent calls reuse the cached graph.
- **Polars auto-select threshold:** The 2 MB threshold for Polars selection is conservative. Some datasets between 1–2 MB may benefit from Polars.
- **SHAP on large datasets:** The `KernelExplainer` is slow on datasets with many features. The `max_samples=100` cap limits accuracy.

### Data Quality

- **Null handling in ETL:** The `"flag"` strategy creates boolean columns, which can significantly increase dimensionality on datasets with many nulls.
- **Categorical encoding:** Label encoding is used for all categoricals. This can mislead tree-based models if categories have no inherent order.
- **Outlier detection:** IQR-based detection (1.5x multiplier) may be too aggressive for some distributions.

### Model Selection

- **Limited candidate pool:** Only 3 models per task type. No XGBoost, LightGBM, or CatBoost.
- **No hyperparameter optimization beyond grid search:** The trainer uses `GridSearchCV` with limited parameter grids.
- **Re-ranking heuristics:** Small-dataset and high-dimensional boosts may not always improve results.

---

## Future Plans

These are planned but not yet implemented:

- [ ] PDF report generation
- [ ] Time-series forecasting support
- [ ] Plugin system for custom agents
- [ ] S3/GCS/Azure Blob storage backends
- [ ] Online/streaming learning mode
- [ ] XGBoost, LightGBM, CatBoost model candidates
- [ ] Bayesian hyperparameter optimization
- [ ] Custom model registration
- [ ] Multi-output prediction
- [ ] NLP preprocessing pipeline
- [ ] Image feature extraction pipeline
- [ ] WebSocket support for real-time training progress

---

## Contributing

If you encounter a limitation that blocks your use case, consider contributing:

1. **Open an issue** describing the limitation and your use case
2. **Submit a PR** with a proposed solution
3. **Join the discussion** on GitHub

See [CONTRIBUTING.md](https://github.com/kartik00052/PhronesisML/blob/main/CONTRIBUTING.md) for guidelines.
