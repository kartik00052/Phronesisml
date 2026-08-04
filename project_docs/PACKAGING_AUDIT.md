# PhronesisML — Packaging & uv Migration Audit

> **Purpose:** Step 1 of the v0.3.0 packaging/uv-migration checklist — audit the current packaging, dependency, and tooling layout so the migration steps that follow are evidence-driven.
> **Date:** 2026-08-05
> **Audited state:** working tree on top of commit `b75818c` (v0.3.0 work in progress; `uv.lock` untracked).
> **Status:** COMPLETE — audit findings recorded; remediation plan locked.

---

## 1. Build backend & metadata

| Area | Current state | Verdict |
|---|---|---|
| Build backend | `hatchling` (`[build-system] requires = ["hatchling"]`) | OK — modern PEP 517 backend, no `setup.py`/`setup.cfg`/`MANIFEST.in` present |
| Metadata | PEP 621 `[project]` block (`name`, `version`, `description`, `readme`, `license`, `authors`, `keywords`, `classifiers`, `dependencies`) | OK |
| Version | Static `0.3.0` in both `pyproject.toml` and `phronesisml/__init__.py` | **RISK** — duplicated source of truth; drift-prone. Consider single-source (hatchling `dynamic` version from `__init__.py`) |
| License | `license = "MIT"` + OSI classifier | OK |
| Requires-Python | `>=3.11,<3.14` + classifiers for 3.11/3.12/3.13 | OK |
| Type hints | `phronesisml/py.typed` present | OK |
| Entry point | `[project.scripts] phronesisml = "phronesisml.interfaces.cli.app:app"` | OK — matches actual CLI app object |

## 2. Dependencies

| Area | Current state | Verdict |
|---|---|---|
| Core deps | `pydantic`, `langgraph`, `pandas`, `polars`, `scikit-learn`, `numpy`, `shap`, `pyarrow`, `joblib` — bounded ranges (`pandas>=2.0,<3.0` etc.) | OK |
| Extras | `cli`, `spark`, `mlflow`, `excel`, `dev`, `all` | **GAP** — no `docs` extra; `dev` missing `pytest-xdist`, `build`, `twine`, `coverage`; `all` does not include `docs` |
| `requirements.txt` | Stale pin list (pandas 2.3.1, polars 1.42.1, sklearn 1.6.1, numpy 2.2.6, pydantic, langgraph, pytest, mypy …) at repo root | **RISK** — drift vs `pyproject.toml`; excluded from sdist; ambiguous role (lockfile? freeze? install hint?). Must be reconciled or removed |
| `uv.lock` | Exists at repo root, untracked, lockfile v1 revision 3, resolved only for `sys_platform == 'win32'` | **RISK** — untracked (not reproducible in CI), Windows-only resolution |
| `[tool.uv] environments` | Restricted to `sys_platform == 'win32'` | **GAP** — blocks cross-platform `uv sync`; blocks uv in Linux CI |

## 3. Tooling & scripts

| Tool | Config | Verdict |
|---|---|---|
| Ruff | `[tool.ruff]` target py311, line-length 100, select E/F/I/N/UP/B/SIM/ANN | OK |
| mypy | `[tool.mypy]` strict, python_version 3.13 | **GAP** — `python_version = "3.13"` while project supports 3.11+; `requirements.txt` lacks mypy pin alignment |
| pytest | `[tool.pytest.ini_options]` asyncio_mode auto, testpaths tests | OK |
| Makefile | Targets `lint/format/typecheck/test/check/build/clean` using `python -m …` | **GAP** — no uv targets; `clean` uses `find` (POSIX-only, fails on Windows) |
| pre-commit | `.pre-commit-config.yaml` (ruff --fix, ruff-format, generic hooks, `check-added-large-files --maxkb=10000`) | OK |

## 4. CI / release workflows

| Workflow | Current state | Verdict |
|---|---|---|
| `.github/workflows/ci.yml` | auto-format (pip, py3.13), lint (pip, py3.13), test matrix 3.11/3.12/3.13 (pip `-e ".[dev]"`), typecheck (pip, py3.13), pypi-publish (`pip install build` + `python -m build` + gh-action-pypi-publish, tags only) | **GAP** — pip-only; no uv leg; no `twine check`; no build artifact smoke |
| `.github/workflows/docs.yml` | pip `-e ".[dev]"` + mkdocs-material + mkdocstrings, strict build, gh-deploy | **GAP** — pip-only; hard-coded mkdocs deps instead of a `docs` extra |

## 5. Findings summary

### Findings (numbered for the migration steps)

1. **F1 — No `docs` extra.** mkdocs deps are installed ad hoc in CI (`pip install -e ".[dev]" mkdocs-material "mkdocstrings[python]"`). Should become `[docs]` extra and be referenced by `docs.yml` and `all`.
2. **F2 — `dev` extra incomplete.** Missing `pytest-xdist`, `build`, `twine`, `coverage` (the project's stated core dev tools). README still documents `dev` as "pytest, ruff, mypy".
3. **F3 — `all` extra excludes `docs`.** `all = ["phronesisml[cli,spark,mlflow,excel]"]`. Should include `docs` (docs are non-runtime and appropriate to exclude from `all`; decision: include for single-command completeness).
4. **F4 — Duplicated version string.** `pyproject.toml` and `__init__.py` both hard-code `0.3.0`. Switch to hatchling dynamic version from `phronesisml/__init__.py`.
5. **F5 — Stale `requirements.txt`.** Drifts from `pyproject.toml`; ambiguous purpose. Reconcile: regenerate as a pip-compatible freeze *or* delete and rely on `pyproject.toml` + `uv.lock`. Decision: keep a regenerated `requirements.txt` (pip users) and document that `uv.lock` is canonical for uv.
6. **F6 — `uv.lock` untracked + Windows-only.** Track it and widen `[tool.uv] environments` to the full supported platform set so CI (Linux) and macOS/WSL users can `uv sync`.
7. **F7 — CI is pip-only.** No uv leg, no cross-platform uv lock check, no `twine check`. Add a uv job and a build/verify job.
8. **F8 — mypy `python_version` mismatch.** `3.13` hard-coded vs `requires-python >=3.11`. Align to `3.11` (floor) or drop the pin.
9. **F9 — Makefile POSIX-only `clean` + no uv targets.** Make `clean` cross-platform and add `sync/install/build-uv` targets documenting the dual workflow.
10. **F10 — sdist excludes `docs/`, `project_docs/`, `.github/`, `mkdocs.yml`, `requirements.txt`.** Intentional (SDK distribution only); document the intent in `pyproject.toml` via comment.

## 6. Remediation plan (maps to checklist steps 2–12)

| # | Action | Steps |
|---|---|---|
| 1 | Add `docs` extra; expand `dev` (+`pytest-xdist`, `build`, `twine`, `coverage`); `all` includes `docs` | 2–4 |
| 2 | Single-source version via hatchling dynamic version | 2 |
| 3 | Regenerate `requirements.txt` from `pyproject.toml`; keep `uv.lock` canonical | 2, 5 |
| 4 | Track `uv.lock`; widen `[tool.uv] environments` | 5 |
| 5 | Makefile: uv targets + cross-platform `clean` | 6 |
| 6 | CI: dual pip+uv matrix, `twine check`, build smoke | 7–8 |
| 7 | README/docs: document both `pip install` and `uv` workflows | 9–10 |
| 8 | Deliverables: `UV_MIGRATION_REPORT.md`, `DEPENDENCY_MATRIX.md`, `INSTALLATION_VALIDATION.md`, `BUILD_VALIDATION.md`, `CI_VALIDATION.md`, updated `project_state.json` + `CHANGELOG.md` | 10–12 |
