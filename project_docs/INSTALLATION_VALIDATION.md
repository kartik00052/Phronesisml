# PhronesisML — Installation Validation

> **Purpose:** Evidence that the dual pip + uv installation paths install `phronesisml==0.3.0` with the correct extras, on the supported Python range.
> **Date:** 2026-08-05
> **Method:** All commands run in the project's Windows venv (Python 3.12.13, uv 0.11.21). CI runs the same matrix on Linux in `.github/workflows/ci.yml`.
> **Status:** PASSED.

## 1. Environment under test

| Item | Value |
|---|---|
| OS | Windows (win32) |
| Python | 3.12.13 (`.python-version`, uv leg); **3.11.9 (fresh pip-leg venv)** |
| uv | 0.11.21 |
| pip | 24.0 (fresh venv) / bundled with uv venv |
| Project version | 0.3.0 (dynamic, from `phronesisml/__init__.py`) |

## 2. Pip path

| Command | Result |
|---|---|
| `pip install -e ".[dev,cli,excel,docs]"` (fresh py3.11 venv) | Installed; `phronesisml==0.3.0` importable |
| `python -c "import phronesisml; print(phronesisml.__version__)"` | `0.3.0` |
| `python -c "import importlib.metadata; print(importlib.metadata.version('phronesisml'))"` | `0.3.0` |
| `phronesisml --help` | Renders (entry point `phronesisml = phronesisml.interfaces.cli.app:app`) |
| `phronesisml train data/iris.csv` | `Trained: LogisticRegression (score=1.0000)` — identical to the uv leg |
| `pip install --dry-run "…whl[spark]"` | `Would install py4j-0.10.9.9 pyspark-3.5.9` |
| `pip install --dry-run "…whl[all]"` | Resolves mlflow 2.22.5 + pyspark 3.5.9 + full graphs, **no conflicts** |

## 3. uv path

| Command | Result |
|---|---|
| `uv lock` | Resolved 175 packages; `phronesisml -> (dynamic) 0.3.0` |
| `uv lock --check` | Resolved 175 packages in 75ms — lock consistent |
| `uv sync --extra dev --extra cli --extra excel --extra docs` | Checked 122 packages — in sync |
| `uv sync --all-extras` | Installed `pyspark 3.5.9`, `mlflow 2.22.5` from lock; `uv sync --all-extras --check` → "Would make no changes" |
| `uv pip install -e ".[dev,cli]"` | Installed dev tools incl. `pytest-xdist 3.8.0`, `coverage 7.15.3`, `build 1.5.0`, `twine 6.2.0`; restored `rich 13.9.4` per lock |
| `uv run python -c "import phronesisml; print(phronesisml.__version__)"` | `0.3.0` |

## 4. Lock cross-platform coverage

`[tool.uv] environments` now lists `win32`, `darwin` (arm64 only), and `linux`. `uv.lock` resolves markers for all three platforms (verified: `rich`/`twine` markers include `sys_platform == 'darwin' or sys_platform == 'linux' or sys_platform == 'win32'`). Darwin is restricted to `platform_machine == 'arm64'`: shap 0.51.0 (py<3.12) pins `numba<0.63` on darwin-x86_64, which requires `numpy<2.4` and conflicts with the `numpy>=1.24,<2.5` range — so Intel-Mac universal resolution is unsatisfiable. The lock now carries a single `numba 0.66.0` and splits `shap` 0.51.0 (py<3.12) / 0.52.0 (py≥3.12) with resolution markers.

## 5. Extra group verification

| Extra | Installed markers verified |
|---|---|
| `cli` | `typer 0.27.1`, `rich 13.9.4` |
| `excel` | `openpyxl 3.1.5` |
| `docs` | `mkdocs 1.6.1`, `mkdocs-material 9.7.7`, `mkdocstrings 0.30.1` |
| `dev` | `pytest 8.4.2`, `pytest-asyncio 0.26.0`, `pytest-cov 5.0.0`, `pytest-xdist 3.8.0`, `coverage 7.15.3`, `ruff 0.16.1`, `mypy 1.20.2`, `pre-commit 4.6.1`, `build 1.5.0`, `twine 6.2.0` |
| `spark` | `pyspark 3.5.9` (installed via `uv sync --all-extras`) |
| `mlflow` | `mlflow 2.22.5` (installed via `uv sync --all-extras`) |

## 6. Known constraint

`twine>=7` requires `rich>=14.3.3`, which conflicts with the `cli` pin `rich>=13,<14`. The lock resolves the compatible pair `twine 6.2.0` + `rich 13.9.4`. Re-raising the `twine` bound requires raising the `rich` bound in the same change (see `DEPENDENCY_MATRIX.md` §6.2).
