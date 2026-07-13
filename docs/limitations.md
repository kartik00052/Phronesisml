# Limitations

AetherML is honest about what it does and does not support. This page lists the current known limitations — none of these are hidden or softened.

## Current Limitations

| Area | Limitation | Details |
|---|---|---|
| **PDF Reports** | Not supported | `generate_report(format="pdf")` raises `NotImplementedError`. Only Markdown and HTML formats work. |
| **Clustering** | Not supported | The pipeline is designed for **supervised learning** only (classification and regression). Unsupervised tasks — clustering, anomaly detection, dimensionality reduction — are not implemented. |
| **Time-series** | Not supported | No special handling for temporal features, forecasting, seasonal decomposition, or time-based train/test splits. |
| **Plugin system** | Not implemented | The `plugins/` directory and entry-points-based discovery mechanism are planned but not built. |
| **Storage backends** | Local only | Only local filesystem storage is implemented. S3, GCS, and Azure Blob backends are planned. |
| **Job store** | In-memory only | FastAPI background jobs use an in-memory dictionary. Jobs are lost on server restart. A database-backed store is planned. |
| **Legacy Excel (.xls)** | Requires manual install | `.xls` files (pre-2007 Excel) require `pip install xlrd`. The base install only supports `.xlsx` via `openpyxl`. |
| **GPU acceleration** | Not supported | All training runs on CPU via scikit-learn. No GPU-accelerated model training (e.g., XGBoost GPU, PyTorch). |
| **Custom models** | Not supported | Model candidates are hardcoded in the selection agent. You cannot add custom model classes without modifying the source code. |
| **Streaming data** | Not supported | The pipeline requires a complete file on disk. No support for streaming, incremental, or online learning. |
| **Large-than-memory (non-Spark)** | Limited | The pandas engine loads the entire dataset into memory. For datasets larger than RAM, use the Spark engine (`pip install aetherml[spark]`). The Polars engine handles memory more efficiently but is not truly distributed. |

## What AetherML *Is* vs. *Is Not*

| AetherML is | AetherML is not |
|---|---|
| An ML pipeline **SDK** | A full MLOps platform |
| A transparent, inspectable pipeline | A black-box AutoML tool |
| Good for tabular supervised learning | A solution for images, text, or time-series |
| Designed for **exploration and prototyping** | A production model serving system |
| A developer tool with a clean Python API | A no-code/low-code platform |

## Future Plans

These are planned but not yet implemented:

- [ ] PDF report generation
- [ ] Clustering and unsupervised learning stages
- [ ] Time-series forecasting support
- [ ] Plugin system for custom agents
- [ ] S3/GCS/Azure Blob storage backends
- [ ] Database-backed job store for the REST API
- [ ] Online/streaming learning mode
