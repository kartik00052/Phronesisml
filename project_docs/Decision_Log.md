# PhronesisML — Decision Log

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Consolidated log of architectural decisions. Deep rationale for the original 8 decisions: `../docs/design-decisions.md`. New entries recorded here as decisions land. Format: **DECISION-xxx** — Problem → Chosen → Rejected → Why.

## Original decisions (AetherML era → 0.2.0)

| # | Decision | Chosen | Rejected | Why |
|---|---|---|---|---|
| DECISION-001 | Agent shape | Protocol-based agents (`BaseAgent` via duck typing) | Function soup, global state, ABC inheritance | Signature bloat / thread hazards / diamond inheritance |
| DECISION-002 | Orchestration | LangGraph stateful graphs | Airflow, Prefect, custom DAG executor | Typed state, conditional routing, cache, lightweight |
| DECISION-003 | Engine abstraction | 3-tier auto-select (<2 MB pandas, 2–500 MB polars, >500 MB spark) | Single engine, pluggable abstract engine | Performance + memory + distributability with one interface |
| DECISION-004 | Data processing | Two-stage: ETL (all columns) → target detection → FE (features only) | Single stage, guess-target-first, skip ETL | Can't exclude a target you haven't detected yet |
| DECISION-005 | Model catalog | Hardcoded candidates per task (3–5 sklearn models) | Plugin system, YAML defs, dynamic import | Security + determinism; plugin system deferred |
| DECISION-006 | Job store | In-memory `JobStore` dict *(obsolete — REST layer removed in v0.3.0)* | SQLite/Postgres/Redis/Celery | Simplicity for current scope; durable store planned |
| DECISION-007 | Explainability | SHAP with explainer routing | LIME, permutation-only, custom | Per-instance explanations, mature, resource-bounded |
| DECISION-008 | State model | Pydantic `WorkflowState` BaseModel | Plain dict, TypedDict, dataclass | Runtime validation + self-documenting types |

## Recent decisions (2026)

| # | Decision | Chosen | Rejected | Why |
|---|---|---|---|---|
| DECISION-009 | Ambiguous-task resolution | `resolve_task_class()` single source of truth in `auto_selector.py`; trainer filters candidates; metrics derive from model class | Per-module thresholds | BUG-02 root cause was threshold drift across modules |
| DECISION-010 | `outlier_flag` handling | Metadata-only by default; opt-in `include_outlier_flag` | Keep leaking into features | BUG-01: silent aliasing + feature leak |
| DECISION-011 | REST job execution *(obsolete — REST layer removed in v0.3.0)* | `asyncio.to_thread` off-loop execution | In-loop `asyncio.create_task` | BUG-03: blocked event loop / dead healthcheck |
| DECISION-012 | `best_params` contract | Writer emits both `params` and `best_params`; readers prefer `best_params` | Immediate key removal | BUG-04: non-breaking deprecation window |
| DECISION-013 | Run metadata | Run-metadata population of `run_id`/`status`; `"default_run"` fallback kept | Breaking schema change | BUG-05: additive fix, fallback stays |
| DECISION-014 | HPO time budget | Hard ceiling enforced between trials; in-flight trial allowed to finish | Per-trial kill | ISSUE-07: bounded overshoot by design |
| DECISION-015 | New engine-light data/ML modules | Pure, offline, JSON-able dict returns; `(result_df, log_dict)` for transforms | Agent-coupled helpers | Deterministic + testable + reusable across SDK/CLI |

## Standing rejections

| Request | Decision |
|---|---|
| Time-series, PDF reports | Rejected/deferred (KNOWN-003/004) |
| Cloud/LLM/GPU mandates, AI-agent framing | Rejected — violates constitution §1 |
| Silent SHAP fallback | Rejected — must warn + explain |
| `[docs]` pip extra | Rejected — no consumers; `mkdocs` runs from `dev` |
| `Instructions.md` | Rejected — superseded by `AI_QUALITY_GATE.md`; creating it would create a second constitution |
