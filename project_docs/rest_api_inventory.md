# PhronesisML — REST API Decommission Inventory

> **Purpose:** Complete dependency analysis of the REST API subsystem before removal.
> **Date:** 2026-08-05
> **Scope:** Every file, dependency, import, and doc reference related to FastAPI / Uvicorn / Starlette / REST routes / REST schemas / REST jobs / REST middleware / OpenAPI / Swagger / API startup / API configuration.

---

## 1. Source code — REST subsystem

| File path | Why it exists | Dependencies | Imports | Imported by | Safe to delete? |
|---|---|---|---|---|---|
| `phronesisml/interfaces/api/__init__.py` | Package docstring for the FastAPI layer; documents the uvicorn run command | none | none | `tests/test_interfaces.py` (`from phronesisml.interfaces.api import app`) | YES |
| `phronesisml/interfaces/api/app.py` | FastAPI application: app creation, CORS middleware, request-timing middleware, exception handlers, router registration, root endpoint | fastapi | fastapi (FastAPI, HTTPException, Request, RequestValidationError, CORSMiddleware, JSONResponse); `phronesisml.__version__`; `phronesisml.interfaces.api.models`; `phronesisml.interfaces.api.routes` | `tests/test_regressions.py` (`from phronesisml.interfaces.api.app import app`) | YES |
| `phronesisml/interfaces/api/routes.py` | REST route handlers — thin adapters over `phronesisml.simple` async functions | fastapi, python-multipart (runtime) | fastapi (APIRouter, File, Form, HTTPException, UploadFile); `phronesisml.__version__`; `phronesisml.interfaces.api.jobs`; `phronesisml.interfaces.api.models` | `phronesisml/interfaces/api/app.py` | YES |
| `phronesisml/interfaces/api/models.py` | Pydantic request/response schemas (APIResponse, ErrorDetail, JobData, HealthData, VersionData, CapabilitiesData) + API constants | pydantic | pydantic (BaseModel, ConfigDict, Field) | `phronesisml/interfaces/api/app.py`, `phronesisml/interfaces/api/routes.py` | YES |
| `phronesisml/interfaces/api/jobs.py` | In-memory async job store for background pipeline jobs (job lifecycle, off-loop execution) | none (stdlib: asyncio, uuid, dataclasses, datetime) | stdlib only | `phronesisml/interfaces/api/routes.py`; `tests/test_regressions.py` (`from phronesisml.interfaces.api.jobs import JobStore`) | YES |
| `phronesisml/interfaces/api/__pycache__/*.pyc` | Bytecode cache of the deleted API modules | — | — | — | YES |

## 2. Source code — imports of REST modules from outside `interfaces/api/`

| File path | Why it exists | Safe to delete? |
|---|---|---|
| `tests/test_interfaces.py` | Contains a `rest_client` fixture + 6 REST smoke tests (REST portion only) | YES (REST portion) |
| `tests/test_regressions.py` | Contains BUG-03 job-store test + API-level test section (`_api_client`, 3 tests) (REST portion only) | YES (REST portion) |

No other `.py` file in the repository imports `phronesisml.interfaces.api.*` or `fastapi`/`uvicorn`/`starlette`.

## 3. Shared logic used by the REST layer (MUST be preserved)

The REST routes are thin adapters; every functional path delegates to the shared SDK surface:

| Shared symbol | Lives in | Used by REST at | Preserve? |
|---|---|---|---|
| `analyze_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:226` | YES — public SDK |
| `clean_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:243` | YES — public SDK |
| `validate_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:260` | YES — public SDK |
| `detect_target_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:277` | YES — public SDK |
| `engineer_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:299` | YES — public SDK |
| `select_model_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:330` | YES — public SDK |
| `train_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:365` | YES — public SDK |
| `evaluate_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:398` | YES — public SDK (exported in `__all__`) |
| `explain_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:429` | YES — public SDK |
| `report_async` | `phronesisml/simple.py` | `interfaces/api/routes.py:459` | YES — public SDK |
| `PIPELINE_ORDER` | `phronesisml/workflow/graph.py` | `interfaces/api/routes.py:175` | YES — workflow core |
| `__version__` | `phronesisml/__init__.py` | `interfaces/api/app.py:24`, `routes.py:21` | YES |

**Conclusion:** no shared logic lives inside `interfaces/api/`; removing the directory removes only the REST wrapper. Nothing needs to be moved to core.

## 4. Tests that exclusively verify REST functionality (delete)

| Test | File | Verifies |
|---|---|---|
| `test_rest_health` | `tests/test_interfaces.py` | `GET /health` envelope |
| `test_rest_version` | `tests/test_interfaces.py` | `GET /version` |
| `test_rest_capabilities_include_all_stages` | `tests/test_interfaces.py` | `GET /capabilities` |
| `test_rest_rejects_unsupported_format` | `tests/test_interfaces.py` | 415 on unsupported upload |
| `test_rest_job_flow_completes` | `tests/test_interfaces.py` | async job lifecycle |
| `test_bug03_jobstore_runs_cpu_work_off_loop` | `tests/test_regressions.py` | job store off-loop execution |
| `test_api_health_responsive_during_train_job` | `tests/test_regressions.py` | `/health` during `/train` |
| `test_api_analyze_job_roundtrip` | `tests/test_regressions.py` | `/analyze` job round-trip |
| `test_api_rejects_unsupported_format` | `tests/test_regressions.py` | 415 envelope |

CLI tests in `tests/test_interfaces.py` (`test_cli_help_exposes_commands`, `test_cli_run_help_documents_options`, `test_cli_info_reports_version`, `test_cli_run_completes_on_tiny_dataset`, `test_cli_run_missing_file_exits_nonzero`) are preserved.

## 5. REST documentation (delete or update)

| File path | Reference | Action |
|---|---|---|
| `docs/guides/rest-api.md` | Entire file is the REST walkthrough | DELETE |
| `docs/getting-started.md` | "Using the REST API" section | UPDATE |
| `docs/examples.md` | "REST API Usage" section | UPDATE |
| `docs/troubleshooting.md` | "API Issues" section | UPDATE |
| `docs/limitations.md` | REST job-store / rate-limit / auth rows | UPDATE |
| `docs/index.md` | REST API feature card | UPDATE |
| `docs/guides/cli.md` | Docker/REST references | UPDATE |
| `docs/design-decisions.md` | "Why In-Memory Job Store?" (REST) | UPDATE |
| `docs/guides/simple-api.md` | FastAPI async-context mentions | UPDATE |
| `mkdocs.yml` | `REST API: guides/rest-api.md` nav entry | UPDATE |
| `docs/root_cause/*.md` | `Affected REST` + `interfaces/api/routes.py` references | UPDATE |
| `project_docs/API_Contracts.md` | §6 REST (FastAPI), import example | UPDATE |
| `project_docs/AI_QUALITY_GATE.md` | SDK-first/API-tests/wheel-smoke/Docker rules | UPDATE |
| `project_docs/Known_Issues.md` | BUG-03, ISSUE-08, KNOWN-001 | UPDATE |
| `project_docs/MASTER_FUNCTION_MATRIX.md` | §18 REST API, packaging entry | UPDATE |
| `project_docs/Roadmap.md` | REST roadmap items | UPDATE |
| `project_docs/project_state.json` | REST bug/roadmap/features entries | UPDATE |
| `project_docs/Project_Knowledge_Base.md` | REST API section + references | UPDATE |
| `project_docs/Architecture.md` | SDK-first + interfaces table | UPDATE |
| `project_docs/Testing.md`, `Release_Process.md`, `Decision_Log.md`, `Coding_Standards.md`, templates | REST references | UPDATE |
| `README.md` | FastAPI features/extras/quick-start/interfaces | UPDATE |
| `CHANGELOG.md` | FastAPI interface / `[api]` entries | UPDATE |
| `PROJECT_KNOWLEDGE_BASE.md` | REST API section + references | UPDATE |
| `ARCHITECTURE_AUDIT.md` | Interfaces table | UPDATE |
| `AUDIT_REPORT.md`, `IMPLEMENTATION_ROADMAP.md`, `PUBLIC_API_AUDIT.md`, `CODEBASE_INTEGRITY_REPORT.md`, `TASK_SUMMARY.md` | REST references | UPDATE |

## 6. Packaging / infrastructure (remove REST-only)

| File path | REST dependency/reference | Action |
|---|---|---|
| `pyproject.toml` | `api` extra (`fastapi`, `uvicorn`, `python-multipart`); `all` extra includes `api`; mypy override `phronesisml.interfaces.api.*` | UPDATE |
| `Dockerfile` | `CMD uvicorn phronesisml.interfaces.api.app:app`; `.[api,excel]`; healthcheck on `/health`; EXPOSE 8000 | DELETE (REST-server deployment) |
| `docker-compose.yml` | REST service on port 8000 with `/health` healthcheck | DELETE |
| `.dockerignore` | Only meaningful with the Dockerfile | DELETE |
| `.github/workflows/ci.yml` | `docker` + `docker-publish` jobs build the REST image and health-check `/health` | UPDATE (remove jobs) |
| `Makefile` | `docker` target runs the REST image | UPDATE (remove target) |
| `requirements.txt` | no `fastapi`/`uvicorn`/`python-multipart` present — no change needed | VERIFIED |

## 7. Runtime dependencies to remove from packaging

- `fastapi>=0.111,<1.0`
- `uvicorn>=0.30,<1.0`
- `python-multipart>=0.0.9`

`pydantic` stays (used by core configs, `WorkflowState`, and results). `httpx` in the `dev` extra was consumed only by the removed REST `TestClient` tests — removed.
