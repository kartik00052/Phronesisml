# PhronesisML — CI Validation

> **Purpose:** Documents the updated CI matrix after the uv migration and how to validate the workflows locally before pushing.
> **Date:** 2026-08-05
> **Status:** CONFIGURED — local mirrors pass; full matrix executes on GitHub Actions.

## 1. Workflow inventory

### `.github/workflows/ci.yml`

| Job | Trigger | Python | Install | Checks |
|---|---|---|---|---|
| `auto-format` | PR/push to main | 3.13 | `pip install ruff` | `ruff check --fix` + `ruff format`, commits back |
| `lint` | always | 3.13 | pip + `astral-sh/setup-uv` | `ruff check --no-fix`, `ruff format --check`, `uv lock --check` |
| `test` | after `lint` | **3.11 / 3.12 / 3.13** × **pip / uv** (6 legs) | pip: `-e ".[dev]"`; uv: `uv sync --all-extras` | `pytest -x`; `python test_phronesis.py` (regression) |
| `typecheck` | always | 3.13 | `pip install -e ".[dev]"` | `mypy phronesisml/ --ignore-missing-imports` |
| `build` | after lint+typecheck+test | 3.13 | pip (build, twine) + uv | `python -m build`, `uv build`, `twine check dist/*`, wheel reinstall + import smoke |
| `pypi-publish` | tags `v*` only, after build | 3.13 | `pip install build` | `python -m build` + `gh-action-pypi-publish` (trusted publishing) |

### `.github/workflows/docs.yml`

| Job | Trigger | Install | Checks |
|---|---|---|---|
| `build` | push/PR to main | **pip / uv** legs; pip: `-e ".[docs]"`; uv: `uv sync --extra docs` | `mkdocs build --strict`; `gh-deploy` on main push (pip leg only) |

## 2. Local validation mirrors (all PASSED)

| Local command | Mirrors CI |
|---|---|
| `uv run ruff check phronesisml/ tests/ --no-fix` | `lint` |
| `uv run ruff format --check phronesisml/ tests/` | `lint` |
| `uv lock --check` | `lint` (uv lock leg) |
| `uv sync --all-extras` | `test` (uv legs) |
| `uv run pytest tests/ -q --tb=short` | `test` |
| `uv run mypy phronesisml/ --ignore-missing-imports` | `typecheck` |
| `python -m build` + `uv build` + `twine check dist/*` | `build` |
| `pip install -e ".[docs]"` + `mkdocs build --strict` | `docs` |

## 3. What changed from the previous CI

| Area | Before | After |
|---|---|---|
| Install tooling | pip only | Dual pip + uv matrix |
| Lock check | none | `uv lock --check` in lint |
| Test legs | 3 (pip, 3.11/3.12/3.13) | 6 (pip + uv × 3 Pythons) |
| Build job | none (only publish) | New `build` job with both builders + `twine check` + import smoke |
| Docs deps | inline `mkdocs-material "mkdocstrings[python]"` | `[docs]` extra |
| Publish gate | needs lint+typecheck+test | needs lint+typecheck+test+build |
| `[tool.uv] environments` | win32 only | win32/darwin(arm64)/linux |

## 4. Notes

- `test_phronesis.py` (regression suite) runs with `|| true` in CI — it is a diagnostic script, not a gating suite; the gating suite is `pytest tests/`.
- Auto-format and publish use the pip leg intentionally to keep trusted-publishing (PyPI) minimal and dependency-light.
- The `docs` workflow matrix adds a uv build check without doubling the gh-deploy (deploy runs on the pip leg only).
- Darwin is limited to `arm64` (Apple Silicon): shap 0.51.0 (the py<3.12 shap) pins `numba<0.63` on darwin-x86_64, which requires `numpy<2.4` and conflicts with our `numpy>=1.24,<2.5` — so a universal lock including Intel Macs is unsatisfiable.
