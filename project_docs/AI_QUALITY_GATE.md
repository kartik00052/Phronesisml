# AI Quality Gate — PhronesisML Constitution

> **Status:** Mandatory reading for every human and AI contributor **before writing a single line of code**.
> **Scope:** Applies to all source, tests, configuration, infrastructure, and documentation changes in this repository.
> **Enforcement:** The rules below are not advisory. A change that violates this document is not done — regardless of whether tests pass.
> **Supersedes:** This document is the single constitution of PhronesisML. It consolidates the SDK-first, offline-first, deterministic, transparent, modular, resource-aware principles previously referenced as `INSTRUCTIONS.md` (which is not present in the tree) and adds the mandatory project-state ritual (§12).
> **Companion file:** `project_state.json` — the machine-readable, always-current project snapshot that every contributor regenerates after each completed task (§12).

---

## Table of Contents

1. [Project Philosophy](#1-project-philosophy)
2. [Architecture Rules](#2-architecture-rules)
3. [Coding Rules](#3-coding-rules)
4. [Documentation Rules](#4-documentation-rules)
5. [Testing Rules](#5-testing-rules)
6. [Packaging Rules](#6-packaging-rules)
7. [Release Rules](#7-release-rules)
8. [Root Cause Analysis Workflow](#8-root-cause-analysis-workflow)
9. [Quality Gate](#9-quality-gate)
10. [Definition of Done](#10-definition-of-done)
11. [AI Hallucination Prevention Rules](#11-ai-hallucination-prevention-rules)
12. [Project State File Ritual](#12-project-state-file-ritual)

---

## 1. Project Philosophy

PhronesisML is an **offline-first, deterministic, resource-aware ML-engineering SDK** — an auto-ML platform that automates the complete machine-learning lifecycle from raw data to an evaluated, explained model plus an on-disk artifact suite, without writing ML code.

Non-negotiable values:

1. **SDK-first.** The Python SDK (`simple`, OOP `Phronesis`, `run_pipeline`) is the canonical interface. The CLI is a thin adapter over it. Never put business logic in the CLI layer.
2. **Offline-first.** No mandatory cloud, LLM, GPU, or network dependency. Optional integrations (MLflow, Spark) must degrade gracefully when absent.
3. **Deterministic.** Seeded RNG everywhere (sampling, HPO, explainability). A given input + config must reproduce a given output.
4. **Transparent and inspectable.** Rule-based, deterministic selection and heuristics over black-box magic. Users must be able to read *why* a decision was made.
5. **Modular and testable.** Protocol-based agents, constructor-injected composition root, explicit data contracts.
6. **Resource-aware by default.** Every potentially expensive operation carries a hard ceiling (`max_trials`, `max_time_seconds`, SHAP `max_samples`/`max_features`, LOF row cap, upload size cap, pre-flight sampling).
7. **Honest about uncertainty.** Ambiguity is surfaced (`ambiguity_caveat`, `ambiguity_reason`), never silently resolved.
8. **Correctness over features.** The pipeline must never silently deliver a wrong model/metric pair (see BUG-02 history). Metrics must derive from the actual model class and resolved task class.

---

## 2. Architecture Rules

The architecture is the contract. Do not drift from it without explicit approval.

1. **LangGraph orchestration.** The pipeline is a LangGraph state machine. Nodes wrap agents; routers decide `proceed` / `__end__`. Do not bypass the graph to call agents ad hoc.
2. **`WorkflowState` field ownership.** Every state field is owned by exactly one stage (see `workflow/state.py`). A stage may only write its own fields; reads are governed by the ownership map. Adding a field requires updating the ownership map.
3. **Composition root (DI).** All agents are constructor-injected in exactly two places (`phronesisml/__init__.py` and `sdk.py` → `agents/compose.py`). No service locators, no global singletons, no import-time agent construction.
4. **Agents are Protocols.** `BaseAgent` is a structural Protocol. Every agent returns the `AgentResult(success, data, error, error_type, error_message, error_context)` envelope and **MUST NOT raise for expected failures**.
5. **Engine abstraction.** All data operations go through `BaseEngine` (`collect()` / `lazy()`). Auto-route by size: `< 2 MB` pandas, `2–500 MB` polars, `> 500 MB` spark; `EngineConfig.preferred` overrides. **`collect()` returns a cached pandas frame — engine-neutral code MUST defensively copy before any in-place mutation** (BUG-01).
6. **Deterministic pipeline order.** Stage order is fixed (`_stages.py`, `_FULL_PIPELINE_STAGES`). Do not reorder stages for one-off fixes; evolve the routing table instead.
7. **Single source of truth.** Shared constants and rules live in exactly one module (e.g. `MAX_CLASSIFICATION_UNIQUE_VALUES`, `AMBIGUITY_THRESHOLD`). Do not reintroduce per-module copies — this exact drift caused BUG-02.
8. **Fail-fast, degrade gracefully.** `AgentError` halts the workflow; `AgentNotImplementedError` skips with partial results preserved. Optional integrations degrade with a warning, never a crash.
9. **No silent aliasing.** Shared mutable state (engine collect cache, upstream DataFrames) must never be mutated behind the caller's back.

---

## 3. Coding Rules

1. **Python floor `>=3.11`** (per `pyproject.toml`); CI validates on 3.13. Use `from __future__ import annotations` and modern idioms (`StrEnum`, `typing.Self`-era annotations).
2. **Style.** `ruff` (lint + format) with the repo config (`line-length = 100`, selected rules incl. `ANN`). Formatting is enforced by `ruff format --check` — never hand-prettify against it.
3. **Types.** `mypy` strict is the target. Third-party stub gaps (pandas, sklearn, mlflow, pyspark) are handled with targeted `# type: ignore[import-untyped]`/`[import-not-found]` — not by loosening global strictness. Do not add new *un-ignored* mypy errors beyond the documented baseline.
4. **Lazy imports.** Heavy imports (sklearn, shap, mlflow, spark, sdk) stay lazy (`__getattr__` in `__init__.py`, imports inside functions). `import phronesisml` must stay cheap.
5. **No comments by default.** Write self-documenting code. Comments are reserved for invariants, drift warnings, and non-obvious design constraints. Do not restate the code in prose.
6. **Secrets.** Never commit secrets, credentials, or API keys. No outbound telemetry.
7. **No new dependencies** without justification and a `pyproject.toml` extras decision. Prefer reusing existing machinery.
8. **Exceptions.** Use the existing hierarchy (`phronesisml/exceptions.py`). Wrap third-party errors at the public boundary; never leak raw tracebacks in the SDK/API envelope.
9. **Deterministic ordering.** When iteration order matters for reproducibility, sort or seed it. No dependence on `set`/`dict` insertion order for results.
10. **Follow existing patterns.** New modules mirror existing ones (schemas.py/agent.py per agent; a `trainer`-style module per ML subsystem). Copy the established shape before innovating.

---

## 4. Documentation Rules

1. **Docs are part of the deliverable.** A code change without its doc update is incomplete. This includes README, `docs/`, `mkdocs.yml` nav, docstrings, and `CHANGELOG.md`.
2. **Accuracy over coverage.** Every claim must be verifiable against the code. If it cannot be verified, mark it `NOT VERIFIED` (see §11). Docs that contradict the implementation are a defect (ISSUE-06 class).
3. **Public API docstrings** follow google style (mkdocstrings-compatible) and document args, returns, and raised exceptions.
4. **Feature/limitation matrices** (knowledge base, README) must match reality. When behavior changes, update the matrices in the same change.
5. **AUDIT_REPORT / ROADMAP / KNOWLEDGE_BASE** are living documents tied to the version they describe. Note the version and date in each.

---

## 5. Testing Rules

1. **Every defect fix ships a regression test first** (tests must fail on the pre-fix code and pass post-fix). New fixes belong in `tests/test_regressions.py` following the BUG-xx/ISSUE-xx naming convention.
2. **Test the path that broke.** A fix without a test that exercises the *original failure mode* is not done.
3. **Behavioral assertions over implementation details.** Assert observable outcomes (frame equality, metric sets, job status) — not internal call counts.
4. **Deterministic fixtures.** Synthetic data with fixed RNG seeds; `tmp_path` for any file output; never write into the repo root from tests.
5. **CLI tests** cover the Typer surface end-to-end as delegated through the SDK. The SDK is tested via the simple/OOP surfaces.
6. **No new warnings that matter.** Suppress only expected third-party deprecation warnings; do not hide regressions behind broad filters.
7. **The full suite must pass** before a change is complete (§9).

---

## 6. Packaging Rules

1. **Build with `hatchling`** per `pyproject.toml`. Never hand-package.
2. **Extras.** Dependencies that are not core go behind extras: `cli`, `spark`, `mlflow`, `excel`, `dev`, `all`. README extras tables must match `pyproject.toml` exactly (ISSUE-06 class defect).
3. **`py.typed`** is shipped (type hints are a feature).
4. **Wheel smoke test.** Before any release, build a wheel and install it in a **clean venv** (correct Python floor), then run CLI and SDK end-to-end.
5. **sdist hygiene.** Exclude tests, benchmark scratch, CSV fixtures, and internal docs from the sdist per the existing `[tool.hatch.build.targets.sdist]` exclusions.

---

## 7. Release Rules

1. **Semver.** `MAJOR.MINOR.PATCH`. Pre-1.0, behavior-correcting bug fixes ship in `MINOR` (e.g. Phase 1 → `0.3.x`); API breaks ship in `MAJOR` (1.0).
2. **Conventional commits.** `fix:`, `feat:`, `docs:`, `chore:`, `style:`, `release:`, `refactor:`. History must stay readable.
3. **`CHANGELOG.md`** gets an entry for every release, citing fix IDs (BUG-xx, ISSUE-xx).
4. **Non-breaking by default.** Changes that alter observable behavior are **additive/opt-in** unless explicitly approved as breaking. Breaking changes require per-item approval and a migration note.
5. **Gate before tagging.** §9 quality gate green + clean-room wheel smoke test + docs sync + `project_state.json` regenerated.
6. **Version bump in one place** (`phronesisml/__init__.py:__version__`), then propagate consistently (API `/version`, CLI info).

---

## 8. Root Cause Analysis Workflow

When a defect is found, follow this order — do **not** jump to a patch:

1. **Reproduce.** Write a minimal reproduction (deterministic synthetic data). Prove the failure before touching code.
2. **Isolate the boundary.** Identify the earliest stage/module where behavior diverges from contract. Find the *root* — e.g. BUG-02 was not a metrics bug; it was a task-resolution drift at the detector/selector boundary plus a mixed candidate pool.
3. **Classify.** Correctness (wrong result), contract (wrong shape/key), liveness/ops (event loop blocking), or docs/packaging.
4. **Fix at the choke point.** Prefer the single source of truth (one shared rule, one writer, one boundary) over patching every symptom. Where a rule already exists, extend it; where it does not, create it and delete the per-module copies.
5. **Prove the fix.** Add a regression test that fails on the old code (§5.1). Run the full gate (§9).
6. **Check for siblings.** The same root cause elsewhere (e.g. all `model.score()` call sites, all `get("best_params")` readers) must be fixed together.
7. **Record it.** Update `project_state.json` (§12) and, for significant defects, the AUDIT/ROADMAP docs.

---

## 9. Quality Gate

The gate below is **mandatory** for every change that touches code, config, or infrastructure. Run in the listed order; the change is blocked until every step is green.

| Step | Command / Check | Requirement |
|---|---|---|
| Lint | `ruff check .` | Zero errors |
| Format | `ruff format --check .` | Zero files would be reformatted |
| Types | `mypy phronesisml/ --ignore-missing-imports` | Clean (0 errors in 101 files as of the v0.3.0 packaging gate) |
| Tests | `pytest -q` (full suite) | All tests pass, including `tests/test_regressions.py` |
| Packaging (release only) | `python -m build` + clean-venv wheel smoke test | Wheel builds and installs; CLI/SDK run end-to-end |
| State file | §12 | `project_state.json` regenerated and accurate |
| Docs | §4 | No doc/implementation contradiction introduced |

Targets: `make lint`, `make format`, `make typecheck`, `make test`, `make check`.

---

## 10. Definition of Done

A task is **done** only when all of the following hold:

- [ ] Root cause identified and documented (if a defect) — §8.
- [ ] Fix implemented at the choke point; no symptom-patching.
- [ ] Regression test added that fails on the pre-fix code (for defects).
- [ ] Full test suite passes: `pytest -q`.
- [ ] `ruff check .` and `ruff format --check .` are clean.
- [ ] No new mypy errors over the documented baseline.
- [ ] Docs updated in the same change (§4) — README, `docs/`, docstrings, `CHANGELOG.md` as applicable.
- [ ] Public API preserved (or breaking change explicitly approved and documented).
- [ ] `project_state.json` regenerated with accurate counts/status (§12).
- [ ] No stray files, no committed secrets, no artifacts written into the repo root.

---

## 11. AI Hallucination Prevention Rules

AI contributors are the primary audience of this section. These rules are hard constraints.

1. **Read before you write.** Read this document, then `project_state.json`, then the relevant code — in that order — before producing any change. Never assume repository facts from memory.
2. **Verify against the tree.** Every claim about existing behavior must be grounded in code or a reproduced run. Mark unverified claims `NOT VERIFIED` (the roadmap's `VERIFIED` / `INFERRED` / `NOT VERIFIED` legend applies).
3. **No invented artifacts.** Never cite files, modules, endpoints, or APIs that do not exist (e.g. a non-existent `INSTRUCTIONS.md`). If the roadmap references something absent from the tree, say so.
4. **No invented tests.** Tests must reference real functions/signatures. Run them. A test that cannot pass is a hallucination.
5. **No invented metrics/values.** Never fabricate benchmark numbers, coverage percentages, or "reported" results. Reproduce or omit.
6. **Signature discipline.** Call functions with their real parameter names (e.g. `recommend_models(task_type, n_rows, ...)` — positional/keyword names from the definition, not invented ones). A `TypeError` in your own test is a hallucination, fix the test to match reality.
7. **Documentation must not oversell.** Do not claim a feature works unless a test or reproduced run proves it. Do not write docs that contradict `project_state.json` or the code.
8. **When unsure, verify or ask.** Prefer a web search / file read / failing test over guessing. Never silently assume.
9. **State-file discipline.** Regenerate `project_state.json` (§12) with real numbers only — never a plausible guess.
10. **Report honestly.** If a step could not be verified (e.g. Docker daemon unavailable), record it as unverified in the state file and in the task summary.

---

## 12. Project State File Ritual

`project_state.json` is the machine-readable snapshot that lets the next agent resume work **without re-analyzing the repository**.

**Mandatory rule:** after **every completed task**, regenerate it so its values reflect the working tree at that moment.

Schema (keep these top-level fields stable; extend sub-objects additively):

| Field | Meaning | Example |
|---|---|---|
| `schema_version` | Version of this state-file schema | `1` |
| `updated_at` | ISO-8601 UTC timestamp of the last regeneration | `2026-08-04T12:00:00Z` |
| `current_version` | `__version__` from `phronesisml/__init__.py` | `0.2.2` |
| `phase` | Roadmap phase in progress | `1` |
| `git` | `branch`, `commit`, `dirty` (working tree vs HEAD) | — |
| `completed_roadmap_items` | Roadmap items done in the working tree (id, title, status: `done`/`in_working_tree`) | — |
| `pending_roadmap_items` | Roadmap items not yet started (id, phase, priority) | — |
| `known_issues` | Open defects/limitations with severity and evidence | — |
| `verified_features` | Behaviors proven by tests or reproduced runs | — |
| `failed_checks` | Gate steps currently failing (empty array = all green) | — |
| `last_verification` | `{ timestamp, tool, command, result }` of the last gate run | — |
| `test_counts` | `{ total, passed, failed, regression, api, files }` from `pytest` | — |
| `documentation_sync` | `{ status: "synced" \| "partial", notes }` | — |
| `notes` | Free-form context for the next agent (uncommitted work, caveats) | — |

Rules:

- Update it with **real values** — run the commands, count the tests, read the version. Never fabricate.
- Keep `failed_checks` accurate; an empty array is a true claim that the last gate run was green.
- JSON only — no comments; the file is parsed by tools and agents.
- Review `AI_QUALITY_GATE.md` and this file as the first two reads of any new task.
