<p align="center">
  <img src="assets/banner.png" alt="AetherML — Open-Source Agentic Machine Learning Framework" width="100%"/>
</p>

**A transparent, inspectable alternative to AutoML — the ML lifecycle modeled as a graph of cooperating agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)
![GitHub stars](https://img.shields.io/github/stars/kartik00052/AetherML?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/kartik00052/AetherML?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/kartik00052/AetherML?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/kartik00052/AetherML?style=flat-square)

**Quick Links:** [Why AetherML](#why-aetherml) · [Installation](#installation) · [Quick Start](#quick-start) · [Architecture](#architecture-overview) · [Contributing](#contributing) · [FAQ](#faq)

---

## Table of Contents

1. [Why AetherML](#why-aetherml)
2. [Key Features](#key-features)
3. [Architecture Overview](#architecture-overview)
4. [How It Works](#how-it-works)
5. [Technology Stack](#technology-stack)
6. [Installation](#installation)
7. [Quick Start](#quick-start)
8. [Examples](#examples)
9. [SDK Interfaces](#sdk-interfaces)
10. [Project Structure](#project-structure)
11. [Roadmap](#roadmap)
12. [Documentation](#documentation)
13. [Contributing](#contributing)
14. [FAQ](#faq)
15. [License](#license)
16. [Community](#community)
17. [Acknowledgements](#acknowledgements)

---

## Why AetherML

Most machine learning work today happens at one of two extremes.

**Notebooks** are flexible but fragile — validation, feature engineering, and reporting logic end up interleaved in an unordered sequence of cells, with no enforced structure and no clean boundary between exploration and production.

**AutoML tools** sit at the other extreme: upload a dataset, wait, and receive a model with little insight into *why* a particular transformation, encoding, or algorithm was chosen. They optimize for a leaderboard metric, not for an engineer's understanding of the pipeline that produced it.

AetherML occupies the space in between. It's a **Python SDK** that models the ML lifecycle — validation, profiling, ETL, EDA, feature engineering, target detection, model recommendation, training, evaluation, explainability, and reporting — as a graph of cooperating agents, each with a well-defined responsibility and a well-defined contract with the rest of the system.

| | Notebooks | AutoML Tools | AetherML |
|---|---|---|---|
| Structure | Ad hoc, cell-by-cell | Fixed, opaque | Modular agents on a typed `WorkflowState` |
| Transparency | High, but unorganized | Low — a black box | High — every decision is inspectable |
| Overridable decisions | N/A (you wrote it) | Rarely | Yes — imputation, encoding, model family |
| Reusability across datasets | Low | Low | High — same pipeline, swap the data |
| Production-ready | No | Partially | Yes — versioned artifacts, architecture tests |

> **In short:** AetherML recommends; it does not obscure. Every stage of the pipeline is a discrete, testable, reusable unit of code operating on a shared, typed `WorkflowState`.

AetherML is **SDK-first** — the CLI, the FastAPI service, and any future GUI are thin clients built on the same SDK a data scientist would `import` directly into their own scripts. There is exactly one source of truth for ML logic.

[↑ Back to top](#table-of-contents)

---

## Key Features

| Feature | Description | Status |
|---|---|---|
| **Multi-Agent Workflow** | Each pipeline stage is implemented as an independent agent with a single responsibility | Implemented |
| **LangGraph Orchestration** | Agents are nodes in a directed graph; LangGraph manages state passing, conditional edges, and retries | Implemented |
| **Automatic Engine Selection** | Dataset size and shape determine whether Pandas, Polars, or PySpark is used | Implemented |
| **ETL** | Declarative extraction, cleaning, and transformation into a canonical internal representation | Implemented |
| **Validation** | Schema, type, and quality validation before any downstream processing occurs | Implemented |
| **Exploratory Data Analysis** | Automated statistical profiling and structured dataset summaries | Implemented |
| **Feature Engineering** | Automated and configurable transformation, encoding, and derivation of features | Implemented |
| **Target Detection** | Heuristic, overridable identification of the prediction target and task type | Implemented |
| **Model Recommendation** | Rule- and metric-driven suggestion of candidate model families | Implemented |
| **Explainability** | Post-training feature importance and model-behavior summaries | Implemented |
| **Reporting** | Structured, versionable output artifacts for every stage of a run | Implemented |
| **Modular Architecture** | Clear separation between agents, services, engines, and interfaces | Implemented |
| **FastAPI Interface** | REST API with file upload, background jobs, and OpenAPI docs (`pip install aetherml[api]`) | Implemented |
| **Offline-First Design** | Core pipeline stages run without network access or hosted services | Implemented |
| **SDK-First Philosophy** | Every interface (CLI, API, GUI) is a client of the SDK — never a place where logic lives | Implemented |
| **Plugin System** | Extension points for custom agents, models, engines, and storage backends | Planned |

[↑ Back to top](#table-of-contents)

---

## Architecture Overview

AetherML is organized into layers. Each layer depends only on the layer(s) beneath it — never on layers above it, and never sideways into a sibling's internals.

```
                     ┌────────────────────────┐
                     │        Python SDK        │   ← Public entry point (aetherml.SDK)
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │     LangGraph Workflow    │   ← Orchestrates agent execution order
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │          Agents           │   ← One responsibility per agent
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │         Services          │   ← Reusable domain logic, engine-agnostic
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │       Data Engines         │   ← Pandas / Polars / PySpark implementations
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   Reports / Storage        │   ← Persisted artifacts and run outputs
                     └────────────────────────┘
```

| Layer | Responsibility | Depends On |
|---|---|---|
| **Python SDK** | Single public entry point (`SDK` / `AetherML` class); hides internal orchestration | — |
| **LangGraph Workflow** | Defines the pipeline as a graph of nodes and edges; owns the shared `WorkflowState` | Called by the SDK |
| **Agents** | One pipeline responsibility each; read/write `WorkflowState` | Invoked as graph nodes |
| **Services** | Stateless, reusable domain logic; engine-agnostic | Called by agents |
| **Data Engines** | Concrete `DataEngine` implementations (Pandas, Polars, PySpark) | Called by services |
| **Reports / Storage** | Persists run artifacts — local filesystem by default | Written to by agents/services |

### Design Principles

| Principle | What It Means in AetherML |
|---|---|
| SDK-first | The SDK is the single source of truth for ML logic; CLI/API/GUI are clients, not implementers |
| Offline-first | Core pipeline stages run without network access; storage defaults to local disk |
| Deterministic ML | Same input + config → same output; randomness is always explicitly seeded |
| Dependency Injection | Agents/services receive dependencies rather than constructing them — enables testing with fakes |
| Clean Architecture | Layers depend inward — see the diagram above |
| Single Responsibility & Interface Segregation | One agent, one job; narrow, focused contracts in `interfaces/` |
| Strategy Pattern | Used for interchangeable behaviors like data engine selection |
| Factory Pattern | Used for engine instantiation (`engines/factory.py`) and, later, plugin instantiation |
| Composition over Inheritance | Agents compose services rather than inheriting through deep class hierarchies |

### Data Engine Abstraction

No single dataframe library is optimal across every dataset size AetherML needs to handle, so the framework supports three interchangeable engines behind one interface:

| Engine | Best For | Why |
|---|---|---|
| **Pandas** | Small-to-medium, in-memory datasets | Ubiquitous, well understood, ideal when data comfortably fits in memory |
| **Polars** | Larger single-machine workloads | Rust-based, multi-threaded query engine — significantly faster than Pandas at scale |
| **PySpark** | Distributed / larger-than-memory datasets | Industry standard once data exceeds what one machine can hold |

`ProfilingAgent` inspects row count, column count, and estimated memory footprint, then hands that off to `engines/factory.py`, which selects an engine according to configurable thresholds in `configs/engine_config.py`. Every engine implements the same `DataEngine` interface defined in `engines/base.py`, so agents and services never call Pandas, Polars, or PySpark directly — they call `DataEngine` methods, and the concrete implementation handles the translation. Users can also force a specific engine explicitly, overriding automatic selection.

This boundary is what lets AetherML add a new engine (say, DuckDB) later with zero changes to `agents/`, `services/`, `ml/`, `cli/`, or the SDK's public API — and lets most of the test suite run against a lightweight in-memory fake `DataEngine`, without Polars or PySpark installed.

[↑ Back to top](#table-of-contents)

---

## How It Works

AetherML models the full ML lifecycle as a linear pipeline with conditional branches. Each stage below is a LangGraph node backed by one or more agents.

```
 Dataset Upload
       │
       ▼
   Validation          → Schema/type/quality checks; halts on critical errors
       │
       ▼
   Profiling           → Shape, dtypes, missingness — informs engine selection
       │
       ▼
     ETL                → Cleaning, normalization, canonicalization
       │
       ▼
     EDA                → Distributions, correlations, outlier signals
       │
       ▼
Feature Engineering     → Encoding, scaling, derived features
       │
       ▼
Target Detection        → Identify prediction target and task type
       │
       ▼
Model Recommendation    → Candidate model families ranked by dataset fit
       │
       ▼
   Training              → Fit selected/recommended model(s)
       │
       ▼
   Evaluation            → Metrics against held-out data
       │
       ▼
Explainability          → Feature importance, model behavior summary
       │
       ▼
   Reporting              → Persist structured run artifacts
```

### Agent Responsibilities

Every agent implements the same `BaseAgent` interface and talks to the pipeline exclusively through the shared `WorkflowState`. No agent calls another agent directly — sequencing is owned entirely by the `workflow/` graph.

| Agent | Responsibility | Reads | Writes | Consumed By |
|---|---|---|---|---|
| `ValidationAgent` | Schema, type, quality checks | Raw dataset | Validation report, pass/fail | Profiling, Reporting |
| `ProfilingAgent` | Structural profiling | Validated dataset | Profile summary | Engine factory, ETL |
| `ETLAgent` | Cleaning, normalization | Validated dataset, profile | Canonical dataset | EDA, Feature Engineering |
| `EDAAgent` | Statistical analysis | Canonical dataset | EDA summary | Feature Engineering, Reporting |
| `FeatureEngineeringAgent` | Encoding, scaling, derived features | Canonical dataset, EDA summary | Engineered feature set | Target Detection |
| `TargetDetectionAgent` | Target column & task type | Engineered feature set | Target, task type | Model Recommendation |
| `ModelRecommendationAgent` | Rank candidate models | Feature set, task type | Ranked shortlist | Training |
| `TrainingAgent` | Fit model(s) | Feature set, target, model choice | Trained model artifact | Evaluation |
| `EvaluationAgent` | Compute metrics | Trained model, held-out split | Evaluation metrics | Explainability, Reporting |
| `ExplainabilityAgent` | Feature importance & behavior | Trained model, feature set | Explainability summary | Reporting |
| `ReportingAgent` | Aggregate everything into a report | All prior state | Final report artifact | Storage |

This table describes contracts, not implementation — full agent-by-agent documentation lives in `docs/architecture/agents/`.

[↑ Back to top](#table-of-contents)

---

## Technology Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-CD792C?style=for-the-badge&logo=polars&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)

| Technology | Role | Why It Was Chosen |
|---|---|---|
| Python | Core implementation language | Mature ML/data ecosystem; type hints support the interface-driven design |
| LangGraph | Workflow orchestration | Purpose-built for stateful, graph-shaped workflows with conditional branching |
| Pandas | Default engine, small-to-medium data | Ubiquitous, ideal for datasets that fit comfortably in memory |
| Polars | Engine for larger single-machine workloads | Rust-based, multi-threaded — significantly faster than Pandas at scale |
| PySpark | Engine for distributed/large-scale data | Industry standard once data exceeds single-machine memory |
| scikit-learn | Underlying model implementations | Battle-tested, consistent API surface |
| Pydantic | Config & API schema validation | Enforces typed, validated configuration over untyped dicts |
| pytest | Test runner | De facto standard; strong fixture and plugin ecosystem |
| FastAPI | HTTP interface layer | Async-first, automatic OpenAPI generation, thin enough to stay logic-free |

[↑ Back to top](#table-of-contents)

---

## Installation

**Requirements:** Python 3.11+

### Standard

```bash
pip install aetherml
```

### With optional extras

```bash
pip install aetherml[all]       # everything
pip install aetherml[api]       # FastAPI endpoints
pip install aetherml[cli]       # CLI commands
pip install aetherml[parquet]   # .parquet support
pip install aetherml[explain]   # SHAP explanations
```

### From source (for contributors)

```bash
git clone https://github.com/kartik00052/AetherML.git
cd AetherML

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### Available extras

| Extra | What it adds | Install |
|---|---|---|
| `cli` | Typer CLI commands | `pip install aetherml[cli]` |
| `api` | FastAPI REST endpoints | `pip install aetherml[api]` |
| `parquet` | .parquet/.pq file support | `pip install aetherml[parquet]` |
| `excel` | .xlsx/.xls file support | `pip install aetherml[excel]` |
| `explain` | SHAP model explanations | `pip install aetherml[explain]` |
| `boost` | XGBoost models | `pip install aetherml[boost]` |
| `mlflow` | MLflow experiment tracking | `pip install aetherml[mlflow]` |
| `spark` | PySpark engine for large datasets | `pip install aetherml[spark]` |
| `all` | Everything above | `pip install aetherml[all]` |
| `dev` | Testing, linting, formatting | `pip install aetherml[dev]` |

[↑ Back to top](#table-of-contents)

---

## Quick Start

```python
from aetherml import AetherML

ml = AetherML("data/customers.csv")
ml.run()             # upload → validation → ETL → EDA → … → storage
print(ml.report())
```

```text
$ python quickstart.py
[UploadAgent]        Loaded data/customers.csv — 10,000 rows, 14 columns
[ValidationAgent]    Schema OK · 0 critical issues
[ProfilingAgent]     Selected engine: pandas (dataset fits in memory)
[ETLAgent]           Cleaned & normalized — 3 duplicate rows removed
[EDAAgent]           Profiled 14 columns — 2 strong correlations found
[FeatureEngAgent]    Engineered 21 features from 14 raw columns
[TargetDetectAgent]  Detected target: "churned" (binary classification)
[ModelRecAgent]      Recommended: GradientBoostingClassifier
[TrainingAgent]      Trained in 4.2s — AUC 0.891
[EvaluationAgent]    Precision 0.84 · Recall 0.79 · F1 0.81
[ExplainAgent]       Top feature: "days_since_last_login" (0.31 importance)
[ReportingAgent]     Report written to reports/run_2026-07-13.md
```

*Sample output — actual metrics vary by dataset.*

[↑ Back to top](#table-of-contents)

---

## Examples

### Incremental Usage

Run only the stages you need, with overrides where it matters:

```python
from aetherml import AetherML

ml = AetherML("data/customers.csv")
ml.load()
print(ml.summary())              # lightweight stats — no ML yet

ml.clean(null_strategy="fill")   # override the default null strategy
ml.validate()
ml.eda()

ml.detect_target()
result = ml.train()              # equivalent to ml.recommend_model()
print(f"Best model: {result.model_type} ({result.score:.4f})")

print(ml.evaluate())
print(ml.explain())
```

### Simple API (One-Liner Functions)

For scripts that just need one function call per stage:

```python
from aetherml import analyze, train

profile = analyze("data/customers.csv")
print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")

result = train("data/customers.csv")
print(f"Best model: {result.best_model_type} ({result.best_score:.4f})")
```

<details>
<summary><strong>Individual pipeline stages</strong></summary>

```python
from aetherml import clean, validate, detect_target, engineer, select_model, explain, report

result = clean("data/customers.csv", null_strategy="fill")

result = validate("data/customers.csv")
if not result.passed:
    for issue in result.issues:
        print(issue)

result = detect_target("data/customers.csv")
print(f"Target: {result.column} ({result.task_type})")

result = engineer("data/customers.csv", variance_threshold=0.005)
result = select_model("data/customers.csv")

result = explain("data/customers.csv")
for feature, importance in result.feature_importance.items():
    print(f"  {feature}: {importance:.4f}")

print(report("data/customers.csv"))
```

</details>

### Async Variants

Every function has an `_async` counterpart for FastAPI, Jupyter's async mode, or other async contexts:

```python
from aetherml import analyze_async, train_async
import asyncio

async def main():
    profile = await analyze_async("data/customers.csv")
    result = await train_async("data/customers.csv")

asyncio.run(main())
```

### Error Handling

```python
from aetherml import train
from aetherml.exceptions import DataValidationError, EngineSelectionError, WorkflowError

try:
    result = train("data/customers.csv")
except DataValidationError as e:
    print(f"Dataset failed validation: {e}")
except EngineSelectionError as e:
    print(f"Could not select a data engine: {e}")
except WorkflowError as e:
    print(f"Pipeline failed: {e}")
```

<details>
<summary><strong>Advanced usage — low-level workflow API</strong></summary>

Full pipeline, async:

```python
import asyncio
from aetherml import run_pipeline

async def main():
    result = await run_pipeline(data_path="data/customers.csv")
    print(result)

asyncio.run(main())
```

Running selected stages only:

```python
result = await run_pipeline(
    data_path="data/customers.csv",
    stages=["upload", "etl", "validation"],
)
```

Forcing a specific engine:

```python
from aetherml import AetherMLConfig, run_pipeline

config = AetherMLConfig()
config.engine.preferred = "polars"

result = await run_pipeline(data_path="data/customers.csv", config=config)
```

</details>

[↑ Back to top](#table-of-contents)

---

## SDK Interfaces

AetherML is **SDK-first**: the CLI and the FastAPI service are thin clients that call the same SDK you can `import` directly. Neither contains business logic of its own.

### CLI

```bash
aetherml run data/customers.csv                   # run the full pipeline
aetherml run data/customers.csv --engine polars    # force a specific engine
aetherml info                                       # SDK info
```

Each command maps directly onto an SDK call — `aetherml run` calls `AetherML.run(...)`; there's no logic in the CLI that isn't already in the SDK.

### FastAPI

```bash
pip install aetherml[api]
uvicorn aetherml.interfaces.api.app:app --reload
```

Provides file upload endpoints, background job execution, and automatic OpenAPI docs on top of the same SDK.

### Plugin Architecture (Planned)

> **Status:** not yet implemented — tracked in the [Roadmap](#roadmap).

The `interfaces/` module already defines the contracts (`BaseAgent`, `DataEngine`, `StorageBackend`, and future `ModelBackend` / `ReportFormat` interfaces) that a plugin system will build on. The plan is a Python entry-points-based discovery mechanism — similar in spirit to how pytest or Flake8 discover plugins — letting third parties register:

| Extension Point | Interface | Purpose |
|---|---|---|
| Agents | `BaseAgent` | Add a custom node to the workflow graph |
| Models | `ModelBackend` *(future)* | Add a model family to recommendation/training |
| Data Engines | `DataEngine` | Add an engine (e.g., DuckDB) alongside Pandas/Polars/PySpark |
| Reports | `ReportFormat` *(future)* | Add a custom report renderer |
| Storage | `StorageBackend` | Add a backend (e.g., S3, GCS) |

[↑ Back to top](#table-of-contents)

---

## Project Structure

```
aetherml/
├── __init__.py          # Public SDK surface
├── exceptions.py        # Exception hierarchy
├── agents/               # Pipeline agents
│   ├── base.py             # BaseAgent, AgentResult, Tool
│   ├── upload/              # Data loading agent
│   ├── etl/                 # ETL cleaning agent
│   ├── validation/          # Data validation agent
│   ├── eda/                 # Exploratory data analysis
│   ├── target_detection/    # Target column detection
│   ├── feature_engineering/ # Feature engineering
│   ├── model_selection/     # Model recommendation & training
│   ├── evaluation/          # Model evaluation
│   ├── explainability/      # SHAP-based explainability
│   └── reporting/           # Report assembly
├── configs/              # Pydantic configuration
├── data/                 # Data loading, validation, profiling
├── database/             # Qdrant vector store client
├── engines/              # Pandas/Polars/Spark engine abstraction
├── interfaces/           # Abstract contracts (BaseAgent, DataEngine, StorageBackend)
├── ml/                   # Model definitions, training, metrics
│   ├── automl/              # AutoML model selection
│   ├── evaluation/          # Metrics and evaluation
│   ├── explainability/      # SHAP explanations
│   ├── feature_engineering/ # Feature engineering
│   ├── reports/             # Report builder and templates
│   └── target_detection/    # Target detection heuristics
├── rag/                  # RAG infrastructure
└── workflow/             # LangGraph workflow orchestration
```

<details>
<summary><code>agents/</code> — every pipeline agent</summary>

- **Purpose:** every pipeline agent — validation, EDA, feature engineering, target detection, model recommendation, explainability, reporting, and more.
- **Pattern:** reads from `WorkflowState`, delegates real logic to `ml/`, `data/`, or `engines/` (via services), writes results back.
- **Key modules:** `base.py` (`BaseAgent` interface), `validation_agent.py`, `etl_agent.py`, `eda_agent.py`, `feature_engineering_agent.py`, `target_detection_agent.py`, `model_recommendation_agent.py`, `training_agent.py`, `evaluation_agent.py`, `explainability_agent.py`, `reporting_agent.py`.
- **Boundaries:** invoked only by `workflow/` as graph nodes; never imports from `cli/`, `api/`, or `interfaces/`.
- **Extending:** new agents (e.g. `DriftDetectionAgent`) register as new graph nodes without touching existing ones.

</details>

<details>
<summary><code>workflow/</code> — the LangGraph orchestration graph</summary>

- **Purpose:** the LangGraph graph itself — nodes, edges, conditional branches, and the shared `WorkflowState` schema.
- **Responsibilities:** wires agents in order, handles conditional skips (e.g. "skip EDA on `--fast`"), manages retries, exposes the single `run()` entry point the SDK calls.
- **Key modules:** `graph.py`, `state.py` (`WorkflowState`), `edges.py`.
- **Boundaries:** imports from `agents/`; imported by the SDK. Never touches `engines/` or `services/` directly.
- **Future:** parallel branches, human-in-the-loop checkpoints, resumable runs.

</details>

<details>
<summary><code>engines/</code> — Pandas / Polars / PySpark abstraction</summary>

- **Purpose:** the `DataEngine` abstraction and its Pandas/Polars/PySpark implementations.
- **Key modules:** `base.py` (`DataEngine` interface), `pandas_engine.py`, `polars_engine.py`, `pyspark_engine.py`, `factory.py`.
- **Boundaries:** used only through `services/` — never imported directly by `agents/`, `cli/`, or `api/`. See [Data Engine Abstraction](#data-engine-abstraction).
- **Future:** additional engines (Dask, DuckDB) via the same interface.

</details>

<details>
<summary><code>services/</code> — stateless domain logic shared across agents</summary>

- **Purpose:** stateless domain logic shared across agents — statistics, encoding strategies, scoring, imputation.
- **Key modules:** `validation_service.py`, `profiling_service.py`, `eda_service.py`, `feature_engineering_service.py`, `model_scoring_service.py`, `explainability_service.py`.
- **Boundaries:** called by `agents/`; calls `engines/` through the `DataEngine` interface.
- **Why it exists:** keeps agents thin and orchestration-focused; houses testable domain logic in one reusable place.

</details>

<details>
<summary><code>ml/</code> — model definitions, training, and metrics</summary>

- **Purpose:** model definitions, training routines, evaluation metrics.
- **Key modules:** `models/`, `metrics.py`, `trainer.py`.
- **Boundaries:** invoked by `ModelRecommendationAgent`, `TrainingAgent`, `EvaluationAgent`.
- **Why it exists:** decouples model-selection/training logic from any one ML library.

</details>

<details>
<summary><code>configs/</code> — configuration schemas and defaults</summary>

- **Purpose:** configuration schemas and defaults for the whole pipeline (engine thresholds, validation rules, feature-engineering defaults, model-recommendation weights).
- **Key modules:** `pipeline_config.py`, `engine_config.py`, `defaults.py`.
- **Boundaries:** read by `workflow/`, `agents/`, `services/` at runtime; never mutated during a run.
- **Future:** per-environment profiles, YAML/JSON config loading.

</details>

<details>
<summary><code>exceptions/</code> — the exception hierarchy</summary>

- **Purpose:** `ValidationError`, `EngineSelectionError`, `TargetDetectionError`, and friends, instead of generic Python exceptions.
- **Key modules:** `base.py` (`AetherMLError`), `validation_exceptions.py`, `engine_exceptions.py`, `workflow_exceptions.py`.
- **Boundaries:** raised throughout `agents/`, `services/`, `engines/`; caught at the SDK boundary and by `cli/`.
- **Future:** structured error codes for the FastAPI interface.

</details>

<details>
<summary><code>interfaces/</code> — abstract contracts (BaseAgent, DataEngine, StorageBackend)</summary>

- **Purpose:** abstract base classes/protocols that concrete implementations must satisfy.
- **Key modules:** `agent_interface.py`, `engine_interface.py`, `storage_interface.py`, `report_interface.py`.
- **Why it exists:** programming against interfaces, not implementations, is what makes the plugin system and engine abstraction possible.
- **Boundaries:** implemented throughout `agents/`, `engines/`, `storage/`; referenced (not implemented) by `workflow/`.

</details>

<details>
<summary><code>cli/</code> — the command-line interface</summary>

- **Purpose:** the command-line interface, built on the SDK.
- **Key modules:** `main.py`, `commands/` (`run.py`, `validate.py`, …).
- **Boundaries:** imports only from the top-level SDK; never reaches into `agents/`, `services/`, or `engines/` directly.
- **Future:** interactive mode, shell completion, richer output.

</details>

<details>
<summary><code>api/</code> — the FastAPI HTTP interface</summary>

- **Purpose:** exposes the SDK over HTTP.
- **Key modules:** `app.py`, `routes.py`, `jobs.py`, `models.py`.
- **Boundaries:** imports only from the top-level SDK, mirroring the CLI's discipline.
- **Future:** auth/authorization middleware, webhook-based job callbacks.

</details>

<details>
<summary><code>reports/</code> — report generation logic</summary>

- **Purpose:** structure and generation logic for output reports (validation, EDA, evaluation, explainability).
- **Key modules:** `report_builder.py`, `templates/`, `schema.py`.
- **Boundaries:** invoked by `ReportingAgent`; writes through `storage/`.
- **Future:** PDF rendering, report diffing between runs.

</details>

<details>
<summary><code>storage/</code> — where artifacts are persisted</summary>

- **Purpose:** abstracts *where* artifacts are persisted.
- **Key modules:** `base.py` (`StorageBackend`), `local_storage.py` (the offline-first default).
- **Boundaries:** used by `reports/` and `ml/` (for trained-model artifacts).
- **Future:** S3/GCS/Azure Blob backends, database-backed run history.

</details>

<details>
<summary><code>plugins/</code> — extension system (planned)</summary>

Reserved for the entry-points-based plugin system described in [Plugin Architecture](#plugin-architecture-planned). Not yet implemented.

</details>

<details>
<summary><code>tests/</code> — the full test suite</summary>

- **Purpose:** `unit/`, `integration/`, `regression/`, `architecture/`, plus `conftest.py` for shared fixtures.
- See [Testing](#testing) for what each category verifies.
- **Boundaries:** imports from every package as needed; never imported by production code.

</details>

<details>
<summary><code>docs/</code> — long-form documentation source</summary>

Source for long-form documentation — architecture guides, per-agent references, configuration guides — that doesn't belong in this README.

</details>

<details>
<summary><code>examples/</code> — runnable example scripts</summary>

Runnable, minimal scripts (`basic_analysis.py`, `custom_config.py`, `selected_stages.py`) demonstrating common SDK usage. Kept current as a first-class documentation responsibility.

</details>

[↑ Back to top](#table-of-contents)

---

## Roadmap

<p align="center">
  <img src="https://img.shields.io/badge/status-active%20development-brightgreen?style=flat-square" alt="Status: Active Development">
  <img src="https://img.shields.io/badge/version-0.1.0-blue?style=flat-square" alt="Version 0.1.0">
</p>

**Completed**
- [x] Core `WorkflowState` and LangGraph-based orchestration
- [x] Validation, Profiling, ETL, EDA, Feature Engineering, Target Detection, Model Recommendation, Training, Evaluation, Explainability, and Reporting agents
- [x] Pandas, Polars, and PySpark data engines with automatic selection
- [x] Local filesystem storage backend
- [x] CLI interface
- [x] FastAPI HTTP interface with background jobs, file uploads, and OpenAPI docs
- [x] HTML report generation (`generate_report(format="html")`)
- [x] Unit, integration, regression, and architecture test suites

**Planned**
- [ ] Plugin system with entry-points-based discovery (`plugins/`)
- [ ] Additional storage backends (S3, GCS, Azure Blob)
- [ ] Additional data engine support (DuckDB)
- [ ] PDF report rendering
- [ ] Parallel/branching agent execution within the workflow graph
- [ ] Desktop GUI client built on top of the SDK
- [ ] Human-in-the-loop checkpoints within the workflow graph

[↑ Back to top](#table-of-contents)

---

## Documentation

This README covers concepts and day-to-day usage. Deeper, agent-by-agent reference material — architecture guides, configuration options, and the full agent contract docs — lives in [`docs/`](docs/). A hosted documentation site is planned; until then, browsing `docs/` directly is the fastest way to go deeper on any single stage.

[↑ Back to top](#table-of-contents)

---

## Contributing

Contributions of all kinds are welcome — bug fixes, new agents, documentation, and test coverage.

![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)
![Good First Issues](https://img.shields.io/github/issues/kartik00052/AetherML/good%20first%20issue?style=flat-square&label=good%20first%20issues)

Start from the **development install** in [Installation](#installation) to get a local editable copy set up.

### Testing

The test suite is split into four categories, each answering a different question:

| Category | Question It Answers | Example |
|---|---|---|
| **Unit** | Does this function/class behave correctly in isolation? | Does `EncodingService.one_hot()` produce the expected columns? |
| **Integration** | Do multiple components work correctly together? | Does `ValidationAgent → ProfilingAgent → ETLAgent` produce a correctly canonicalized dataset? |
| **Regression** | Does the pipeline keep producing stable output over time? | Does a fixed sample dataset always yield the same EDA summary across releases? |
| **Architecture** | Are the module boundaries in this README actually enforced? | Does static analysis confirm `agents/` never imports from `engines/` directly? |

```bash
pytest                    # full suite
pytest tests/unit         # unit tests only
pytest tests/integration  # integration tests only
pytest -k "validation"    # tests matching a keyword
```

Architecture tests exist so that boundary violations are caught in CI, not discovered later during a refactor.

### Linting & Formatting

```bash
ruff check .
ruff format .
```

### Workflow

1. Fork the repo and branch off `main` — use `feature/<description>`, `fix/<description>`, or `docs/<description>`.
2. Make your change, with tests in the appropriate category above.
3. Run the full suite and linter locally before opening a PR.
4. Open a pull request describing the change and referencing any related issue.
5. Address review feedback — a maintainer will merge once it's approved.

New public functions and classes should include type hints and docstrings, and pass `ruff check .` / `ruff format .` before review.

Have an idea before writing code? Open a GitHub [Issue](https://github.com/kartik00052/AetherML/issues) for bugs or feature requests, or start a [Discussion](https://github.com/kartik00052/AetherML/discussions) for open-ended design questions — e.g. "how should the plugin discovery mechanism work?"

[↑ Back to top](#table-of-contents)

---

## FAQ

<details>
<summary>Why not just use AutoML?</summary>

AutoML tools optimize for a leaderboard metric and often hide the reasoning behind their choices. AetherML makes every decision — imputation strategy, encoding, model family — inspectable and overridable, at the cost of being less hands-off than a pure AutoML tool.

</details>

<details>
<summary>Why LangGraph specifically?</summary>

LangGraph models workflows as a graph of stateful nodes with conditional edges, which maps directly onto AetherML's pipeline shape — sequential stages with occasional conditional skips — without hand-written orchestration and retry logic.

</details>

<details>
<summary>Why Polars in addition to Pandas?</summary>

Pandas is the default for small-to-medium datasets, but its single-threaded execution becomes a bottleneck on larger data. Polars' multi-threaded, Rust-based engine handles larger single-machine workloads significantly faster, so AetherML upgrades to it automatically when dataset size warrants it.

</details>

<details>
<summary>Why SDK-first instead of API-first or app-first?</summary>

Building the SDK first ensures there's exactly one place where ML logic lives. Every interface built afterward — CLI, FastAPI, any future GUI — is a client of that logic rather than a second implementation of it, which avoids behavioral drift between interfaces.

</details>

<details>
<summary>Can I run only part of the pipeline?</summary>

Yes — the SDK's `run()` (and `run_pipeline()`) accept a `stages` parameter that lets you run any subset of the pipeline. See [Examples](#examples).

</details>

<details>
<summary>Can I integrate AetherML with my own FastAPI app today?</summary>

Yes, informally — since the SDK is a plain Python package, you can already wrap `AetherML.run()` in your own FastAPI routes. The `api/` module in this repo is AetherML's own first-party FastAPI interface, not a prerequisite for using AetherML from an app you build yourself.

</details>

<details>
<summary>Can I write my own agents today?</summary>

Not yet through a formal mechanism — that's the planned [plugin system](#plugin-architecture-planned). Today, adding a custom agent means modifying `workflow/graph.py` directly in a fork or contribution.

</details>

[↑ Back to top](#table-of-contents)

---

## License

Licensed under the MIT License — see [LICENSE](LICENSE) for the full text.

<details>
<summary>View full MIT License text</summary>

```
MIT License

Copyright (c) 2026 AetherML Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

</details>

[↑ Back to top](#table-of-contents)

---

## Community

AetherML is maintained in the open. If something's broken, open an [Issue](https://github.com/kartik00052/AetherML/issues); if you have a design question or an idea you want to think through before writing code, start a [Discussion](https://github.com/kartik00052/AetherML/discussions). Pull requests are reviewed against the guidelines in [Contributing](#contributing).

[↑ Back to top](#table-of-contents)

---

## Acknowledgements

![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square&logo=langchain&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?style=flat-square&logo=mlflow&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-CD792C?style=flat-square&logo=polars&logoColor=white)

AetherML's design draws on the architectural patterns and developer experience of several mature open-source projects, without affiliation with or endorsement from them:

- **[scikit-learn](https://scikit-learn.org/)** — a consistent estimator API and a commitment to interpretable, well-documented behavior.
- **[FastAPI](https://fastapi.tiangolo.com/)** — proof that a thin, type-driven interface layer can sit cleanly on top of independent business logic.
- **[LangGraph](https://www.langchain.com/langgraph)** — the graph-based orchestration model AetherML's workflow layer is built directly on.
- **[MLflow](https://mlflow.org/)** — its approach to structured, versionable run tracking and reporting.
- **[Polars](https://pola.rs/)** — a model of what a modern, high-performance dataframe engine can look like, and one of AetherML's actual data engines.

---

<p align="center"><sub>Built with a commitment to transparent, inspectable machine learning pipelines.</sub></p>
