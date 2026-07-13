# Changelog

All notable changes to AetherML will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-12

### Added

- **AetherML class** — High-level SDK facade (`from aetherml import AetherML`) that wraps the full LangGraph pipeline behind method-chained calls (`ml.run()`, `ml.report()`, `ml.train()`). Every method returns typed result objects (`DatasetSummary`, `ValidationReport`, `ModelInfo`, etc.).
- **Simple API** — Zero-friction one-liner functions (`analyze()`, `train()`, `clean()`, `validate()`, `detect_target()`, `engineer()`, `select_model()`, `explain()`, `report()`) with `async` variants for FastAPI and Jupyter async contexts. Each returns a frozen dataclass with documented fields.
- **model_type parameter** — Pass `model_type="random_forest"` (or any supported model name) to `AetherML.train()`, `select_model()`, `train()`, or `train_async()` to skip model selection and train a specific model directly.
- **Incremental execution** — Call individual stages in any order; previously-executed stages are deduplicated and not re-run.
- **Async loop guard** — `_ensure_sync()` raises `RuntimeError` with a clear message if called from inside a running event loop (FastAPI, Jupyter async), preventing silent hangs.
- **Jupyter support** — `_repr_html_()` on the `AetherML` class renders a rich summary widget in notebooks.
- **Degenerate feature handling** — `FeatureEngineeringAgent` now gracefully handles zero-variance, all-null, and single-value columns without crashing, controlled by `FeatureSelectionConfig` (`variance_threshold`, `correlation_threshold`, `min_features`).
- **Structured exceptions** — `AetherMLError` hierarchy (`DataValidationError`, `EngineSelectionError`, `WorkflowError`, `ConfigurationError`) with structured fields for programmatic error handling.
- **FastAPI interface** — REST endpoints with multipart file upload, background job execution, job status polling, and OpenAPI docs (`pip install -e ".[api]"`).
- **CLI interface** — Typer-based CLI (`aetherml run`, `aetherml info`) as a thin wrapper around the SDK (`pip install -e ".[cli]"`).
- **PySpark engine** — Optional PySpark data engine for distributed/large-scale datasets (`pip install -e ".[spark]"`).
- **SHAP explainability** — Optional SHAP-based feature importance and model explanation (`pip install -e ".[explain]"`).
- **XGBoost support** — Optional XGBoost model family in the model selection candidate pool (`pip install -e ".[boost]"`).
- **HTML report generation** — `AetherML.generate_report(format="html")` produces a self-contained HTML report.
- **CI/CD pipeline** — GitHub Actions workflow with lint (ruff), typecheck (mypy), tests (pytest across Python 3.11/3.12/3.13), API tests, CLI tests, explainability tests, Docker build, and GHCR image publishing on tagged releases.
- **Docker image** — Multi-stage Dockerfile producing a minimal production image, published to `ghcr.io/kartik00052/aetherml`.
- **Core dependencies required by default** — pandas, polars, numpy, scikit-learn, pydantic, langgraph, and joblib are always installed. Optional extras: `[parquet]` (pyarrow), `[excel]` (openpyxl), `[api]`, `[cli]`, `[spark]`, `[explain]`, `[boost]`, `[mlflow]`.
- **`python-multipart` in API extras** — Required by FastAPI for file upload parsing; added to the `[api]` extra.

### Changed

- **SDK-first architecture** — CLI and FastAPI are now thin clients that delegate entirely to the SDK; no business logic lives outside the SDK.
- **WorkflowState** — Expanded to 11 typed fields covering every pipeline stage; agents read/write through this shared state.
- **`__init__.py` exports** — All public API symbols (Simple API functions, OOP API classes, Advanced API types) are exported from the top-level `aetherml` package.
- **Mypy strictness** — Enabled `strict = true` with `python_version = "3.13"` and per-module overrides for FastAPI/Typer decorator types.

### Fixed

- **pyproject.toml `[project.urls]` placement** — Moved after `dependencies` to resolve build-system warnings.
- **GHCR image name casing** — Lowercased to `kartik00052/aetherml` to comply with GitHub Container Registry's all-lowercase requirement.
- **CI test isolation** — `conftest.py` uses `collect_ignore` to skip `test_api.py` and `test_cli_app.py` when FastAPI/Typer are not installed.

### Known Limitations

- **PDF reports** — `generate_report(format="pdf")` raises `NotImplementedError`. Only Markdown and HTML are supported.
- **Clustering** — The pipeline is designed for supervised learning (classification/regression). Unsupervised tasks (clustering, dimensionality reduction) are not yet supported.
- **Time-series** — No special handling for temporal features, forecasting, or time-based train/test splits.
- **Plugin system** — The `plugins/` directory and entry-points-based discovery mechanism are planned but not yet implemented.
- **Additional storage backends** — Only local filesystem storage is implemented. S3/GCS/Azure Blob backends are planned.
