# PhronesisML — Roadmap

> **Version:** 0.2.2 → 1.0 · **Date:** 2026-08-04
> **Status:** Consolidated summary. The canonical roadmap with ranked features, breaking/non-breaking taxonomy, module/API/LangGraph/CLI proposals and timeline is `IMPLEMENTATION_ROADMAP.md` at the repo root. This file is the quick reference; item IDs match.

## Strategic phases

| Phase | Version | Theme | Key items |
|---|---|---|---|
| 1 | 0.3.x | Correctness hardening | BUG-02, BUG-01, BUG-03, BUG-04, BUG-05, ISSUE-07, ISSUE-06, ISSUE-08 + regression tests + CLI test suite + post-fix gate |
| 2 | 0.4.x–0.5.x | Beta surfaces | Schema validation, model recommendation with WHY, drift check, local run ledger, extra report formats, HPO UX, docs packaging |
| 3 | 1.0 | Ship | Pipeline serialization, local serving, ONNX + model registry, spark hardening, frozen API contract |

## Completed (in working tree, uncommitted)

- Phase 1 correctness: BUG-01…05, ISSUE-06…08 — regression tests in `tests/test_regressions.py` (13).
- Master function matrix (19 sections): engine-light data/validation/etl/eda modules, target analysis, feature construction, resource estimation, engine recommendation, model recommendation report, evaluation report helpers, explainability summary, artifact storage helpers, report IO helpers. Evidence: `MASTER_FUNCTION_MATRIX.md`.

## Phase 2 (target 0.4.x–0.5.x)

1. **Schema validation** — `validate_schema()` / `infer_schema()` (already shipped engine-light in `data/validation.py`; wire into pipeline as a stage).
2. **Model recommendation with WHY** — rationale field + plain-language report block.
3. **Data-drift check API** — `check_drift(reference, current, features=...)`.
4. **Local run ledger** — `compare_runs()`; MLflow stays optional.
5. **Reporting** — PDF + structured-JSON variants (additive).
6. **HPO UX** — user-configurable grids (non-breaking).
7. **Docs & packaging** — mkdocs nav, per-module doc sync.

## Phase 3 (v1.0)

1. Pipeline serialization + versioned artifact registry.
2. Local model serving (`phronesisml serve`).
3. ONNX export + model registry (`ml/export`, `<base>/models/<run_id>/`).
4. Spark scale-out hardening + benchmarks.
5. Python support policy + strict-mypy zero errors.
6. CI release pipeline (wheel + SBOM + vuln scan + PyPI).
7. v1.0 freeze (additive-only contract, migration guide).
8. Beyond 1.0: ensembling/stacking, feature-level SHAP plots, distributed on demand.

## Explicitly out of scope

Multimodal ingestion (audio/image), vector-store/RAG tie-in, mandatory LLM/cloud/GPU features, time-series (KNOWN-004), PDF (KNOWN-003).
