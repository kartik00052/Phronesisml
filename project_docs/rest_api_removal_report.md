# PhronesisML — REST API Decommission Report

> **Purpose:** Final record of the v0.3.0 REST API decommission — what was removed, what was preserved, and the verification evidence.
> **Date:** 2026-08-05
> **Predecessor:** `rest_api_inventory.md` (pre-removal dependency analysis, kept as the decommission record).
> **Status:** COMPLETE — all 13 steps executed; quality gate green post-removal.

---

## 1. Decision

PhronesisML is SDK-first and CLI-first. The REST API subsystem (`phronesisml/interfaces/api/`) was a thin transport wrapper over the shared ML pipeline with no unique business logic. It was removed to reduce the attack surface, drop three runtime dependencies, and cut packaging/CI/deployment surface.

- **DECISION-011** in `Decision_Log.md` (REST-first) annotated **obsolete**.
- Decision recorded in `CHANGELOG.md` under `[0.3.0] - 2026-08-05`.

## 2. Shared logic preserved (Step 2 verification)

The inventory proved the REST layer delegated entirely to shared modules. All of the following remain untouched and are the public SDK surface:

| Shared component | Used by the REST layer via | Status |
|---|---|---|
| `phronesisml/simple.py` async fns (`analyze_async` … `report_async`) | `interfaces/api/routes.py` | Preserved (public SDK) |
| `phronesisml/_stages.py` (`_FULL_PIPELINE_STAGES`) | `routes.py` | Preserved |
| `phronesisml/workflow/graph.py` (`PIPELINE_ORDER`) | `routes.py:175` | Preserved |
| `phronesisml/__init__.py` (`__version__`, `__all__`, `_LAZY_IMPORTS`) | `app.py:24`, `routes.py:21` | Preserved |

**Conclusion:** no logic was lost; only the REST wrapper was deleted.

## 3. Removed source code

| Path | Notes |
|---|---|
| `phronesisml/interfaces/api/__init__.py` | Package docstring; documented the uvicorn run command |
| `phronesisml/interfaces/api/app.py` | FastAPI app, CORS + timing middleware, exception handlers, router registration |
| `phronesisml/interfaces/api/routes.py` | REST route handlers (thin adapters over `simple.py`) |
| `phronesisml/interfaces/api/models.py` | Pydantic request/response schemas + API constants |
| `phronesisml/interfaces/api/jobs.py` | In-memory async job store |
| `tests/test_interfaces.py` | REST-only portion removed (`rest_client` fixture + 6 smoke tests); 5 CLI tests kept |
| `tests/test_regressions.py` | BUG-03 job-store test + `_api_client` section (3 tests) removed; 13 regression tests kept |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | REST-server deployment removed |
| `docs/guides/rest-api.md` | REST API guide deleted |

## 4. Removed dependencies

| Dependency | Where removed |
|---|---|
| `fastapi` | `[api]` extra deleted; `all` extra no longer includes it |
| `uvicorn` | `[api]` extra deleted |
| `python-multipart` | `[api]` extra deleted |
| `pydantic` | **Preserved** — required by `configs/settings.py` and workflow state |
| `httpx` | Preserved as a dev/test dependency only (no import in package code) |

`pyproject.toml`, `requirements.txt`, `Makefile`, and `.github/workflows/ci.yml` were cleaned; `pyproject.toml` sdist-exclude entries for the deleted Docker files were removed.

## 5. Documentation updated (Step 11)

- **Repo root (GitHub-standard files):** `README.md`, `CHANGELOG.md`.
- **`docs/`:** `mkdocs.yml`, `index.md`, `getting-started.md`, `examples.md`, `limitations.md`, `troubleshooting.md`, `design-decisions.md`, `guides/cli.md`, `guides/simple-api.md`, all `root_cause/*.md`.
- **`project_docs/`:** `API_Contracts.md`, `Architecture.md`, `Coding_Standards.md`, `Decision_Log.md`, `Known_Issues.md`, `MASTER_FUNCTION_MATRIX.md`, `Release_Process.md`, `Roadmap.md`, `Testing.md`, `templates/*`, `project_state.json` *(plus the audit/state files `ARCHITECTURE_AUDIT.md`, `AUDIT_REPORT.md`, `CODEBASE_INTEGRITY_REPORT.md`, `DUPLICATION_REPORT.md`, `IMPLEMENTATION_ROADMAP.md`, `PROJECT_KNOWLEDGE_BASE.md`, `PUBLIC_API_AUDIT.md`, `TASK_SUMMARY.md`, consolidated here on 2026-08-05)*.
- Historical records (AUDIT_REPORT, root_cause/*, CHANGELOG v0.1.x/0.2.x entries, project state files) are annotated *obsolete since v0.3.0* rather than rewritten, preserving the audit history.

## 6. Verification evidence

### 6.1 Static scans

- `grep fastapi|uvicorn|starlette|interfaces.api|APIRouter|UploadFile|HTTPException|TestClient|:8000` over `phronesisml/**/*.py` → **0 matches**.
- Only 4 benign docstring mentions of "FastAPI" remain in the SDK (`simple.py`, `sdk.py`, `agents/base.py`) as generic async-context examples ("inside FastAPI or Jupyter async mode"); these do not reference the removed subsystem.
- `Makefile`, `.github/workflows/ci.yml`, `requirements.txt` → no docker/fastapi/uvicorn/8000 references.
- Non-annotated REST/Docker references in `docs/` and `project_docs/`: **0** (remaining mentions are the inventory record, changelog entries, and *obsolete/removed-in-v0.3.0* annotations).

### 6.2 Import smoke tests

- `import phronesisml` OK; `from phronesisml import *` OK (no api entries in `_LAZY_IMPORTS`).
- `from phronesisml.sdk import Phronesis` OK; `from phronesisml.interfaces.cli.app import app` OK.
- CLI `phronesisml --help` and `phronesisml info` render correctly.

### 6.3 Quality gate (run 2026-08-05)

| Step | Command | Result |
|---|---|---|
| Lint | `python -m ruff check .` | clean |
| Format | `python -m ruff format --check .` | 121 files formatted, 0 would change |
| Types | `python -m mypy phronesisml` | 50 errors in 26 files — all documented third-party-stub category (pandas/sklearn/mlflow/pyspark); down from 51 (4 REST modules removed); `--ignore-missing-imports` clean |
| Tests | `python -m pytest -q` | **274 passed, 0 failed** |
| Build | `python -m build` | wheel + sdist built successfully |
| Wheel | content scan | contains only `phronesisml/interfaces/cli/` under `interfaces/`; no api/fastapi/uvicorn/starlette/8000 in package files |
| sdist | content scan | no Dockerfile/docker-compose/.dockerignore/rest-api artifacts |
| Install | `pip install --force-reinstall --no-deps dist/*.whl` | OK |
| E2E CLI | `phronesisml run <smoke.csv>` | full 17-stage pipeline completed; 3 artifacts stored |
| E2E SDK | `from phronesisml import Phronesis, run_pipeline, __version__` | OK |

## 7. Residual references (intentional)

| Location | Why it remains |
|---|---|
| `rest_api_inventory.md` | Pre-removal analysis — the decommission record itself |
| `CHANGELOG.md` `[0.3.0]` entry | Documents the removal |
| Historical docs (AUDIT_REPORT, root_cause/*, old changelog entries, old state files) | Annotated *obsolete since v0.3.0*, preserved for audit history |
| SDK docstrings (`simple.py`, `sdk.py`, `agents/base.py`) | Generic async-context examples, not references to the removed subsystem |

## 8. Success criteria

- [x] No REST code, docs, or dependencies remain in the shipped package
- [x] SDK + CLI fully functional and verified end-to-end
- [x] All tests pass (274/274)
- [x] Wheel + sdist build and install cleanly
- [x] No broken imports (repo-wide static scan + import smoke tests)
- [x] No shared logic deleted (inventory cross-reference verified)

**Status: DECOMMISSION COMPLETE.**
