# PhronesisML — Dependency Matrix

> **Purpose:** Single source of truth mapping every PhronesisML dependency to its owner (core vs extra), the declared range in `pyproject.toml`, and the version resolved in `uv.lock` at release time.
> **Date:** 2026-08-05
> **Scope:** `phronesisml==0.3.0`, Python `>=3.11,<3.14`.
> **Status:** CURRENT — reflects the working tree at v0.3.0 release.

## 1. Core runtime dependencies

Installed with `pip install phronesisml` (or any `[extra]` install; extras are additive).

| Package | `pyproject.toml` range | `uv.lock` resolved | Purpose |
|---|---|---|---|
| `pydantic` | `>=2.0,<3.0` | 2.13.4 | `PhronesisConfig`, `SamplingConfig`, workflow state schemas |
| `langgraph` | `>=0.2,<1.0` | 0.6.11 | Multi-agent workflow orchestration graph |
| `pandas` | `>=2.0,<3.0` | 2.3.3 | Primary data engine (transform, EDA, evaluation) |
| `polars` | `>=1.0,<2.0` | 1.43.2 | Optional lazy/vectorized engine |
| `scikit-learn` | `>=1.3,<2.0` | 1.9.0 | Model training, clustering, anomaly detection, metrics, encoders |
| `numpy` | `>=1.24,<2.5` | 2.4.6 | Array math shared by all ML components |
| `shap` | `>=0.51,<0.53` | 0.51.0 (py<3.12) / 0.52.0 (py≥3.12) | Model explainability (SHAP explainers); split by Python version because 0.52.0 requires py≥3.12 |
| `pyarrow` | `>=15.0` | 19.0.1 | Parquet/Arrow IO, polars interop |
| `joblib` | `>=1.3,<2.0` | 1.5.3 | Model persistence (`save()`/`restore()`) |

## 2. Optional extras

### `[cli]` — `pip install phronesisml[cli]`
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `typer` | `>=0.12,<1.0` | 0.27.1 | CLI command framework |
| `rich` | `>=13.0,<14.0` | 13.9.4 | CLI tables/panels/progress |

> Note: `rich` is pinned `<14.0` because `twine>=7` requires `rich>=14`; the lock pins `twine 6.2.0` (see `[dev]`) so both coexist at `rich 13.9.4`.

### `[spark]` — `pip install phronesisml[spark]`
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `pyspark` | `>=3.5,<4.0` | not installed locally | Spark engine (optional heavy dep) |

### `[mlflow]` — `pip install phronesisml[mlflow]`
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `mlflow` | `>=2.10,<3.0` | not installed locally | Experiment tracking |

### `[excel]` — `pip install phronesisml[excel]`
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `openpyxl` | `>=3.1,<4.0` | 3.1.5 | `.xlsx` read/write |

### `[docs]` — `pip install phronesisml[docs]` *(new in v0.3.0)*
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `mkdocs` | `>=1.6,<2.0` | 1.6.1 | Documentation site builder |
| `mkdocs-material` | `>=9.5,<10.0` | 9.7.7 | Material theme |
| `mkdocstrings[python]` | `>=0.25,<1.0` | 0.30.1 | Docstring-to-docs rendering |

### `[dev]` — `pip install phronesisml[dev]` *(expanded in v0.3.0)*
| Package | Range | Resolved | Purpose |
|---|---|---|---|
| `pytest` | `>=8.0,<9.0` | 8.4.2 | Unit test runner |
| `pytest-asyncio` | `>=0.23,<1.0` | 0.26.0 | Async test support (`asyncio_mode = auto`) |
| `pytest-cov` | `>=5.0,<6.0` | 5.0.0 | Coverage plugin |
| `pytest-xdist` | `>=3.5,<4.0` | 3.8.0 | Parallel test execution (`-n auto`) |
| `coverage` | `>=7.0,<8.0` | 7.15.3 | Coverage measurement engine |
| `ruff` | `>=0.4,<1.0` | 0.16.1 | Linter + formatter |
| `mypy` | `>=1.10,<2.0` | 1.20.2 | Static type checking (strict) |
| `pre-commit` | `>=3.0,<5.0` | 4.6.1 | Pre-commit hook runner |
| `build` | `>=1.2,<2.0` | 1.5.0 | PEP 517 source/wheel builds |
| `twine` | `>=5.0,<7.0` | 6.2.0 | PyPI artifact upload/validation |

### `[all]` — `pip install phronesisml[all]`
Aggregates `[cli,spark,mlflow,excel,docs]` *(docs added in v0.3.0)*. Dev tooling is deliberately **not** part of `all` — it is a runtime superset, not a developer superset.

## 3. Test-only / workflow dependencies

| Package | Where declared | Purpose |
|---|---|---|
| `httpx` | `requirements.txt` (dev convenience) | HTTP client used in regression tests |

## 4. Historical / removed (v0.3.0)

| Package | Status | Note |
|---|---|---|
| `fastapi`, `uvicorn`, `python-multipart` | Removed | REST API decommissioned; see `rest_api_removal_report.md` |

## 5. Lock files

| File | Role | Status |
|---|---|---|
| `pyproject.toml` | Declarative ranges (canonical) | Tracked |
| `uv.lock` | Locked resolution for `uv sync` (cross-platform: win32/darwin-arm64/linux) | **Now tracked** |
| `requirements.txt` | Pip-compatible pin list for `pip install -r requirements.txt` | Regenerated, tracked |

## 6. Resolution invariants

1. Every `requirements.txt` pin is `>=` the range declared in `pyproject.toml` and `==` the version resolved in `uv.lock` for that package at release time.
2. `rich`/`twine` are the only constrained pair (F4/footnote above); the lock pins `twine 6.2.0`.
3. Optional packages (`pyspark`, `mlflow`) are resolved in the lock but not installed in the default local env; `health()` reports them as optional.
