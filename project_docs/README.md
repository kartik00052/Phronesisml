# PhronesisML — Internal Project Documentation (Session Entry Point)

> **Read this file first in any new session.** Everything needed to understand the project's design, state, quality rules, history, and decisions lives in this folder. If you are resuming work, start with this file, then `AI_QUALITY_GATE.md`, then `project_state.json`, then the relevant topical doc — in that order.
>
> **Last synced:** 2026-08-05 (v0.3.0 REST-API decommission + docs consolidation).

---

## 1. Project in one paragraph

PhronesisML is an automated ML lifecycle SDK (installable wheel, no server) with a Python SDK (`phronesisml.sdk` / `phronesisml.simple`), a Typer CLI (`phronesisml run ...`), a deterministic 11-stage LangGraph pipeline, engine abstraction (pandas/polars/spark auto-routing), bounded HPO, per-task evaluation, SHAP explainability, and Markdown/HTML/JSON report generation. The REST API subsystem was removed in v0.3.0 (2026-08-05) — the project is now SDK-first / CLI-first. Published on PyPI as `phronesisml` (v0.2.2); v0.3.0 changes are in the working tree, uncommitted.

## 2. How to read this folder (recommended order for a new session)

| # | File | Why read it |
|---|---|---|
| 1 | `README.md` (this file) | Orientation + file map + current state |
| 2 | `AI_QUALITY_GATE.md` | The binding constitution: rules, quality gate, release rules, §12 state-file contract |
| 3 | `project_state.json` | Machine-readable, always-current snapshot: bugs, known issues, verified features, test counts, gate results |
| 4 | `Architecture.md` | Design overview; single entry point into the layer model |
| 5 | `MASTER_FUNCTION_MATRIX.md` | Verified 19-section inventory of every public function/module with evidence |
| 6 | `PROJECT_KNOWLEDGE_BASE.md` | File-by-file technical reference (largest doc; skim, use as a lookup) |
| 7 | `Decision_Log.md` | Every decision + standing rejection (DECISION-001..015) |
| 8 | `Testing.md` | Test layout, gate commands, baselines |
| 9 | `Coding_Standards.md` | Enforced style/type rules |
| 10 | `Workflow.md` | Dev workflow + run-scoped report rules |
| 11 | `Release_Process.md` | Release steps |
| 12 | `Roadmap.md` | Quick phase/priority reference |
| 13 | `Known_Issues.md` | Residual/known limitations (machine truth: `project_state.json`) |
| 14 | `API_Contracts.md` | Public SDK/CLI contract summary |
| 15 | `rest_api_removal_report.md` | Decommission record of the REST subsystem (v0.3.0) |
| 16 | `rest_api_inventory.md` | Pre-removal dependency analysis (historical) |
| 17 | `AUDIT_REPORT.md` | Clean-room production audit (historical, REST annotated obsolete) |
| 18 | `ARCHITECTURE_AUDIT.md` | Static architecture audit (historical) |
| 19 | `CODEBASE_INTEGRITY_REPORT.md` | Integrity/drift audit (historical) |
| 20 | `DUPLICATION_REPORT.md` | Duplication audit (historical) |
| 21 | `IMPLEMENTATION_ROADMAP.md` | Full phased roadmap (historical; superseded by `Roadmap.md` summary) |
| 22 | `PUBLIC_API_AUDIT.md` | Public-API surface audit (historical) |
| 23 | `TASK_SUMMARY.md` | Summary of the latest completed work tranche (historical) |
| 24 | `templates/` | `ROOT_CAUSE.template.md`, `TASK_SUMMARY.template.md` |

## 3. File layout outside this folder

| Location | Contents |
|---|---|
| `../docs/` | **User-facing** documentation site (MkDocs, `../mkdocs.yml`): index, getting-started, architecture, design-decisions, examples, api, troubleshooting, limitations, guides/ |
| `../docs/root_cause/` | Root-cause analysis write-ups (NEW-01…08) |
| `../docs/runs/` | Per-dataset run reports produced by pipeline executions |
| `../` (repo root) | GitHub-standard files only: `README.md`, `CHANGELOG.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `mkdocs.yml`, source `phronesisml/`, `tests/`, `benchmarks/` |
| `phronesisml/` (repo root) | The package (SDK + CLI). `phronesisml/interfaces/` contains only `cli/` after the v0.3.0 REST removal |

## 4. Current state (verified 2026-08-05)

- **Quality gate:** `pytest -q` → **305 passed, 0 failed**; `ruff check .` clean; `ruff format --check .` clean (121 files); `mypy phronesisml/ --ignore-missing-imports` → **clean (0 errors, 101 files)**.
- **Packaging:** wheel + sdist build cleanly via `uv build` and `python -m build`; `twine check dist/*` passes; wheel ships only the `phronesisml` package; sdist excludes `project_docs/`, `docs/`, `tests/`, Docker artifacts.
- **v0.3.0 REST decommission:** complete — no REST code/deps/docs remain (see `rest_api_removal_report.md`); SDK/CLI verified end-to-end.
- **uv migration:** complete — pyproject dynamic version, tracked cross-platform `uv.lock` (win32/darwin-arm64/linux), regenerated `requirements.txt`, dual pip+uv CI, `[docs]` extra (see `UV_MIGRATION_REPORT.md`).
- **Working tree:** v0.2.2, v0.3.0 REST-decommission, and packaging changes are **uncommitted** (35 entries on top of `b75818c`); tag `v0.3.0` not yet created.

## 5. Golden rules (from `AI_QUALITY_GATE.md`)

1. No invented metrics/values — reproduce or omit.
2. Docs are part of the deliverable — a code change without its doc update is incomplete.
3. Regenerate `project_state.json` after any state change (§12).
4. The quality gate (ruff → format → mypy → pytest → build) must pass before completion.
5. When resuming work, read this folder (esp. §2 order) — not the whole tree.
