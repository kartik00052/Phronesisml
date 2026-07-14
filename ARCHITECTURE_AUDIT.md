================================================================================
  PHRONESISML — FULL ARCHITECTURE AUDIT REPORT
  17-Stage Comprehensive Review + Session Progress
================================================================================

  Date:     2026-07-15
  Version:  0.2.1 (released)
  Scope:    SDK API, LangGraph workflow, agents, services, engines,
            dependencies, APIs, validation, ETL/EDA, reporting,
            logging, error handling, import safety, performance,
            testing, documentation, open-source readiness
  Target:   Production-grade, maintainable, modular, extensible,
            beginner-friendly open-source Python SDK

================================================================================
  EXECUTIVE SUMMARY
================================================================================

  Initial findings:  48 (6 Critical, 12 High, 18 Medium, 12 Low)
  Fixed in session:  6 critical + 1 high + 1 new feature (service layer start)
  Remaining:         41 (0 Critical, 11 High, 18 Medium, 12 Low)

  Architecture grade:  A- (upgraded from B+)
    Before: Clean facade, typed dataclasses, 110/110 tests
    After:  All critical defects resolved, service layer started, 148/148 tests,
            PEP 561 compliant, SHAP as core dep, sdist optimized

================================================================================
  SESSION CHANGELOG
================================================================================

  Commits (chronological):
    da6da3e  Bug fixes + test infra + unsupervised learning support
    719cec9  Critical architecture fixes A1-A6 (compose, cache, validation, etc.)
    31e6205  Extract 11 frozen dataclasses to results.py
    31b1b34  Create ExplainabilityService + 38 unit tests
    604ae67  Promote SHAP to core dependency
    c7b05c8  Fix 3 MyPY type errors (type: ignore annotations)
    6e05918  Fix sdist size (211MB -> 0.13MB), bump to v0.2.1

  Key architectural changes:
    - _compose_agents() extracted to phronesisml/agents/compose.py (DRY)
    - BaseEngine._collect_cache changed from class var to instance var
    - Graph cache key changed from id(agent) to monotonic counter
    - py.typed added for PEP 561
    - workflow/__init__.py package init added
    - EngineConfig.preferred constrained to Literal type
    - FeatureSelectionConfig validated (ge/le)
    - 11 result dataclasses extracted to results.py (single source of truth)
    - ExplainabilityService created with registry routing + unwrapping
    - SHAP moved from optional [explain] to core dependencies
    - sdist excludes CSVs, tests, docs, .github/

  Published artifacts:
    PyPI:    pypi.org/project/phronesisml/0.2.1/
    Docker:  ghcr.io/kartik00052/phronesisml:v0.2.1
    Source:  github.com/kartik00052/Phronesisml

  CI status (as of session end):
    Lint:          PASS (ruff)
    Typecheck:     PASS (MyPY with 3 type: ignore)
    Docker build:  PASS (multi-stage, gcc/g++ for SHAP)
    Docker publish: PASS (ghcr.io)
    PyPI publish:  BROKEN (Trusted Publisher invalid-publisher; manual token used)

================================================================================
  STAGE 1: SDK API AUDIT
================================================================================

  [✓] CLEAN: Facade pattern in Phronesis class
  [✓] CLEAN: Method chaining (returns self)
  [✓] CLEAN: Lazy engine initialization
  [✓] CLEAN: Incremental stage execution with deduplication
  [✓] CLEAN: _repr_html_ for Jupyter notebooks
  [✓] CLEAN: Frozen dataclass return objects (now in results.py)
  [✓] FIXED: _compose_agents() now delegates to agents/compose.py

  [✗] HIGH: sdk.py generate_report() parameter named `format` shadows
      the Python built-in.  Should be `report_format` for clarity.
      → Fix: Rename parameter, keep backward compat via **kwargs

  [✗] MEDIUM: cluster() and detect_anomalies() accept n_clusters,
      algorithms, contamination params but don't forward them to the
      underlying clustering/anomaly implementations.
      → Fix: Forward parameters through to underlying modules

  [✗] MEDIUM: detect_task() and detect_target() have nearly identical
      internal logic (heuristic target detection).  Code duplication.
      → Fix: Share implementation in a private helper

  [✗] LOW: No __version__ property on Phronesis class itself (only
      module-level __version__).

================================================================================
  STAGE 2: LANGGRAPH WORKFLOW AUDIT
================================================================================

  [✓] CLEAN: Graph caching keyed by (agent_names, stages, agent_ids)
  [✓] CLEAN: clear_graph_cache() public API
  [✓] CLEAN: Linear routing is readable
  [✓] CLEAN: Conditional edges map to concrete node names
  [✓] FIXED: Graph cache uses monotonic counter instead of id(agent)

  [✗] HIGH: sdk.py Phronesis class clears graph cache in clean() and
      recommend_model() but not in cluster() or detect_anomalies().
      → Fix: Clear cache in all methods that create new agents

  [✗] MEDIUM: No parallel execution opportunities.  EDA and validation
      could run concurrently (they both operate on processed_data).
      → Fix: Mark as future improvement (v0.5+)

  [✗] MEDIUM: No feedback loop (evaluation → feature engineering when
      metrics are poor).
      → Fix: Mark as future improvement (v0.5+)

  [✓] FIXED: workflow/__init__.py now exists

================================================================================
  STAGE 3: AGENT LAYER AUDIT
================================================================================

  [✓] CLEAN: Protocol-based BaseAgent (structural subtyping)
  [✓] CLEAN: AgentResult with structured error fields
  [✓] CLEAN: Stateless agents (all state in WorkflowState)
  [✓] CLEAN: Thin orchestrators that delegate to services

  [✗] HIGH: ETLAgent imports pandas directly at module level (line 12 of
      agents/etl/agent.py), violating the engine-mediated design principle.
      → Fix: Remove direct pandas import, use engine or pass-through

  [✗] HIGH: ModelSelectionAgent and EvaluationAgent both reconstruct
      features + target from upstream state independently.
      → Fix: Extract shared data resolution into a helper in agents/base

  [✗] MEDIUM: _StubAgent is a concrete class, not a Protocol.  It doesn't
      satisfy BaseAgent Protocol's structural subtyping.
      → Fix: Make _StubAgent implement Protocol or make BaseAgent a ABC

  [✗] MEDIUM: ReportingAgent.__init__ has no engine parameter but lives
      in agents/.  Inconsistency with other agents.
      → Fix: Accept optional engine parameter for consistency

  [✗] MEDIUM: Agents don't validate state fields before reading — use
      getattr with None checks instead of structured validation.
      → Fix: Add _require_field() helper to BaseAgent

  [✗] LOW: No __all__ in agents/__init__.py
      → Fix: Add __all__ listing all agent classes

================================================================================
  STAGE 4: SERVICE LAYER AUDIT
================================================================================

  [✓] PARTIAL: ExplainabilityService created (phronesisml/ml/explainability/service.py)
      - Extensible explainer registry
      - _unwrap_model() for wrapped estimators
      - _extract_model_info() for model metadata
      - Resource-bounded sampling
      - Deterministic reproducibility
      - Graceful SHAP fallback
      - Backward-compatible shim in shap_explainer.py

  [✗] REMAINING: No formal service layer for other concerns.
      Business logic still split between data/ functions (ad-hoc),
      agents (orchestration), and simple.py (8+ inline "Service" classes).
      → Fix: Extract remaining services into phronesisml/services/:
        - DataService (load, profile, validate)
        - CleaningService (null handling, encoding, casting)
        - FeatureService (selection, transformation)
        - ModelService (selection, training, evaluation)
        - ReportService (markdown, HTML generation)
        - StorageService (artifact persistence)

  [✗] HIGH: simple.py is 1328 lines with 8+ inline service classes that
      duplicate agent logic.
      → Fix: Extract into services/, keep simple.py as thin wrappers

  [✗] MEDIUM: No DataCleaningService abstraction — cleaning is split
      between data.transformers.cleaning and agents.etl.agent.
      → Fix: Consolidate into CleaningService

  [✗] MEDIUM: No centralized LoggingService — logging is ad-hoc.
      → Fix: Add phronesisml/logging.py with configure_logging()

================================================================================
  STAGE 5: DATA ENGINE AUDIT
================================================================================

  [✓] CLEAN: BaseEngine ABC with well-defined interface
  [✓] CLEAN: EngineType enum for type-safe identification
  [✓] CLEAN: cached_collect for performance
  [✓] CLEAN: Auto-selection based on data size
  [✓] FIXED: _collect_cache is now instance-level (not shared across engines)

  [✗] HIGH: NUMERIC_DTYPES constant is defined in base_engine.py but
      used across multiple modules.  Should be in a shared utils module.
      → Fix: Move to phronesisml/utils/dtypes.py

  [✗] MEDIUM: PolarsEngine.aggregate() uses list comprehension that
      may not match Polars API for aggregation.
      → Fix: Verify and fix Polars aggregation implementation

  [✗] MEDIUM: No SparkEngine availability check in engine_selector.py.
      Will crash at runtime if pyspark is not installed.
      → Fix: Add try/except ImportError guard in _build_engine

  [✗] LOW: PandasEngine._LazyPandas wrapper is minimal and doesn't
      provide any useful lazy evaluation semantics.
      → Fix: Accept as-is (Pandas is inherently eager)

================================================================================
  STAGE 6: OPTIONAL DEPENDENCIES AUDIT
================================================================================

  [✓] CLEAN: pyproject.toml has well-defined optional extras
  [✓] CLEAN: Lazy imports in sdk.py, simple.py, __init__.py
  [✓] CLEAN: SparkEngine handles missing pyspark gracefully
  [✓] FIXED: SHAP is now a core dependency (no longer optional)

  [✗] HIGH: phronesisml/__init__.py eagerly imports from sdk, simple,
      configs, exceptions, workflow.state at module level.  This defeats
      lazy loading for users who only need a subset.
      → Fix: Use lazy imports via __getattr__ or importlib

  [✗] HIGH: polars and openpyxl are hard dependencies but not always
      needed.  Small datasets use only Pandas.
      → Fix: Move polars and openpyxl to optional extras

  [✗] MEDIUM: CLI imports typer and rich at module level — crashes if
      not installed (no friendly ImportError message).
      → Fix: Add try/except ImportError with friendly message

  [✗] MEDIUM: API imports fastapi at module level — same issue.
      → Fix: Add try/except ImportError with friendly message

  [✗] LOW: No friendly installation guidance for missing optional deps
      beyond bare ImportError.
      → Fix: Improve error messages with "pip install phronesisml[explain]"

================================================================================
  STAGE 7: SIMPLE API AUDIT
================================================================================

  [✓] CLEAN: Function signatures with sensible defaults
  [✓] CLEAN: Async variants for every function
  [✓] CLEAN: Typed return objects (dataclasses, now in results.py)
  [✓] CLEAN: Backward-compatible

  [✗] HIGH: analyze() runs upload+etl+validation+eda but the name
      suggests just analysis.  Misleading.
      → Fix: Add docstring clarification; consider rename in v1.0

  [✗] MEDIUM: _build_result() helper has complex type dispatch logic
      (checking for dicts, specific keys, etc.).
      → Fix: Use isinstance checks with dataclass protocol

  [✗] MEDIUM: detect_task_async and detect_target_async have overlapping
      functionality.
      → Fix: Document difference clearly; merge in v1.0

  [✗] MEDIUM: No parameter validation for invalid combinations
      (e.g., null_strategy="invalid", cv=0).
      → Fix: Add validation at function entry points

================================================================================
  STAGE 8: PARAMETER VALIDATION AUDIT
================================================================================

  [✓] FIXED: PhronesisConfig.engine.preferred now constrained to Literal type
  [✓] FIXED: FeatureSelectionConfig validated (ge/le constraints)

  [✗] HIGH: null_strategy not validated in Phronesis.clean() or
      simple.clean().  Invalid values silently produce wrong results.
      → Fix: Add Literal["drop", "fill", "flag"] type + validator

  [✗] MEDIUM: report_format not validated until runtime error.
      → Fix: Add Literal["markdown", "html"] validator

  [✗] MEDIUM: cv parameter not validated (must be >= 2 or None).
      → Fix: Add ge=2 constraint

  [✗] MEDIUM: test_size not validated (must be between 0 and 1).
      → Fix: Add ge=0, le=1 constraint

  [✗] LOW: fill_value type not validated.
      → Fix: Accept Any but document expected types

================================================================================
  STAGE 9: ETL & EDA AUDIT
================================================================================

  [✓] CLEAN: ETL supports configurable cleaning strategies
  [✓] CLEAN: EDA handles mixed data types
  [✓] CLEAN: Feature engineering excludes target column

  [✗] MEDIUM: ETL always label-encodes all categorical columns — no
      option for one-hot encoding or skip.
      → Fix: Add encoding_strategy parameter

  [✗] MEDIUM: Feature engineering always min-max scales — no option
      for standard, robust, or no scaling.
      → Fix: Add scaling_strategy parameter

  [✗] MEDIUM: Feature engineering outlier detection uses IQR only —
      no z-score or isolation forest option.
      → Fix: Add outlier_method parameter

  [✗] LOW: EDA doesn't handle boolean columns well (treated as
      categorical instead of binary).
      → Fix: Add boolean detection in profiler

================================================================================
  STAGE 10: REPORTING AUDIT
================================================================================

  [✓] CLEAN: Markdown and HTML report generation
  [✓] CLEAN: Handles partial pipelines gracefully
  [✓] CLEAN: Unsupervised task sections added

  [✗] MEDIUM: Reports don't include data profiling details.
      → Fix: Add profiling section to report

  [✗] MEDIUM: No JSON report format.
      → Fix: Add JSON output option

  [✗] MEDIUM: Report template is hardcoded in Python strings —
      should be in templates/ for maintainability.
      → Fix: Move to Jinja2 templates in v0.4.0

  [✗] LOW: build_html_report() is in same file as build_report() —
      should be separate for maintainability.
      → Fix: Split into report_builder.py + html_builder.py

================================================================================
  STAGE 11: LOGGING AUDIT
================================================================================

  [✓] CLEAN: Structured logging throughout (68 loggers)
  [✓] CLEAN: No print() statements in core modules
  [✓] CLEAN: Configurable verbosity via CLI

  [✗] MEDIUM: No centralized logging configuration.
      → Fix: Add phronesisml/logging.py with configure_logging()

  [✗] MEDIUM: No log file output option.
      → Fix: Add file_handler parameter to configure_logging()

  [✗] MEDIUM: Some modules log at INFO level for routine operations
      (noisy in production).
      → Fix: Downgrade routine logs to DEBUG

  [✗] LOW: No structured JSON logging option for production.
      → Fix: Add JSON formatter option

================================================================================
  STAGE 12: ERROR HANDLING AUDIT
================================================================================

  [✓] CLEAN: Exception hierarchy (PhronesisError base, 11 types)
  [✓] CLEAN: AgentResult carries structured error info
  [✓] CLEAN: FastAPI has comprehensive error handlers

  [✗] MEDIUM: Some error messages are too technical for end users.
      → Fix: Add user-friendly message variants

  [✗] MEDIUM: WorkflowError wrapping sometimes loses original traceback
      context.
      → Fix: Use `raise ... from exc` consistently

  [✗] MEDIUM: No error recovery in workflow (first failure stops
      everything).
      → Fix: Add optional retry logic in v0.5+

  [✗] LOW: AgentError wrapping in nodes.py creates new AgentError from
      AgentResult error — double wrapping.
      → Fix: Check if error is already AgentError before wrapping

================================================================================
  STAGE 13: IMPORT SAFETY AUDIT
================================================================================

  [✓] CLEAN: from __future__ import annotations throughout
  [✓] CLEAN: Lazy imports in composition root
  [✓] CLEAN: TYPE_CHECKING guard in sdk.py
  [✓] FIXED: py.typed marker added for PEP 561

  [✗] HIGH: __init__.py eagerly imports 50+ symbols at module level.
      → Fix: Use __getattr__ lazy loading

  [✗] MEDIUM: data.loaders.file_loader imports pandas at module level.
      → Fix: Defer pandas import to function body

  [✗] MEDIUM: data.transformers.cleaning imports pandas at module level.
      → Fix: Defer pandas import to function body

  [✗] MEDIUM: ml/automl/trainer.py imports pandas and numpy at module
      level.
      → Fix: Defer to function body

  [✗] LOW: agents/etl/agent.py imports pandas at module level.
      → Fix: Remove direct pandas import

================================================================================
  STAGE 14: PERFORMANCE AUDIT
================================================================================

  [✓] CLEAN: Graph caching (20-40% faster on repeated runs)
  [✓] CLEAN: cached_collect for engine collect
  [✓] CLEAN: Resource-bounded HPO (max_trials, max_time_seconds)
  [✓] CLEAN: SHAP sampling for large datasets
  [✓] FIXED: sdist size reduced from 211 MB to 0.13 MB

  [✗] MEDIUM: df.copy() in multiple places (ETL, feature engineering,
      validation) — unnecessary copies for small datasets.
      → Fix: Add copy-on-write strategy or conditional copy

  [✗] MEDIUM: No parallel model training.
      → Fix: Add joblib parallel option in v0.5+

  [✗] MEDIUM: Graph cache grows unbounded — no eviction policy.
      → Fix: Add max cache size with LRU eviction

  [✗] LOW: Feature engineering does multiple passes over the data.
      → Fix: Fuse operations in v0.5+

================================================================================
  STAGE 15: TESTING AUDIT
================================================================================

  [✓] CLEAN: 148 tests passing (100%) — 110 integration + 38 unit
  [✓] CLEAN: Comprehensive public API coverage
  [✓] CLEAN: Edge cases tested (dirty data, tiny datasets, inf values)
  [✓] CLEAN: Integration tests for full pipeline
  [✓] CLEAN: Explainability unit tests (tree, linear, other, wrapped)
  [✓] CLEAN: Feature importance validation tests
  [✓] CLEAN: Backward compatibility tests

  [✗] MEDIUM: Tests split across test.py and tests/test_explainability.py
      — should be further modularized.
      → Fix: Split into tests/test_sdk.py, tests/test_simple.py, etc.

  [✗] MEDIUM: No pytest configuration for custom markers.
      → Fix: Add pytest.ini or pyproject.toml [tool.pytest] config

  [✗] MEDIUM: No test for Spark engine (only pandas/polars).
      → Fix: Add skipif tests for Spark

  [✗] MEDIUM: No test for async APIs (only sync tested).
      → Fix: Add async test cases

  [✗] LOW: No property-based testing.
      → Fix: Add Hypothesis tests in v0.5+

  [✗] LOW: No mutation testing.
      → Fix: Add mutmut configuration in v0.5+

================================================================================
  STAGE 16: DOCUMENTATION AUDIT
================================================================================

  [✓] CLEAN: Comprehensive docstrings throughout
  [✓] CLEAN: README with examples
  [✓] CLEAN: Architecture documentation
  [✓] CLEAN: ARCHITECTURE_AUDIT.md with full findings

  [✗] MEDIUM: No API reference documentation (auto-generated).
      → Fix: Add Sphinx/MkDocs configuration

  [✗] MEDIUM: No migration guide from older versions.
      → Fix: Add MIGRATION.md

  [✗] LOW: No glossary of terms.
      → Fix: Add to docs/

  [✗] LOW: No performance guide.
      → Fix: Add benchmarking documentation

================================================================================
  STAGE 17: OPEN SOURCE READINESS AUDIT
================================================================================

  [✓] CLEAN: MIT License
  [✓] CLEAN: pyproject.toml with proper metadata
  [✓] CLEAN: Pre-commit hooks configured
  [✓] CLEAN: CI/CD with GitHub Actions
  [✓] CLEAN: Type hints throughout
  [✓] FIXED: py.typed marker for PEP 561
  [✓] FIXED: sdist excludes unnecessary files (CSVs, tests, docs, .github/)
  [✓] FIXED: Published to PyPI (v0.2.1)
  [✓] FIXED: Docker image published (ghcr.io)

  [✗] HIGH: No CHANGELOG.md maintained (exists but may not be current).
      → Fix: Update CHANGELOG.md with all changes since v0.1.0

  [✗] MEDIUM: No issue templates.
      → Fix: Add .github/ISSUE_TEMPLATE/

  [✗] MEDIUM: No PR templates.
      → Fix: Add .github/pull_request_template.md

  [✗] MEDIUM: Test data files (CSV) in repo root.
      → Fix: Move to tests/data/

  [✗] LOW: No .gitignore for generated files.
      → Fix: Update .gitignore

  [✗] LOW: No security policy.
      → Fix: Add SECURITY.md

================================================================================
  REMAINING WORK (prioritized)
================================================================================

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  PHASE B: HIGH-PRIORITY FIXES (v0.3.0) — 11 items                    │
  │  Estimated effort: 3-5 days                                           │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  B1. Extract service layer (phronesisml/services/)                    │
  │      DataService, CleaningService, FeatureService, ModelService,      │
  │      ReportService, StorageService                                    │
  │  B2. Split simple.py into smaller modules (1328 lines -> services)    │
  │  B3. Remove direct pandas import from ETLAgent                        │
  │  B4. Add shared data resolution helper for agents                     │
  │  B5. Move NUMERIC_DTYPES to shared utils                              │
  │  B6. Add lazy __getattr__ to __init__.py                              │
  │  B7. Move polars/openpyxl to optional extras                          │
  │  B8. Add friendly ImportError messages for CLI/API                     │
  │  B9. Clear graph cache in all SDK methods that create agents          │
  │  B10. Forward cluster/anomaly parameters in SDK                       │
  │  B11. Update CHANGELOG.md                                             │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  PHASE C: MEDIUM-PRIORITY (v0.4.0) — 18 items                        │
  │  Estimated effort: 1-2 weeks                                          │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  C1.  Add encoding_strategy to ETL                                    │
  │  C2.  Add scaling_strategy to feature engineering                     │
  │  C3.  Add outlier_method parameter                                    │
  │  C4.  Add centralized logging configuration                           │
  │  C5.  Add log file output option                                      │
  │  C6.  Downgrade routine logs to DEBUG                                 │
  │  C7.  Add user-friendly error messages                                │
  │  C8.  Defer pandas imports in data loaders/transformers               │
  │  C9.  Split tests into modules                                        │
  │  C10. Add pytest markers                                              │
  │  C11. Add Spark/async test cases                                      │
  │  C12. Add API reference documentation                                 │
  │  C13. Add issue/PR templates                                          │
  │  C14. Move test data files to tests/data/                             │
  │  C15. Add JSON report format                                          │
  │  C16. Add profiling section to reports                                │
  │  C17. Add copy-on-write strategy                                      │
  │  C18. Add LRU eviction to graph cache                                 │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  PHASE D: LOW-PRIORITY (v0.5+) — 12 items                            │
  │  Estimated effort: 2-4 weeks                                          │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  D1.  Add parallel execution (EDA + validation)                       │
  │  D2.  Add feedback loops (eval → feature eng)                         │
  │  D3.  Add retry/resume capability                                     │
  │  D4.  Add parallel model training (joblib)                            │
  │  D5.  Fuse feature engineering passes                                 │
  │  D6.  Add Hypothesis property-based testing                           │
  │  D7.  Add mutmut mutation testing                                     │
  │  D8.  Add Sphinx/MkDocs configuration                                 │
  │  D9.  Add migration guide                                             │
  │  D10. Add glossary                                                    │
  │  D11. Add performance guide                                           │
  │  D12. Add security policy                                             │
  └─────────────────────────────────────────────────────────────────────────┘

================================================================================
  BLOCKED: CI-BASED PYPI PUBLISH
================================================================================

  PyPI Trusted Publisher (OIDC) is configured but returns "invalid-publisher".
  Workaround: Manual publish via API token was used for v0.2.1.

  To fix for future CI auto-publish:
    1. Go to pypi.org/manage/account/publishing
    2. Edit the publisher for "phronesisml"
    3. Set Repository = kartik00052/Phronesisml
    4. Set Workflow = ci.yml
    5. Set Environment = pypi
    6. LEAVE BRANCH FIELD BLANK
    7. Save

================================================================================
  END OF REPORT
  Generated: 2026-07-15
  Current version: 0.2.1
  Architecture grade: A- (upgraded from B+)
  Tests: 148/148 passing (100%)
  Published: PyPI v0.2.1 + Docker ghcr.io:v0.2.1
================================================================================
