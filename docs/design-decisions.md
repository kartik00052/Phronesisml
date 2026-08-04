# Design Decisions

Every significant design choice in PhronesisML came from a real problem. This page documents the major issues we faced, the fallbacks we considered, and why we made the choices we did.

---

## 1. Why Agents Instead of Functions?

### The Problem

Early prototypes used plain functions for each pipeline stage. As the pipeline grew, functions started accumulating hidden dependencies — they needed access to the engine, the config, the previous stage's output, and error handling state. Testing became painful because every function needed the full pipeline context.

### Fallbacks Considered

| Approach | Why It Failed |
|----------|---------------|
| **Pure functions with many parameters** | Signature bloat — 8+ parameters per function |
| **Global state module** | Untestable, implicit dependencies, threading hazards |
| **Class inheritance chain** | Diamond inheritance when agents need multiple capabilities |

### The Decision: Protocol-Based Agents

Agents satisfy a `BaseAgent` protocol via duck typing (structural subtyping). They receive a single `state` dict and return a standardized `AgentResult`. This gives us:

- **Testability:** Any agent can be tested in isolation with a mock state dict
- **Independence:** Agents don't know about each other — they only read/write state
- **Composability:** New agents can be added without modifying existing ones

### Trade-off

We lose compile-time type checking on agent implementations (since Protocol is structural). We compensate with runtime validation via Pydantic state and comprehensive tests.

---

## 2. Why LangGraph Instead of Airflow/Prefect?

### The Problem

The ML pipeline is a directed graph with conditional routing — if validation fails, skip training. If target detection is ambiguous, flag it. We needed a framework that supports conditional edges, not just linear DAGs.

### Fallbacks Considered

| Approach | Why It Failed |
|----------|---------------|
| **Airflow** | Designed for batch scheduling, not interactive ML pipelines. Heavy dependencies. |
| **Prefect** | Similar — orchestration-focused, not stateful computation graphs |
| **Custom DAG executor** | Reinventing the wheel. No caching, no streaming, no checkpointing |
| **Simple function chaining** | No conditional routing. No partial result recovery |

### The Decision: LangGraph

LangGraph provides:

- **Stateful graphs** with typed state (we use Pydantic `BaseModel`)
- **Conditional routing** — each node can decide to proceed or end
- **Graph compilation and caching** — repeated calls skip recompilation
- **Streaming support** — real-time progress updates
- **Lightweight** — no external services required

### Trade-off

LangGraph is a newer framework with a smaller ecosystem. We accept this because the core graph semantics are stable, and the alternative (building our own) would be far more costly.

---

## 3. Why Three Engines (Pandas/Polars/Spark)?

### The Problem

Different datasets have different performance characteristics. A 100-row CSV doesn't need Polars. A 10GB dataset can't fit in Pandas. We needed an abstraction that lets users pick the right tool without changing their code.

### Fallbacks Considered

| Approach | Why It Failed |
|----------|---------------|
| **Pandas only** | Can't handle large datasets. No lazy evaluation. |
| **Polars only** | Smaller ecosystem. Some users don't have it installed. |
| **Abstract "pluggable" engine** | Over-engineered. Users don't want to write engine plugins. |

### The Decision: Three-Tier Auto-Selection

```
< 2 MB  → Pandas (fast startup, familiar)
2–500 MB → Polars (2-10x faster, lower memory)
> 500 MB → Spark (distributed)
```

Users can override with `config.engine.preferred = "polars"`. The engine layer normalizes everything to Pandas at the boundary — downstream code doesn't need to know which engine is active.

### Major Issue: Polars/Pandas API Mismatch

**What happened:** `load_file()` normalizes all data to Pandas via `engine.collect()`. But PolarsEngine's `memory_usage()` and `head()` methods used Polars-only APIs (`df.estimated_size()`, `df.head(n).to_pandas()`). When a user forced Polars on a small dataset, the pipeline crashed at the EDA stage with `AttributeError: 'DataFrame' object has no attribute 'estimated_size'`.

**The fix:** Made PolarsEngine methods accept both Polars and Pandas DataFrames:

```python
def memory_usage(self, df: Any) -> int:
    if isinstance(df, pd.DataFrame):
        return int(df.memory_usage(deep=True).sum())
    if isinstance(df, pl.DataFrame):
        return int(df.estimated_size("bytes"))
    raise EngineError(f"Expected DataFrame, got {type(df).__name__}")
```

**Lesson:** Engine abstraction boundaries must be tested with all engine types, not just the native one.

---

## 4. Why Two-Stage Data Processing (ETL → Target Detection → Feature Engineering)?

### The Problem

ETL needs to clean ALL columns (including the target). But feature engineering needs to EXCLUDE the target from transforms (you don't scale or encode the thing you're predicting). This creates a chicken-and-egg problem.

### Fallbacks Considered

| Approach | Why It Failed |
|----------|---------------|
| **Single stage handles everything** | Can't exclude target if you don't know it yet |
| **Guess the target first, then clean** | Cleaning without knowing types is fragile |
| **Skip ETL, do everything in FE** | Target column gets scaled/encoded — breaks labels |

### The Decision: Two-Stage Split

1. **ETL (before target detection):** Clean ALL columns — drop nulls, cast types, encode categoricals
2. **Target Detection:** Identify the prediction target and task type
3. **Feature Engineering (after target detection):** Transform feature columns only — scale, encode, handle outliers, select features

### Trade-off

Some data is "wasted" — ETL encodes columns that FE will re-encode. This is intentional: ETL produces a clean, valid DataFrame that target detection can analyze. FE then adds signal on top.

---

## 5. Why No Custom Models?

### The Problem

Users want to add their own model classes (XGBoost, LightGBM, custom sklearn estimators). The current model selection agent has hardcoded candidates.

### Fallbacks Considered

| Approach | Why It Was Deferred |
|----------|---------------------|
| **Plugin system with entry points** | Complex to implement, versioning issues |
| **YAML model definitions** | Limited expressiveness for custom params |
| **Dynamic import from config** | Security concerns, validation complexity |

### The Decision: Hardcoded Candidates (for now)

The model selection agent supports:

**Classification:** `logistic_regression`, `random_forest`, `gradient_boosting`

**Regression:** `linear_regression`, `random_forest`, `gradient_boosting`

Each has pre-defined hyperparameter spaces and re-ranking heuristics for small datasets and high-dimensional data.

### Workaround

Use the OOP API to train a specific model directly:

```python
ml = Phronesis("data.csv")
ml.run()  # or call stages individually
ml.train(model_type="random_forest")
```

Or use the advanced API with a custom pipeline:

```python
from phronesisml import run_pipeline
result = await run_pipeline(
    data_path="data.csv",
    stages=["upload", "etl", "validation", "eda",
            "target_detection", "feature_engineering"],
)
# Then train your own model on result["features"]
```

### Future Plan

A plugin system is on the roadmap but not yet implemented.

---

## 6. Why SHAP for Explainability?

### The Problem

Users need to understand *why* a model makes certain predictions. Black-box models (random forest, gradient boosting) are inherently opaque.

### Fallbacks Considered

| Approach | Why It Was Deferred |
|----------|---------------------|
| **LIME** | Less mature, fewer integrations |
| **Permutation importance** | Doesn't show per-prediction explanations |
| **Custom feature importance** | Reimplementing what SHAP already does |

### The Decision: SHAP with Three Explainer Types

SHAP is the industry standard for model explainability. PhronesisML auto-selects the right explainer:

| Model Type | SHAP Explainer | Speed |
|------------|---------------|-------|
| Tree-based (RF, GBM) | `TreeExplainer` | Fast, exact |
| Linear (LR, Ridge) | `LinearExplainer` | Fast, exact |
| Everything else | `KernelExplainer` | Slow, approximate |

### Graceful Degradation

SHAP is included as a core dependency (`shap>=0.51,<0.53`; resolves to 0.51.0 on py<3.12 and 0.52.0 on py≥3.12). The explainability agent uses it to generate feature importance explanations automatically — no extra install needed.

---

## 7. Why Pydantic for Workflow State?

### The Problem

The `WorkflowState` object carries data between 11 agents. If an agent writes the wrong type, downstream agents crash with confusing errors.

### Fallbacks Considered

| Approach | Why It Failed |
|----------|---------------|
| **Plain dict** | No type checking, easy to misspell keys |
| **TypedDict** | Structural only, no runtime validation |
| **Dataclass** | No validation, mutable by default |

### The Decision: Pydantic BaseModel

```python
class WorkflowState(BaseModel):
    raw_data: pd.DataFrame | None = None
    processed_data: pd.DataFrame | None = None
    target_column: str | None = None
    task_type: str | None = None
    # ... every field typed and validated
```

Pydantic provides:

- **Runtime validation** — wrong types caught immediately
- **Serialization** — state can be saved/loaded
- **Documentation** — field types are self-documenting

### Trade-off

Pydantic has overhead for large DataFrames (validation on every assignment). We accept this because the validation cost is negligible compared to ML computation.

---

## Summary of Key Trade-offs

| Decision | Chose | Rejected | Reason |
|----------|-------|----------|--------|
| Agent pattern | Protocol (duck typing) | ABC inheritance | Avoids diamond inheritance |
| Pipeline framework | LangGraph | Airflow/Prefect | Stateful graphs, conditional routing |
| Engine abstraction | 3-tier auto-select | Single engine | Different datasets need different tools |
| Data processing | Two-stage (ETL → FE) | Single stage | Target must be known before feature engineering |
| Model selection | Hardcoded candidates | Plugin system | Simplicity for alpha; plugins planned |
| Job store | In-memory dict | Database | Lightweight for development |
| Explainability | SHAP | LIME/Permutation | Industry standard, three explainer types |
| State management | Pydantic BaseModel | TypedDict/Dataclass | Runtime validation + serialization |
