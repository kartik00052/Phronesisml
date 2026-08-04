# PhronesisML — Testing

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Operational testing guide. Binding rules: `AI_QUALITY_GATE.md` §5 (Testing Rules) and §9 (Quality Gate).

## 1. Test layout

| Location | Purpose |
|---|---|
| `tests/test_regressions.py` | BUG-xx / ISSUE-xx regression tests (currently 17) |
| `tests/test_data_io.py` … `test_target_analysis.py` | Engine-light data/ML module suites (this task's buckets) |
| `tests/test_preflight.py`, `tests/test_explainability.py` | Pre-flight + SHAP explainer suites |
| `tests/test_phronesis.py` | End-to-end integration scenarios |
| `tests/test_explanation_summary.py`, `test_artifact_storage.py`, `test_report_io.py` | SHAP summary / storage / report-IO helpers |

## 2. Rules

1. **Regression test first** for every defect fix — must fail on pre-fix code, pass post-fix.
2. **Test the path that broke** — assert the original failure mode, not internal call counts.
3. **Behavioral assertions** — frame equality, metric sets, job status — not implementation details.
4. **Deterministic fixtures** — synthetic data with fixed RNG seeds; `tmp_path` for file output; never write into the repo root.
5. **CLI tests** cover the Typer surface end-to-end (as delegated through the SDK).
6. **No new meaningful warnings** — suppress only expected third-party deprecations.

## 3. Determinism testing

Same dataset + config + seed must produce identical metrics, best model, reports, artifacts.
Baseline pattern in the repo: `SAMPLE_ROWS = 1000`, RNG seed `42`. New determinism coverage lives in `tests/test_determinism.py` (see Tranche 4).

## 4. Quality gate (mandatory before completion)

| Step | Command | Requirement |
|---|---|---|
| Lint | `ruff check .` | Zero errors |
| Format | `ruff format --check .` | Zero files would be reformatted |
| Types | `mypy phronesisml/ --ignore-missing-imports` | Clean (0 errors in 101 files) |
| Tests | `pytest -q` | Full suite passes, incl. `tests/test_regressions.py` |
| State file | §12 of gate | `project_state.json` regenerated |
| Docs | gate §4 | No doc/implementation contradiction introduced |

Targets: `make lint`, `make format`, `make typecheck`, `make test`, `make check`.

## 5. Current baseline

Last full gate (2026-08-05, v0.3.0 packaging/uv-migration): **305 passed, 0 failed**; ruff clean; ruff-format clean (121 files); mypy clean (0 errors, 101 files); `uv lock --check` consistent; `twine check dist/*` passed; `mkdocs build --strict` passed.

## 6. Integration scope to verify before release

SDK · Simple API · CLI · artifacts · reports · packaging (wheel + sdist) · optional extras. Anything that cannot be verified in the current environment (Python 3.13 wheel, Spark/MLflow live) must be recorded as `NOT VERIFIED` in `project_state.json` — never asserted.
