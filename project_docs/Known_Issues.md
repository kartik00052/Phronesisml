# PhronesisML — Known Issues

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Machine-readable source of truth for issues is `project_state.json` (`known_issues`). This file is the human-readable companion. Audit detail: `AUDIT_REPORT.md`.

## 1. Phase-1 defects (fixed in working tree, uncommitted)

| ID | Severity | Status | Summary |
|---|---|---|---|
| BUG-01 | High | Fixed | Feature engineering mutated upstream state in place + leaked `outlier_flag` into features. Fix: defensive copy; `outlier_flag` metadata-only by default (opt-in `FeatureSelectionConfig.include_outlier_flag`). |
| BUG-02 | High | Fixed | Ambiguous-target contract broken: classifier selected for continuous target, then regression metrics reported. Fix: `resolve_task_class()` single source of truth in `auto_selector.py`; trainer filters candidates by resolved class; metrics derive from model class. |
| BUG-03 | High | Fixed | *(Obsolete — REST layer removed in v0.3.0.)* REST API blocked its event loop during CPU-bound jobs; `/health` unresponsive. Fix: `asyncio.to_thread` in job store. |
| BUG-04 | Medium | Fixed | `best_pipeline` key mismatch (`params` vs `best_params`). Fix: writer emits both; readers prefer `best_params` with `params` fallback. |
| BUG-05 | Low | Fixed | `run_id`/`status` never populated; report header showed `None`. |
| ISSUE-06 | Low | Fixed | README drift vs `pyproject.toml` extras / pipeline order. |
| ISSUE-07 | Low | Fixed | HPO `max_time_seconds` was a soft ceiling. Fix: budget enforced between trials. |
| ISSUE-08 | Low | Fixed | *(Obsolete — Docker image removed in v0.3.0.)* Docker installed `[api]` only; `.xlsx` failed in container. Fix: `[excel]` added. |

## 2. Residual / known limitations

| ID | Severity | Description |
|---|---|---|
| ISSUE-07-residual | Low | A single in-flight HPO trial may overshoot `max_time_seconds` (budget checked between trials). By design. |
| MYPY-001 | Resolved | Strict mypy is **clean** as of the v0.3.0 packaging gate — `mypy phronesisml/ --ignore-missing-imports` reports 0 errors in 101 files. The historical 50-error figure (pandas/sklearn/mlflow/pyspark stub category) was eliminated by fixing the 9 gate-blocking errors in 7 files. |
| KNOWN-001 | Medium | *(Obsolete — REST layer removed in v0.3.0.)* In-memory API job store; jobs lost on restart. |
| KNOWN-002 | Medium | Linear workflow graph; no feedback loops / conditional task-type branches. Phase 2/3. |
| KNOWN-003 | Low | PDF reports raise `NotImplementedError`. Markdown/HTML only. |
| KNOWN-004 | Low | No time-series support. |
| KNOWN-005 | Low | Spark path and MLflow active path not verified locally (need pyspark+JVM / mlflow). |

## 3. Documented drift found during doc consolidation (2026-08-04)

| Claim in docs | Reality | Action |
|---|---|---|
| KB says Python floor `>=3.12,<3.14` | `pyproject.toml` = `>=3.11` | KB to be corrected; this doc and `Architecture.md` state `>=3.11` |
| Roadmap says "12 protocol agents" | `phronesisml/agents/` has 11 agent packages | Roadmap wording to be corrected |
| README project structure lists `rag/` | `phronesisml/rag/` does not exist | README to be corrected |
| Charter references a `[docs]` extra | `pyproject.toml` defines `cli, spark, mlflow, excel, dev, all` | Reject `[docs]`; use `mkdocs` + `dev` |
| Charter references `Instructions.md` | Absent; superseded by `AI_QUALITY_GATE.md` | Documented in this set; file intentionally not created |

## 4. Rejected feature requests (philosophy conflicts)

| Request | Why rejected |
|---|---|
| Time-series modeling | Out of scope (KNOWN-004); no date-aware modeling planned before 1.0 |
| PDF reports | Deferred (KNOWN-003); external tooling workaround documented |
| Cloud/LLM/AI-agent features | Violates offline-first / no-hidden-behavior constitution |
| Silent SHAP fallback | Violates transparency; warn + explain instead |
| `[docs]` pip extra | Would add a packaging surface with no consumers; `mkdocs` runs from `dev` |
