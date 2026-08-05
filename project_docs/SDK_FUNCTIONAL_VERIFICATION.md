# SDK Functional Verification — v0.3.0 QA Pass

> **Version:** 0.3.0 (working tree, tag not yet created) · **Date:** 2026-08-05
> **Scope:** 12-phase QA audit for a first-time local-CSV user
> **Datasets:** `BankChurners.csv`, `heart.csv`, `diabetes_prediction_dataset.csv`

## 1. Executive Summary

PhronesisML v0.3.0 is **installable and largely functional** for a first-time
local-CSV user: fresh-install, import matrix, CLI, end-to-end pipeline, artifact
generation, SHAP routing, deterministic runs, and safe error handling all work.
Six defects were confirmed and documented as RCAs (NEW-09…NEW-14); the most
impactful is **NEW-09 — `predict()`/restore→predict crashes on string
categorical columns**, which breaks the core "train → save → deploy → predict"
story for the majority of real-world CSVs (any with text columns). All confirmed
defects are **unfixed** in this pass and pinned by 6 xfail regression tests.

**Verdict: NOT release-clean for v0.3.0 as-is.** The dataset support matrix works,
but NEW-09 blocks a realistic first-user workflow (predict on raw rows containing
strings) and NEW-10 breaks the default `compare` CLI path. Fix both before tagging.

## 2. Phase Matrix

| # | Phase | Result | Notes |
|---|-------|--------|-------|
| 1 | Fresh install | **PASS** | `uv build` → wheel 213333 B / sdist 330888 B; wheel + `[cli,excel]` install into fresh py3.11 venv; import matrix (24 names) OK; `phronesisml version` → 0.3.0; `pip install -e .` over wheel OK |
| 2 | SDK surface (18 checks/dataset) | **heart 20/20 PASS · bank 18/20 · diab 18/20** | Only failures: predict + restore→predict on string categoricals (**NEW-09**) |
| 3 | CLI | **PASS (with NEW-10)** | 12 commands; `compare` without `-m` crashes (**NEW-10**); `evaluate` missing (**NEW-12**) |
| 4 | End-to-end | **PASS** | heart→RF acc 1.0; bank→GradBoostReg r² 0.66 (score 0.6281); diab→GradBoostReg score 0.2345; `run(mode=fast)` skips explainability+storage |
| 5 | Artifacts | **PASS (with NEW-11)** | 18/18 files JSON-valid; no `report.json` (canonical = `pipeline.json`); `resource_estimation.json` placeholder (**NEW-11**) |
| 6 | SHAP routing | **PASS** | Tree→TreeExplainer (RF/GB), Linear→LinearExplainer (LogReg) verified E2E; Permutation/Kernel covered by 41 unit tests (SVM/KNN/LinearSVC) |
| 7 | Error handling | **PASS (2 UX notes)** | Friendly failures for missing/empty files (SDK + CLI); leaked pandas error on `predict(dict-of-scalars)` |
| 8 | Determinism | **PASS** | 3× balanced runs on heart → identical model/score/top-3 SHAP/prediction (`DEFAULT_RANDOM_STATE=42`) |
| 9 | Docs vs surface | **FAIL (drift)** | 10+ doc/surface contradictions — see §5 |
| 10 | Root-cause docs | **DONE** | NEW-09…NEW-14 written + indexed in `docs/root_cause/README.md` |
| 11 | Regression suite | **DONE** | `tests/test_regressions_v030.py` — 6 xfail (strict); full suite **312 passed, 6 xfailed** |
| 12 | This report | **DONE** | — |

## 3. Confirmed Defects (unfixed)

| ID | Severity | Symptom | Choke point | RCA |
|----|----------|---------|-------------|-----|
| NEW-09 | **High** | `predict()`/restore→predict: `ValueError: could not convert string to float` on any string categorical (bank `Existing Customer`, diab `Female`) | ETL `encoding_maps` never merged into FE recipe → empty `encoding_maps` → `astype(float)` on raw strings at `transform.py:116` | `docs/root_cause/NEW-09_*.md` |
| NEW-10 | Medium | CLI `compare <file>` (no `-m`) → `'NoneType' object is not iterable`, exit 1 | `app.py:403` `list(model) or None` with `model=None` | `docs/root_cause/NEW-10_*.md` |
| NEW-11 | Low | `resource_estimation.json` = `{"status":"unavailable","reason":"pre-flight resource estimation did not run"}` in every run | sampling node wired only in `__init__.py:298` (`run_pipeline`); `sdk.py:514` `build_graph` omits it | `docs/root_cause/NEW-11_*.md` |
| NEW-12 | Low | `phronesisml evaluate` → exit 2 "No such command" (SDK has `evaluate`) | CLI registry never received the command after NEW-01 | `docs/root_cause/NEW-12_*.md` |
| NEW-13 | Low | Detector prose "2–5 unique" vs code `range(3, 6)`; `n_unique==2` uses a different branch/signal | re-typed literal range (sibling of NEW-04) | `docs/root_cause/NEW-13_*.md` |
| NEW-14 | Medium | Docs claim phantom `evaluation_report.json`, "12 functions", 2–4 CLI commands, phantom params (`fill_value=`), phantom attributes (`DatasetProfile.numeric_columns`, `CleanResult.shape`, `EvaluationMetrics.get()`, `WorkflowState.target_confidence`) | docs not enforced against code | `docs/root_cause/NEW-14_*.md` |

**Not defects (verified as intended):**
- `explain()`/`compare()`/`predict()` before train **auto-train** (lazy full pipeline) — valid design; only `predict(dict)` leaks a raw pandas error (UX note).
- All-null column → ETL null-drop collapses to 0 rows → clean "zero rows (empty)" error (fails safely; message slightly misleading).
- Corrupted/ragged CSV and duplicate columns load permissively with NaNs (exit 0).
- Target misuse on bank/diab (numeric age-like column chosen as target, task `ambiguous` conf < 0.6) — documented heuristic limitation, not a detection bug.

## 4. Per-Dataset Results

| Dataset | Engine | Target | Task | Model | Score | Explain | Predict(raw) |
|---------|--------|--------|------|-------|-------|---------|--------------|
| heart.csv (1025) | pandas | target | ambiguous | RandomForestClassifier | acc 1.0 | TreeExplainer, 12 feats | **OK** (all-numeric) |
| BankChurners.csv (10k) | pandas | (age-like) | ambiguous | GradientBoostingRegressor | r² 0.66 (0.6281) | TreeExplainer | **FAIL** string→float |
| diabetes (100k) | polars | (age-like) | ambiguous | GradientBoostingRegressor | 0.2345 | TreeExplainer | **FAIL** string→float |

Engine routing threshold verified: <2 MB → pandas (heart/bank), 2 MB+ → polars (diab 100k). Restore round-trips: heart 18 artifacts, restore→predict matches.

## 5. Docs Drift (NEW-14) — quick reference

- `evaluation_report.json` claimed in `PROJECT_KNOWLEDGE_BASE.md:364,516`, `IMPLEMENTATION_ROADMAP.md:136,318,395`, `AUDIT_REPORT.md:44,141` — real artifact is `evaluation.json`/`pipeline.json`.
- CLI documented as 2–4 commands (`PUBLIC_API_AUDIT.md:62`, `API_Contracts.md:46-48`, `IMPLEMENTATION_ROADMAP.md:106`, entire `docs/guides/cli.md`) — real: 12.
- "12 functions" (`API_Contracts.md:14`, `IMPLEMENTATION_ROADMAP.md:82`) — real: 23.
- Phantom params/attrs in examples (see NEW-14) — all raise `TypeError`/`AttributeError` if executed.

## 6. Regression Suite

`tests/test_regressions_v030.py` — 6 tests, all `xfail(strict=True)`, each pinned to an RCA ID. Full suite: **312 passed, 6 xfailed** (baseline intact). On fix, remove the xfail markers and the tests must pass.

## 7. Recommendations before tagging v0.3.0

1. **Fix NEW-09** (High) — merge ETL `encoding_maps` into the FE recipe; unmark 2 tests. Without it, string-categorical predict is broken.
2. **Fix NEW-10** (trivial) — `app.py:403`: `list(model) if model else None`; unmark 1 test.
3. **Fix NEW-12** — add `evaluate` CLI command; unmark 1 test.
4. **Fix NEW-11** — wire `sampling_config`+`engine` into `sdk._run_stages`; unmark 1 test.
5. **Fix NEW-13** — unify 2–5 unique branch; unmark 1 test.
6. **Fix NEW-14** — correct the four doc/filename/count claims and add a doc-guard test.
7. Improve `predict(dict)` to normalize scalar dicts (friendly error instead of pandas `ValueError`).
8. Then: run full suite (expect all green), `uv build`, create tag `v0.3.0`.
