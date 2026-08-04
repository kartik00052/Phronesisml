# PhronesisML — Coding Standards

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Operational summary of the rules that are enforced. The binding constitution is `AI_QUALITY_GATE.md` — this file condenses its coding sections (§2, §3, §5, §11) into a quick reference. When these conflict, the gate wins.

## 1. Language & runtime

- Python floor `>=3.11` (`pyproject.toml`). Use `from __future__ import annotations` and modern idioms (`StrEnum`, `typing.Self`-era annotations).
- Never loosen global type strictness to silence third-party stub gaps; use targeted `# type: ignore[import-untyped]` / `[import-not-found]`.

## 2. Style (enforced)

- `ruff` lint + `ruff format` with repo config (`line-length = 100`, selected rules incl. `ANN`).
- `ruff format --check .` must be clean — never hand-prettify against it.

## 3. Architecture constraints

- LangGraph orchestration only; never call agents ad hoc.
- `WorkflowState` field ownership map must be updated when adding fields.
- Composition root in exactly two places (`phronesisml/__init__.py`, `sdk.py`).
- Engine-neutral code MUST copy before in-place mutation (`collect()` returns a cached pandas frame — BUG-01).
- Shared constants live in exactly one module (e.g. `MAX_CLASSIFICATION_UNIQUE_VALUES` in `auto_selector.py`, `AMBIGUITY_THRESHOLD` in the target detector). Do not reintroduce per-module copies.

## 4. Coding rules

- **Lazy imports:** heavy imports (sklearn, shap, mlflow, spark, sdk) stay lazy (`__getattr__` in `__init__.py`, imports inside functions). `import phronesisml` must stay cheap (~16 ms).
- **Comments:** no comments by default; reserved for invariants, drift warnings, and non-obvious constraints.
- **Secrets:** never commit credentials; no outbound telemetry.
- **No new dependencies** without justification + an extras decision in `pyproject.toml`.
- **Exceptions:** use `phronesisml/exceptions.py`. Wrap third-party errors at the public boundary.
- **Deterministic ordering:** sort or seed iteration order; no dependence on `set`/`dict` insertion order for results.
- **Follow existing patterns:** new modules mirror existing ones (schemas.py/agent.py per agent; trainer-style module per ML subsystem).

## 5. Public API conventions

- Public functions are typed, documented (google-style docstrings, mkdocstrings-compatible), and exported through their package `__init__.py`.
- New engine-light/offline helpers return pure, deterministic, JSON-able dicts.
- `(result_df, log_dict)` pattern for data/feature transforms, matching `data/transformers/cleaning.py`.
- Once a field ships in the SDK/API envelope, it is frozen; new fields are additive-only.

## 6. AI contributor rules (condensed from gate §11)

- Read `AI_QUALITY_GATE.md`, `project_state.json`, then the code — in that order.
- Every claim about behavior must be grounded in code or a reproduced run; unverified claims are marked `NOT VERIFIED`.
- Never invent files/modules/tests/metrics. Call functions with their real parameter names.
- Regenerate `project_state.json` after every completed task with real numbers.

## 7. Anti-patterns (rejected by design)

| Anti-pattern | Rejected because |
|---|---|
| Business logic in CLI | Violates SDK-first |
| Global singletons / service locators | Untestable, hidden coupling |
| Silent SHAP fallback | Violates transparency — warn and explain |
| Silently resolving ambiguous targets | Must surface `ambiguity_caveat` |
| New cloud/LLM/GPU mandates | Violates offline-first |
