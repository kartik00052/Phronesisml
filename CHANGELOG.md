# Changelog

All notable changes to PhronesisML will be documented in this file.

> **Note:** This project was formerly known as **AetherML** and published to PyPI as
> [`aetherml`](https://pypi.org/project/aetherml/). The `aetherml` package on PyPI is
> now **deprecated** — no new versions will be published there. Install the new package
> with `pip install phronesisml`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-13

### Changed (Breaking)

- **Project renamed from AetherML to PhronesisML** — The package, CLI, Docker image,
  and all public-facing names have been updated.
  - **Package:** `pip install aetherml` → `pip install phronesisml`
  - **Import:** `from aetherml import AetherML` → `from phronesisml import Phronesis`
  - **CLI command:** `aetherml run` → `phronesisml run`
  - **Docker image:** `ghcr.io/kartik00052/phronesisml`
  - **GitHub repo:** `github.com/kartik00052/PhronesisML`
- **Class renames:**
  - `AetherML` → `Phronesis`
  - `AetherMLConfig` → `PhronesisConfig`
  - `AetherMLError` → `PhronesisError`
- **PyPI deprecation:** The `aetherml` package on PyPI is deprecated. New versions will
  only be published as `phronesisml`. Existing `aetherml` installs are unaffected but
  will not receive further updates.

---

The entries below document the project's history under its former name, **AetherML**.

## [0.1.3] - 2026-07-13 *(as AetherML)*

### Added

- **`py.typed` marker** (PEP 561) — Downstream users get proper type-checking support from mypy/pyright.
- **Dependabot config** — Automated weekly dependency-update PRs for pip and GitHub Actions.
- **Real CI/PyPI badges** in README — Dynamic shields linked to PyPI, GitHub Actions, and license.
- **Installation matrix** in README — Shows which extras enable which features.

### Changed

- **Version bump to 0.1.3** — Fresh publish to validate Trusted Publisher pipeline end-to-end.

## [0.1.2] - 2026-07-13 *(as AetherML)*

### Added

- **PyPI Trusted Publishing** — CI now publishes to PyPI automatically on `v*` tags via GitHub OIDC (no API tokens stored in secrets).
- **PyPI CI publish job** — `pypi-publish` in `ci.yml` builds the wheel and pushes to PyPI using `pypa/gh-action-pypi-publish`.

### Changed

- **`openpyxl` and `pyarrow` are now core dependencies** — Excel (.xlsx), Parquet, and Feather files work out of the box with `pip install aetherml`. No manual extra installs needed.
- **README installation section** rewritten with format support table, extras matrix, and clearer quick-start guidance.
- **Import error messages** in `pandas_engine.py`, `shap_explainer.py`, and `file_loader.py` updated to reference `pip install aetherml[explain]` instead of raw pip package names.

### Removed

- **Stale manual extras** — Removed separate `[excel]` and `[parquet]` extras (now core). Cleaned up any leftover `[excel]`/`[parquet]` references from v0.1.0.

## [0.1.0] - 2026-07-12 *(as AetherML)*

### Added

- **AetherML class** — High-level SDK facade (`from aetherml import AetherML`) that wraps the full LangGraph pipeline behind method-chained calls (`ml.run()`, `ml.report()`, `ml.train()`). Every method returns typed result objects (`DatasetSummary`, `ValidationReport`, `ModelInfo`, etc.).
- **Simple API** — Zero-friction one-liner functions (`analyze()`, `train()`, `clean()`, `validate()`, `detect_target()`, `engineer()`, `select_model()`, `explain()`, `report()`) with `async` variants for FastAPI and Jupyter async contexts. Each returns a frozen dataclass with documented fields.
- **model_type parameter** — Pass `model_type="random_forest"` (or any supported model name) to `AetherML.train()`, `select_model()`, `train()`, or `train_async()` to skip model selection and train a specific model directly.
- **Incremental execution** — Call individual stages in any order; previously-executed stages are deduplicated and not re-run.
- **Async loop guard** — `_ensure_sync()` raises `RuntimeError` with a clear message if called from inside a running event loop (FastAPI, Jupyter async), preventing silent hangs.
- **Jupyter support** — `_repr_html_()` on the `AetherML` class renders a rich summary widget in notebooks.
- **Degenerate feature handling** — `FeatureEngineeringAgent` now gracefully handles zero-variance, all-null, and single-value columns without crashing, controlled by `FeatureSelectionConfig` (`variance_threshold`, `correlation_threshold`, `min_features`).
- **Structured exceptions** — `AetherMLError` hierarchy (`DataValidationError`, `EngineSelectionError`, `WorkflowError`, `ConfigurationError`) with structured fields for programmatic error handling.
- **FastAPI interface** — REST endpoints with multipart file upload, background job execution, job status polling, and OpenAPI docs (`pip install aetherml[api]`).
- **CLI interface** — Typer-based CLI (`aetherml run`, `aetherml info`) as a thin wrapper around the SDK (`pip install aetherml[cli]`).
- **PySpark engine** — Optional PySpark data engine for distributed/large-scale datasets (`pip install aetherml[spark]`).
- **SHAP explainability** — Optional SHAP-based feature importance and model explanation (`pip install aetherml[explain]`).
- **XGBoost support** — Optional XGBoost model family in the model selection candidate pool (`pip install aetherml[boost]`).
- **HTML report generation** — `AetherML.generate_report(format="html")` produces a self-contained HTML report.
- **CI/CD pipeline** — GitHub Actions workflow with lint (ruff), typecheck (mypy), tests (pytest across Python 3.11/3.12/3.13), API tests, CLI tests, explainability tests, Docker build, and GHCR image publishing on tagged releases.
- **Docker image** — Multi-stage Dockerfile producing a minimal production image, published to `ghcr.io/kartik00052/aetherml`.
- **Core dependencies required by default** — pandas, polars, numpy, scikit-learn, pydantic, langgraph, and joblib are always installed. Optional extras: `[api]`, `[cli]`, `[spark]`, `[explain]`, `[boost]`, `[mlflow]`.
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
