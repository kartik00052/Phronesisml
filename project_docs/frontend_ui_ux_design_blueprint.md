# PhronesisML Frontend — UI/UX Research & Design Discovery

**Status:** Research / Design Blueprint (no implementation in this phase)
**Package audited:** `phronesisml` v0.3.1 (Python >=3.11,<3.14)
**Deliverable:** Design specification + implementation blueprint for the eventual PhronesisML web dashboard
**Scope:** Research only. No frontend code, no backend/API changes, no dependency installs.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Repository analysis → UX implications](#2-repository-analysis--ux-implications)
3. [Research methodology](#3-research-methodology)
4. [Competitive & reference research](#4-competitive--reference-research)
5. [Design principles & visual direction](#5-design-principles--visual-direction)
6. [Design system recommendations](#6-design-system-recommendations)
7. [Information architecture & navigation](#7-information-architecture--navigation)
8. [User journeys](#8-user-journeys)
9. [Screen-by-screen specifications](#9-screen-by-screen-specifications)
10. [Real-time execution UX](#10-real-time-execution-ux)
11. [Backend ↔ Frontend contract](#11-backend--frontend-contract)
12. [Error, empty & degraded states](#12-error-empty--degraded-states)
13. [Accessibility](#13-accessibility)
14. [Responsive design](#14-responsive-design)
15. [Frontend tech stack recommendation](#15-frontend-tech-stack-recommendation)
16. [Implementation blueprint & priorities](#16-implementation-blueprint--priorities)
17. [Risks & open questions](#17-risks--open-questions)
18. [Reference links](#18-reference-links)

---

## 1. Executive summary

PhronesisML is a LangGraph-based, agent-driven AutoML **Python SDK** (v0.3.1). It
has no web frontend today (`frontend/` is empty) and no HTTP layer (the previous
REST API was deliberately decommissioned in v0.3.0 in favor of an SDK-first
architecture). Every piece of data the UI needs already exists as structured
Python objects and JSON artifacts on disk.

This document is a design discovery that turns that backend reality into a
frontend blueprint. Key conclusions:

1. **The UI should be a "run inspector", not a "maker".** PhronesisML's value is
   observability of an autonomous 11-stage agent pipeline. The dashboard's job is
   to make each stage's decision legible: *what the agent decided, why, and what
   it produced* — matching the LangGraph frontend pattern of "one card per graph
   node, one region per state key".
2. **Mirror the 11-stage pipeline as the primary navigation spine.** Upload → ETL →
   Validation → EDA → Target detection → Feature engineering → Model selection →
   Evaluation → Explainability → Reporting → Storage. This is the canonical
   `_FULL_PIPELINE_STAGES` list and is the strongest mental model users already have
   from the docs/CLI.
3. **Two visual paradigms, used deliberately:** (a) a **horizontal DAG / stepper**
   for live execution and (b) a **tabular leaderboard** for model comparison — the
   two patterns that dominate every competitor reviewed (DataRobot, H2O, AutoGluon,
   MLflow, W&B, Vertex AI, SageMaker, Azure ML).
4. **No real-time channel exists.** Backend `status` is a single string
   (`running` / `completed` / `failed`). The blueprint recommends SSE for progress
   plus polling for run lists, and specifies the minimal backend observability
   additions needed (stage-level events).
5. **Every backend/frontend interface is `Proposed`.** Because there is no REST
   API, this doc designs the contract a thin local server (FastAPI adapter around the
   SDK) would expose, clearly labeled `Existing capability` (SDK method) vs `Proposed
   HTTP endpoint`.
6. **Visual direction:** developer-platform aesthetics (Linear, Vercel, Supabase
   sensibility), light + dark themes, restrained accent color, no generic "AI
   purple gradient" stock look, dense-but-calm information hierarchy.

---

## 2. Repository analysis → UX implications

### 2.1 Pipeline structure

Canonical stages (`phronesisml/_stages.py::_FULL_PIPELINE_STAGES`):

```
upload → etl → validation → eda → target_detection → feature_engineering →
model_selection → evaluation → explainability → reporting → storage
```

Stage slices (used by the public API for partial runs) are the natural basis for
the "run a subset" UX:

| Slice constant | Stages | Public entry point |
|---|---|---|
| `_STAGES_ANALYZE` | upload, etl, validation, eda | `analyze()` |
| `_STAGES_CLEAN` | upload, etl | `clean()` |
| `_STAGES_VALIDATE` | upload, etl, validation | `validate()` |
| `_STAGES_DETECT_TARGET` | upload … target_detection | `detect_target()` |
| `_STAGES_ENGINEER` | upload … feature_engineering | `engineer()` |
| `_STAGES_SELECT_MODEL` / `_STAGES_EVALUATE` | upload … evaluation | `select_model()` / `evaluate()` |
| `_STAGES_EXPLAIN` | upload … explainability | `explain()` |
| `_STAGES_REPORT` | upload … reporting | `report()` |
| `_STAGES_TRAIN` | all 11 | `train()` / `run_pipeline()` |
| `_STAGES_CLUSTER` / `_STAGES_ANOMALY` / `_STAGES_DETECT_TASK` | specializations | `cluster()` / `detect_anomalies()` / `detect_task()` |

**UX implication:** the run wizard should present stages as a checklist the user
can truncate ("Run up to…"), and the run detail page should render exactly those
stages that were executed.

### 2.2 WorkflowState = single source of truth

`phronesisml/workflow/state.py::WorkflowState` (Pydantic) is the single dataclass
flowing through every agent. It cleanly separates into **five UX regions**, each
owned by specific agents:

| Region | Representative fields | Best UI surface |
|---|---|---|
| Input | `data_path`, `file_format`, `row_count`, `raw_data` | Data/provenance panel |
| Data quality | `validation_report`, `transform_log`, `validated_data`, `processed_data` | Validation summary + transform log |
| Understanding | `data_profile`, `eda_report`, `target_column`, `task_type`, `target_detection_confidence`, `ambiguity_reason` | EDA & target detection tabs |
| Modeling | `features`, `feature_names`, `best_pipeline`, `training_metrics`, `evaluation_report`, `model` | Leaderboard / model cards |
| Delivery | `explainability` (feature importance, SHAP), `report_path`, `run_id`, `artifact_uri`, `status`, sampling flags | Reports & artifacts tabs |

**UX implication:** a run detail page organized around these regions will feel
"explainable" — the UI documents each agent's decision the way LangGraph's
frontend SDK maps nodes to cards and state keys to regions.

### 2.3 Saved runs & artifacts

Every run writes 17 files under `Phronesis_artifacts/run_<id>/`
(`services/storage.py::save_artifacts`, storage agent):

`config.json` · `eda.json` · `engine_selection.json` · `evaluation.json` ·
`feature_metadata.json` · `logs.txt` · `metrics.json` · `model.joblib` ·
`model.json` · `pipeline.json` · `report.html` · `report.md` ·
`resource_estimation.json` · `run_metadata.json` · `shap.json` ·
`target_detection.json` · `training.json` · `validation.json`

`run_metadata.json` already holds: `run_id`, `status`, `version`, `data_path`,
`target_column`, `task_type`, `engine`, `best_pipeline`, `artifact_count`,
`saved_files`. `services/storage.py` also exposes `list_artifacts(base_dir)`,
`load_artifact(path)`, and `build_artifact_manifest(...)` — a ready-made backend
for an artifacts browser.

**UX implication:** the "Runs" section can be built almost entirely from
`run_metadata.json` (list) + the 17 files (detail). No backend change required for
read-only browsing of already-completed runs.

### 2.4 Engine auto-selection is a user-facing decision

`engines/engine_selector.py` + `configs/settings.py`:
- file < **2 MB** → pandas
- 2 MB → **max_memory_bytes** (default 500 MB) → polars
- above → spark (pyspark optional extra)
- `EngineConfig.preferred` forces an engine; hard ceiling 2 GB default.

**UX implication:** show the chosen engine and its reasoning as a first-class
signal in the run header ("pandas · file 1.2 MB < 2 MB"), and surface it in the
wizard as an overridable setting with the auto recommendation displayed. Users who
trained with spark need to know pyspark is an optional extra.

### 2.5 Task types & ambiguity

Task types: classification / regression / clustering / anomaly_detection /
`ambiguous`. Target detection uses name signals + cardinality heuristics;
`AMBIGUITY_THRESHOLD = 0.6`; `MAX_CLASSIFICATION_UNIQUE_VALUES = 20`. An ambiguous
result carries `target_detection_confidence` and `ambiguity_reason`.

**UX implication:** the target-detection screen is a *confirmation* interaction,
not a form. When ambiguous, highlight the uncertainty, show candidates and why,
and require an explicit user pick (matches the "interrupt / human-in-the-loop"
pattern from LangGraph).

### 2.6 Metrics by task type

`ml/evaluation/metrics.py` and `report.py`:

| Task | Metrics available | Primary (leaderboard sort) |
|---|---|---|
| classification | accuracy, precision_macro, recall_macro, f1_macro, roc_auc, confusion matrix, ROC curve, PR curve, average_precision | f1_weighted / f1 / roc_auc / accuracy |
| regression | rmse, mae, r2 | r2 / rmse / mae |
| clustering | silhouette, davies_bouldin, calinski_harabasz | silhouette_score |
| anomaly detection | contamination ratio, anomaly count | f1 / precision |

`compare_models()` ranks best-first — the direct data source for a leaderboard table.

**UX implication:** the leaderboard is task-aware; primary metric column is
sortable and switchable; secondary metrics expandable per row; confusion matrix
+ ROC/PR curves render inline.

### 2.7 Explainability

`ml/explainability/service.py`: `ExplainConfig(max_samples=100, max_features=50)`,
explainer routing Tree → Linear → Permutation → Kernel; deterministic sampling;
structured `feature_importance` dict; outputs `explainer_type`, `sampled` flag,
`n_samples_used`. SHAP artifacts are serialized into `shap.json`.

**UX implication:** the explainability tab must truthfully display *how* the
explanation was computed (explainer type + sampling banner), not just a bar chart.
Beeswarm + force-plot style visualizations should be re-rendered client-side from
`shap.json` rather than embedding static images where feasible.

### 2.8 Errors & degraded operation

- `exceptions.py` hierarchy: `PhronesisError`, `ConfigurationError`, `DataError`,
  `DataLoadError`, `DataTransformError`, `DataValidationError`, `EngineError`,
  `EngineSelectionError`, `WorkflowError`, `AgentError(error_type, error_message)`.
- Agent `success=False` → `AgentError` raises → pipeline halts.
- Reporting/explainability degrade gracefully when optional deps (MLflow, shap
  explainer, report sections) are missing; `health()` returns dependency status
  (`ok` / `degraded`).

**UX implication:** a first-class **failure panel** (which stage, error type,
message, and the captured logs.txt) plus a **system health screen** driven by
`health()`. Degraded optional features must be visually distinguishable.

### 2.9 No HTTP layer

`project_docs/rest_api_inventory.md` + `rest_api_removal_report.md` confirm the
REST API was removed in v0.3.0. All of §11 is therefore **Proposed**, designed as a
thin adapter around the SDK (which runs in-process; the server itself owns the
Phronesis engine or orchestrates `run_pipeline`).

---

## 3. Research methodology

- **Repository pass:** traced `sdk.py`, `simple.py` (23 sync + async public
  functions), `_stages.py`, `workflow/{state,graph,nodes,sampling_node,router}`,
  `agents/{base,compose}` and individual agents, `engines/engine_selector.py`,
  `configs/settings.py`, `services/storage.py`, `ml/{evaluation,explainability,
  reports,target_detection,automl}/*`, `exceptions.py`, `results.py`, the CLI, and
  a real artifact directory (`Phronesis_artifacts/run_4f7a40d7…/`).
- **Web research:** targeted searches (no generic "best AI dashboard" queries) for
  AutoML leaderboards, experiment-tracker UIs, pipeline/DAG UIs, agentic
  visualization, SHAP/data-profiling UIs, developer-tool aesthetics, and design
  inspiration platforms. Every reference listed in §18 was visited or surfaced in
  results — **no URLs were fabricated**; sources judged low-quality (e.g. Tracxn
  profile pages) are omitted.
- **Synthesis:** cross-tabulated competitor patterns against PhronesisML's
  concrete data model to produce screens that are implementable from existing
  artifacts (§9, §11).

---

## 4. Competitive & reference research

### 4.1 AutoML leaders & leaderboards

| Product | Key patterns | Useful for |
|---|---|---|
| **H2O AutoML** | Leaderboard ranked by validation metric; `max_runtime_secs` / `max_models` stopping; Stacked Ensembles surface at top; leaderboard_frame scoring | Leaderboard semantics, stopping-criteria wizard |
| **DataRobot Model Leaderboard** | Performance-ranked leaderboard; per-model tiles; Model Comparison (side-by-side curves); model cards with badges ("✓ top"), insights, sample-size quality flag, blueprint | Leaderboard density, model card anatomy, comparison view |
| **AutoGluon leaderboard** | Tabular leaderboard: `model`, `score_val`, `eval_metric`, `pred_time_val`, `fit_time`, `stack_level`, `can_infer`, `fit_order`, `score_test`; scores shown *higher-is-better* normalized | Column set for Phronesis leaderboard (adapt to `training.json`/`metrics.json`) |
| **Azure ML AutoML** | Job detail: parent job → "Models + child jobs" tab, models ordered by metric as they complete, "Best model summary" section, Overview/Metrics tabs, deploy-from-best | Live-updating leaderboard while models finish (matches Phronesis HPO `trials`), best-model hero |
| **Oracle OML AutoML UI** | Experiment pages with stages `Completed / Running / Ready`; leader board with metric + algorithm | Simple status-badge taxonomy for runs |
| **SageMaker Studio / Experiments** | Left rail: Data → Experiments → Models → Deployments (workflow-shaped nav); Experiments = collection of trials, trial = steps, trial components; chart view for comparing trials | Workflow-shaped IA; experiment/trial/step hierarchy |

**Synthesis:** leaderboards should be **ranked by a switchable primary metric**,
keep scores higher-is-better normalized, mark the current best with a badge,
expose prediction/fit time and "stack/can_infer"-style status, and surface a
"best model" hero with an explicit why (Phronesis Roadmap calls this *model
recommendation with a WHY*).

### 4.2 Experiment tracking

| Product | Key patterns | Useful for |
|---|---|---|
| **MLflow Tracking UI** | Experiments ↔ runs ↔ models; run metadata params/metrics/artifacts; per-run metric charts (line/step); run comparison tables; models tab; search by param/metric | Runs list + run detail structure; comparison table |
| **Databricks MLflow Experiments UI (new chart view)** | Chart view: bar/line/scatter/parallel-coordinates customizable dashboard; run highlighting; brushing to filter | Advanced future: parallel-coordinates HPO view |
| **W&B** | Run table (sort/filter/group); panel-based workspace; **Run Comparer** with "Diff only" toggle to hide identical config values | The **compare runs** experience (Phronesis `compare()`) — highlight differing params/metrics |
| **SageMaker Experiments** | Trial components as workflow steps; charted comparison in Studio | Trial-component → Phronesis stage mapping |

**Synthesis:** Phronesis runs are closer to SageMaker "trials" (multi-step
workflow) than flat MLflow runs; the stage breakdown *is* the trial component
list. The Compare screen should adopt W&B's "show differences only" toggle.

### 4.3 Pipeline / DAG UIs

| Product | Key patterns | Useful for |
|---|---|---|
| **Airflow 3 UI** | DAG list; **Grid view** (rows=tasks, cols=runs, color status matrix); **Graph view** (logical structure + run state overlay); Runs tab; task-instance logs; notes; dark/light themes; DAG Dependencies view | The single most relevant reference for Phronesis pipeline UI; grid + graph duality |
| **Dagster UI** | Overview "factory floor"; Assets catalog + lineage; op graph with right-side inspector; run timeline; launchpad | Click-node → right inspector panel pattern; "factory floor" runs list |
| **Azure ML Designer** | Drag-and-drop canvas of components; component right-pane settings; pipeline jobs grouped into experiments; clone a job to edit | Authoring canvas (future if Phronesis gains pipeline composition); not needed for v1 read-only |
| **React Flow** (@xyflow/react) | Zoom/pan/minimap, custom nodes, ELK/dagre/force auto-layout, `onlyRenderVisibleElements` perf option, MDN-doc style, MIT | The DAG renderer of choice for the pipeline screen |

**Synthesis:** Phronesis graphs are **linear** (upload→…→storage). A full
free-drag node editor is overkill; a **linear stepper + annotated Graph view**
(Airflow-style) is the right call. Evaluate under "avoid the seductive DAG": the
default UI should be the *grid/stepper*; the DAG is a zoom-in, not the home.

### 4.4 Agentic / LangGraph visualization

| Product | Key patterns | Useful for |
|---|---|---|
| **LangSmith Studio / LangGraph Studio** | Graph of nodes; shows each step (prompts, tool calls, results); inspect intermediate state; interrupts; fork threads ("time travel"); add interrupts per node to step through | Phronesis stage stepping; node interrupts → "resume/adjust" interactions |
| **LangGraph frontend SDK patterns** | Named node → one card/timeline step; state key → dedicated UI region; interrupts; subgraphs revealed lazily; `useStream` node-scoped outputs | Directly maps to Phronesis `WorkflowState` keys; the *"cards per stage"* pattern |
| **Langfuse Agent Graphs** | **Aggregated vs Expanded** toggle: one node per step-name (collapsed, with counter) vs per actual call (unrolled DAG); cycles drawn vs unrolled | For Phronesis: aggregated = the 11 stages; expanded = the actual executed nodes incl. sampling nodes |

**Synthesis:** Phronesis's linear graph has *hidden* runtime nodes (sampling nodes
run before EDA, FE, target detection, model selection, explainability; routing
functions choose paths). Langfuse's aggregated/expanded mode is the exact right
way to show "what the code defines" vs "what actually ran".

### 4.5 Explainability & data profiling

| Product | Key patterns | Useful for |
|---|---|---|
| **SHAP** | Beeswarm (feature importance + direction + density), bar (mean abs), force (one prediction), waterfall | Re-render client-side from `shap.json`; honors `max_display` semantics |
| **Azure Responsible AI dashboard** | No-code dashboard: error analysis, model overview, data explorer, feature importances, fairness | Feature-importance + fairness tab structure (stretch) |
| **ydata-profiling** | One-line HTML/JSON report: Overview, Variables (per-column stats + histograms), Correlations, Missing values, Sample data | Phronesis `eda.json` / `data_profile` rendering pattern; per-column expandable cards |

### 4.6 Developer-tool aesthetics & design platforms

| Product | Key patterns | Useful for |
|---|---|---|
| **Linear design refresh** | "Don't compete for attention you haven't earned"; "structure should be felt not seen"; fewer borders; token-based themes; custom theme builder via HSL | Core visual principles + theme token strategy |
| **Vercel dashboard redesign** | Project overview w/ deployment status; status reflected in browser tab; SWR for realtime-ish updates | Project-level home; live status hydration |
| **Supabase Design System** | Copy-paste component system (Radix + Tailwind + shadcn-inspired); UI patterns incl. **charts, empty states, forms, tables, layout**, theming | Concrete design-system reference for building Phronesis UI ✓ |
| **Dribbble references** | ML dashboard (Fuselab), AI Command Center (Botrix-style ops dashboard), AI dataset dashboard, Nixtio dashboard | Mood boards; mostly cautionary (heavy aesthetics) |

**Anti-patterns to avoid (observed in Dribbble AI-dashboard style):** purple
gradient noise, glassmorphism cards everywhere, unnecessary 3D, decorative
orb-busts, decorative glow on charts. Phronesis should look like a tool data
scientists already trust, not a landing page.

---

## 5. Design principles & visual direction

1. **Observability over automation-glamour.** The product IS its pipeline. Show
   the stages, the state each wrote, and the decisions taken. (LangGraph frontend
   principle: "explain what the system is doing instead of hiding execution".)
2. **Structure felt, not seen.** (Linear.) Dense information, soft borders,
   generous whitespace at focal points, restrained elevation.
3. **Every metric carries provenance.** Primary metric & whether it's
   higher-is-better; explainer type & sampled-flag; engine choice & reason;
   feature-selection counts. If the backend knows *why*, the UI says so.
4. **Progressive disclosure.** Top: run status + hero metric. Middle: stepper +
   artifacts. Deep: JSON payloads, raw logs, model file list, advanced config.
5. **Two consistent visual metaphors only:**
   - **The spine** (horizontal stepper/DAG) for *how a run is progressing*.
   - **The table** (runs list, leaderboard, artifacts, compare) for *what exists*.
6. **Honest failure & degradation.** Failed stage = red state, error type +
   message, link to logs. Missing optional feature = explicit "not available"
   with reason, mirroring `health()` degradation semantics.
7. **Dark mode first-class, not an afterthought** — ML users live in dark IDEs;
   both themes designed from tokens (Light-on-light decision below).
8. **Desktop-first, responsive-aware.** The analyst workflow is on a large
   monitor; tablets/phones get read-only "status check" experience (§14).

**Avoid:** generic "AI purple gradient" brand look; making charts decorative;
hiding pipeline internals behind a single chat bubble; forcing a node-editor as
the default view (Airflow already shows the simple stepper/grid is enough for a
linear graph).

---

## 6. Design system recommendations

- **Foundation:** Tailwind CSS v4 + `shadcn/ui`-style copy/paste components
  (mirrors Supabase's own approach — Radix primitives, Tailwind). Keeps the
  eventual frontend dependency-light and auditable.
- **Tokens:** semantic, HSL-based theme tokens (Linear-style) with `light` and
  `dark` variants: `--bg-surface`, `--bg-raised`, `--border-subtle`,
  `--border-default`, `--text-primary/secondary/muted`, `--accent`,
  `--status-pending/running/completed/failed/ambiguous`.
- **Status color system** (map 1:1 to run/stage states):
  - `running` → accent (blue); indeterminate pulse.
  - `completed` → green.
  - `failed` → red.
  - `ambiguous` / warning → amber (target detection, degraded deps).
  - `skipped`/`sampled` → neutral gray with "(sampled)" chip when
    `sampling_metadata` indicates sampling ran.
- **Typography:** a neutral UI sans (e.g. Inter/Geist-family), tabular numerals
  for all metrics (`font-variant-numeric: tabular-nums`), mono for IDs, paths,
  JSON, and the logs pipeline (e.g. Geist Mono / JetBrains Mono).
- **Data-viz:** Recharts/ECharts for line/bar/ROC/PR; custom beeswarm/force
  canvas for SHAP; confusion matrix as color grid, not chart lib. Consistent
  axis/grid styling tokens + hover tooltips with exact values.
- **Components catalogue (v1):** AppShell, primary/secondary nav, StageBadge,
  Stepper, StageCard, StatTile, DataTable (sort/filter/column-toggle), JSON viewer
  (collapsible), LogViewer (virtualized), MetricSparkline, ConfusionMatrix,
  LineChart/BarChart, LeaderboardRow, ModelCard, CompareTable (diff/toggle),
  CodeBlock, EmptyState, ErrorState, Toaster, Modal/Sheet (inspector), Kbd.
- **Icons:** a single consistent icon set (Lucide) — no mixed libraries.

---

## 7. Information architecture & navigation

Suggested IA (desktop app shell with left rail — SageMaker/Dagster-style):

```
PhronesisML
├── Home (workspace overview)
│     ├── recent runs
│     ├── quick "New run" entry
│     └── system health chip (from /health)
├── New run  (wizard: §9.2)
├── Runs
│     ├── Runs list  (from run_metadata.json)
│     └── Run detail  (tabs: Overview · Pipeline · EDA · Model · Explain · Reports · Artifacts · Logs)
├── Models (per-run best models; registry-lite)
│     └── Compare (§9.7)
├── Projects / datasets (*future* — roadmap "local run ledger")
│     └── Compare runs (§9.7)
└── Settings / System health (§9.9)
```

- **Left rail** = coarse navigation; **in-run tabs** = stage-grouped content;
  **right inspector sheet** = node/artifact detail (Dagster pattern).
- Naming mirrors backend functions (`analyze`, `train`, `explain`, `compare`,
  `health`) so docs ↔ UI vocabulary stays aligned.

---

## 8. User journeys

### 8.1 "Run my data and understand what happened" (primary)
1. Home → **New run** → upload file (drag-drop + path).
2. Wizard shows engine auto-selection (with reason) and stage-run-to selector
   (default: full pipeline).
3. Targeted run-configuration screen: preview detected target/task; confirm or
   override (`ambiguous` case forces confirmation).
4. Launch → **Pipeline screen** streams stage-by-stage (spine lights up),
   each stage card exposes its key state (rows, validation summary, top
   features, best model, metrics, SHAP summary).
5. On completion → **Overview** header: status badge, task type, target,
   engine, best model name + primary metric, "View report".
6. Either inspect tabs or open `report.html`/`report.md` from the artifacts tab.

### 8.2 "Which model is best and why?"
1. Run detail → Model tab shows leaderboard (AutoGluon/DataRobot style).
2. Best model hero with rationale (roadmap: WHY), click row → model card
   (params, training.json info, trials used, time).
3. Evaluation tab: confusion matrix, ROC/PR curves, per-class metrics;
   Explain tab: beeswarm + force, with explainer-type banner.

### 8.3 "Compare two runs"
1. Runs list → select 2+ runs → Compare.
2. Table of params & metrics with **diff-only toggle** (W&B Run Comparer).
3. Chosen metrics rendered side-by-side; stage-level diff (which stages differed,
   sampling flags).

### 8.4 "It failed — what happened?"
1. Run shows red stage in spine; Overview shows error card
   (`error_type` + message), stage hyperlink.
2. Logs tab auto-open at failure line; artifact view still browsable for what was
   saved before the halt (graceful degradation).

### 8.5 "Re-run a saved/prior run (resume)" *(future)*
- From run detail → "Fork" (LangGraph time-travel metaphor, roadmap
  `restore`/`load`). Checkpoint → adjust config → re-run.

---

## 9. Screen-by-screen specifications

> Each screen lists the concrete backing artifacts/fields (all exist today).

### 9.1 Home / Projects
- Header: product name, version (`version()`), New Run CTA, search.
- Cards: recent runs (run_metadata.json: `run_id`, `status`, `task_type`,
  `engine`, `best_pipeline`, counts), filterable; system-health chip from
  `health()` (`ok`/`degraded` with missing-deps tooltip).
- **Empty state** designed first (Supabase empty-states pattern): hero CTA, "how
  it works" 11-stage graphic, link to docs.

### 9.2 New Run wizard
Steps:
1. **Data** — upload / path input; on detection show `file_format`,
   sheet picker for Excel (`list_excel_sheets`), size + engine recommendation
   (pandas/polars/spark w/ reason, from engine thresholds).
2. **Scope** — stage filter ("Run through: Analyze / Clean / Validate / Target
   detection / Feature engineering / Model selection / Evaluate / Explain /
   Report / Full train") with checkmark table.
3. **Target & task** — auto-detected `target_column` + `task_type` +
   `target_detection_confidence` + `ambiguity_reason`; if `ambiguous`, require
   explicit confirm/override (interrupt pattern). Clustering/anomaly/simple
   task choices surface only when applicable (`detect_task` / `_STAGES_CLUSTER`
   / `_STAGES_ANOMALY`).
4. **Review & launch** — summary; POST `/api/runs`; on launch exit wizard to Run
   detail with live spine.

### 9.3 Run detail — Overview
- Header strip: status badge, `run_id` (mono, copyable), `data_path`, size,
  engine chip (with tooltip reason), task type, target column.
- Hero stat tiles: primary metric (task-aware), rows · columns, features used,
  time elapsed, `artifact_count`.
- Best-model hero: `best_pipeline` (model_type, score, trials_used,
  `truncated` flag, estimated cost).
- Failure card (when failed) + "open report".

### 9.4 Run detail — Pipeline (the spine)
Two view modes (Airflow-inspired; Langfuse aggregated/expanded rationale):
- **Stepper/Grid view (default):** horizontal sequence of the executed stages;
  each node colored by status; click → inspector sheet showing the agent's state
  contributions (map of `WorkflowState` region → fields) incl. sampling chip.
- **Graph view:** Airflow Graph-style DAG of actual executed nodes incl. hidden
  sampling nodes and routing paths, colored per run state (aggregated vs expanded
  toggle). **This uses React Flow + dagre/elkjs.**
- Left rail: per-node phases (upload/etl/validation/eda/target_detection/
  feature_engineering/model_selection/evaluation/explainability/reporting/storage)
  skip-links (Linear "structure felt not seen").

### 9.5 EDA / Data profile
- From `eda.json` / `data_profile` (shape, numeric_summary, categorical_summary,
  memory_bytes). Per-column cards (ydata-profiling pattern): histogram,
  null count, dtype, cardinality; dataset-level: duplicates, missing, memory.
- Validations summary (validation.json: counts, constraints); interactive
  transform log (`transform_log`, from etl) as a filterable event list.

### 9.6 Model / Leaderboard tab
- Task-aware leaderboard table (AutoGluon columns adapted to `training.json` +
  `metrics.json`): rank, model_type, primary metric (switchable), secondary
  metrics (expandable), `trials_used`, `time_elapsed`, `truncated` flag, and a
  **"✓ best"** badge (DataRobot). Sortable; higher-is-better always shown
  normalized with a caret.
- Row click → ModelCard sheet: params, hyperparameters, CV info.
- Evaluation section: `evaluation.json` + metrics; confusion-matrix grid;
  ROC/PR line charts; per-class stats; clustering/anomaly variants per task.

### 9.7 Compare (models & runs)
- `compare_models()` for in-run model comparison; `compare()` /
  `compare_async()` for cross-run. Diff-only toggle (W&B Run Comparer).
  Only actually-different params/metrics shown; identical values collapsed.
- Metric charts overlaid with legend.

### 9.8 Explainability / SHAP
- Banner: `explainer_type` (Tree/Linear/Permutation/Kernel) + `sampled` flag +
  `n_samples_used` (honesty requirement §5.3).
- Beeswarm (top `n` features, direction + magnitude + feature-value color), bar
  (mean abs), force plot for a selected sample (classification/regression).
- Data source: `shap.json` (`feature_importance` dict); render client-side.
- Stretch: per-sample waterfall, interaction view (SHAP `max_features` cap).

### 9.9 Reports & Artifacts
- **Reports:** rendered `report.md` → Markdown preview; `report.html` → iframe or
  download; PDF export (roadmap).
- **Artifacts browser:** tree of the 17 files (from `list_artifacts`/
  `build_artifact_manifest`); JSON preview w/ collapsible viewer; CSV/txt/md
  preview; download buttons (`load_artifact`).

### 9.10 Logs
- Virtualized monospace stream from `logs.txt`; auto-scroll/follow during running;
  highlight lines after failure; link from failure card (§8.4).

### 9.11 System health
- Table from `health()`: dependency, installed?, version → status `ok`/`degraded`
  chips (pandas, numpy, polars, sklearn, shap, langgraph, pydantic, joblib,
  pyarrow ± optional openpyxl/pyspark/mlflow/typer/rich). Degraded → explanation
  of which features are limited (e.g. spark disabled, Excel disabled). README/
  CLI mirror.

### 9.12 Runs list
- Columns: run_id, status, created, task_type, target, engine, best metric,
  rows/cols, duration, actions (open/compare/delete-local). Filters by status &
  task; search by run_id/target. Data 100% from `run_metadata.json`.

---

## 10. Real-time execution UX

**Current reality:** `WorkflowState.status` is one string; there is **no
event stream** and no stage timeline in state. Progress is only visible after the
run writes artifacts. So live progress requires a backend observability layer:

**Recommendation (layered, incremental):**
1. **v1 — Stage-event emission (backends change, documented in §11 as Proposed):**
   add a lightweight callback/stream in the scheduler layer that emits e.g.
   `{run_id, stage, status: started|completed|failed, summary, ts}` as the graph
   runs. Persist into state (e.g. `stage_events[]`) so completed runs reconstruct
   the same spine offline.
2. **Transport — SSE (recommended now) + polling for lists.** SSE for one-way
   progress + stage events (simple, proxy-friendly, standard `EventSource`);
   poll `GET /api/runs` every few seconds for list mutation ordering; JSON
   fallback if SSE unsupported. Design the event shape so it can later be
   upgraded to WebSocket for bidirectional controls (stop/cancel, fork) without
   changing the event model.
3. **UI behavior:** spine animates on SSE events; metrics hero ticks;
   artifacts tab refreshes per stage completion; tab title reflects status
   (Vercel pattern); optimistic transitions for `started→completed`.

**What the UI must not do:** fake progress bars. Per-stage instant state changes
derived from real events, or an indeterminate "running" state, is more honest.

---

## 11. Backend ↔ Frontend contract

**Important framing:** there is **no HTTP API** today (REST removed in v0.3.0,
SDK-first). Everything below is **Proposed** — a thin local server (FastAPI +
uvicorn serving the SDK in-process, static-served frontend beside it) that future
sessions would implement. Each row names the **existing SDK capability** that
backs the proposal, so implementation cost is largely a wrapper.

### 11.1 REST resources (all Proposed)

| Method | Endpoint | Existing capability that backs it | Notes |
|---|---|---|---|
| `GET` | `/api/health` | `health()` / `health_async()` | dep matrix, `ok`/`degraded` |
| `GET` | `/api/capabilities` | `capabilities()` | feature flags → UI gating |
| `GET` | `/api/runs` | read `Phronesis_artifacts/*/run_metadata.json` (+ `list_artifacts`) | list w/ filters |
| `GET` | `/api/runs/{run_id}` | `run_metadata.json` | summary header |
| `GET` | `/api/runs/{run_id}/artifacts` | `list_artifacts()`/`build_artifact_manifest()` | tree of the 17 files |
| `GET` | `/api/runs/{run_id}/artifacts/{name}` | `load_artifact()` | JSON/CSV/txt/md preview |
| `GET` | `/api/runs/{run_id}/logs` | file reader on `logs.txt` | stream/range |
| `POST` | `/api/runs` | `run_pipeline()` / stage-selected slices + `EngineConfig` | body: file path/upload, target override, stages |
| `GET` | `/api/runs/{run_id}/events` | **Proposed stage-event emitter (§10)** | SSE stream |
| `POST` | `/api/runs/{run_id}/stop` | **Proposed** (interrupt graph) | WebSocket/late upgrade |
| `GET` | `/api/runs/{run_id}/models` | `training.json` + `metrics.json` + `evaluation.json` | leaderboard payload |
| `GET` | `/api/runs/{run_id}/models/{type}/shap` | `shap.json` (`feature_importance` etc.) | client-rendered SHAP |
| `GET` | `/api/runs/compare?runs=…` | `compare()` / `compare_async()` | diff payload |
| `GET` | `/api/runs/{run_id}/report` | `load_artifact(report.md/html)` | preview/download/PDF(future) |
| `POST` | `/api/identity/profile` | `profile()` | optional standalone endpoints mirroring SDK |
| `GET` | `/api/version` | `version()` | header/health |

### 11.2 Event model (Proposed — powers the spine)

```jsonc
// GET /api/runs/{run_id}/events  (SSE)
event: stage
data: {"run_id":"4f7a…","stage":"eda","status":"completed",
       "summary":{"rows":10000,"nulls":12},"ts":"2026-09-19T10:00:00Z"}

event: run
data: {"run_id":"4f7a…","status":"completed","artifact_count":17,"ts":"…"}
```

Sampling nodes should emit `stage=model_selection`, `status=sampled`,
`summary={"sampled":true,"n_samples_used":20000}`.

### 11.3 Field mapping (existing artifacts → UI regions)

| UI region | Artifacts/fields (all exist) |
|---|---|
| Header/hero | `run_metadata.json`, `training.json` (`best_pipeline`) |
| Pipeline spine | `pipeline.json`, stage events (Proposed), routing labels |
| Data quality | `validation.json`, `transform_log` (via state/logs), `eda.json` |
| EDA | `eda.json` (`numeric_summary`, `categorical_summary`, shape, memory) |
| Target/task | `target_detection.json` (`target_column`, `task_type`, confidence, `ambiguity_reason`) |
| Features | `feature_metadata.json`, `feature_names` |
| Leaderboard | `training.json`, `metrics.json`, `evaluation.json` |
| Explainability | `shap.json` (`feature_importance`, `explainer_type`, `sampled`, `n_samples_used`) |
| Reports | `report.md`, `report.html` |
| Storage/artifacts | `config.json`, `engine_selection.json`, `resource_estimation.json`, `model.json`, `logs.txt` |

---

## 12. Error, empty & degraded states

- **Error taxonomy** mirrors `exceptions.py`: `ConfigurationError`,
  `DataLoadError` (bad file), `DataTransformError`, `DataValidationError`,
  `DataError`, `EngineSelectionError` (engine unavailable), `WorkflowError`,
  `AgentError` (with `error_type`/`error_message`). Each maps to a primary CTA
  (re-upload / reconfigure / view logs).
- **Failed run:** red stage badge on spine; Overview failure card; Logs tab
  auto-focused on last error; artifacts still browsable (what was persisted).
- **Degraded capability:** amber chip w/ tooltip ("shap explainer unavailable →
  fell back to permutation", "pyspark not installed — engine polars forced").
  Never render an empty chart with no explanation.
- **Empty states:** designed per screen (no runs yet, no results for a stage,
  no SHAP because explain step skipped) with the action that fills them.
- **Timestamp/timezone:** show `ts` in local time w/ tooltip ISO; durations
  humanized.

---

## 13. Accessibility

- **Contrast:** tokens meet WCAG 2.1 AA in both light & dark themes (verify
  status colors on surfaces; amber used with dark text).
- **Keyboard:** full navigation of spine, tables (row/column keyboard
  interaction), leaderboard sort, tabs, panels; visible focus rings.
- **ARIA:** stage badges + stepper roles (`aria-current`, live region for SSE
  status updates with `aria-live="polite"` — don't announce every tick);
  table column headers; charts get `role="img"` + an accessible data table or
  text summary; color is never the only channel (status also shown via icon +
  label).
- **Motion:** respect `prefers-reduced-motion` (no pulse animations); status
  changes also flash-free.
- **Zoom/fonts:** supports 200% zoom and font reflow (dense tables scroll
  horizontally rather than truncating data).

---

## 14. Responsive design

- **Desktop (primary, ≥1200px):** full left rail + in-run tabs + right
  inspector; data-dense.
- **Tablet (768–1199px):** rail collapses to icons; inspector overlays as sheet;
  leaderboard horizontal-scrolls.
- **Phone (<768px):** read-only status experience: Home summary, run list, run
  status + hero metric, pipeline spine (vertical stepper), logs. Authoring
  (new-run wizard) moves behind "on desktop" prompt; compare read-only.
- Justification: analysts operate on desktop; mobile serves "is it done / did it
  pass / what's the metric" checks. Vercel's own redesign explicitly treated
  mobile as a read side of the product.

---

## 15. Frontend tech stack recommendation

| Layer | Choice | Why |
|---|---|---|
| Framework | React 19 + TypeScript + Vite | ecosystem fit; LangGraph/React Flow/Radix all React |
| Routing/state | TanStack Router/Query + Zustand | server-state for REST, client-state for UI; SSE via keepalive query or manual |
| Styling | Tailwind CSS v4 + shadcn/ui-style local components | Supabase/Linear-style token system; no heavy UI kit |
| Charts | Recharts or Apache ECharts | line/bar/ROC/PR; beeswarm/force custom-rendered |
| Graph/DAG | `@xyflow/react` (React Flow) + dagre or elkjs | linear stepper + optional graph view; minimap, `onlyRenderVisibleElements` |
| Markdown | react-markdown | `report.md` preview |
| Logs/JSON | virtualized list + collapsible JSON viewer | large `logs.txt`, 17 artifacts previews |
| Server (proposed wrapper) | FastAPI + uvicorn (async), SSE | in-process SDK; serves static `dist/` |
| Testing | Vitest + React Testing Library + Playwright (E2E) | follow repo Testing.md practice |

---

## 16. Implementation blueprint & priorities

### Must (v1 — read + run inspection)
1. App shell + theme tokens (light/dark) + Home + System health.
2. Runs list (metadata-driven).
3. New Run wizard v1: file, scope slicer, target/task confirm (`ambiguous`
   flow), review.
4. Run detail: Overview, Pipeline spine (stepper + SSE), Logs, artifacts
   browser, Reports preview.
5. Model tab: leaderboard (switchable metric), model card, evaluation charts.
6. Error/failure/empty/degraded states (full §12).

### Should (v1.5)
7. Stage-event stream + SSE backend adapter (§10/§11); running-state metrics
   dwell.
8. Explainability tab (beeswarm/bar/force from `shap.json`) + explainer banner.
9. Compare (runs & models) with diff-only toggle.
10. Pipeline Graph view (React Flow) — aggregated/expanded toggle; inspector sheet.
11. Keyboard/ARIA completeness pass + Playwright E2E.
12. Artifact manifest endpoint polish + search/filter runs.

### Future (roadmap-aligned; Phronesis Roadmap phase 2/3)
13. Model recommendation with WHY visible in leaderboard hero.
14. Local run ledger → project-level grouping + drift check surfaces.
15. Fork/re-run from checkpoint (LangGraph time-travel metaphor).
16. PDF report export + pipeline serialization preview.
17. ONNX/model registry integration surfaces.
18. Embeddable read-only widget (iframe) for `report.html`-adjacent sharing.

### Sequencing rationale
Backend observability (stage events) is the only cross-cutting *backend* change
and is intentionally isolated (isolated contract §10/§11) so v1 read-only works
fully without it; everything else is a wrapper around existing artifacts.

---

## 17. Risks & open questions

- **SSE vs WebSocket vs polling:** settled here as SSE+list-poll; validate with
  localhost proxies (no CORS prod concerns in-process, but design tokens anyway).
- **Large `logs.txt` / big `eda.json`:** need server-side range/limit + client
  virtualization (bounded). Confirm typical sizes during v1.
- **Spark/pyspark absent:** engine chips must be honest about unavailable engines
  (`EngineSelectionError` path) — affects both wizard and failure UX.
- **`compare()` semantics:** confirm whether cross-run compare requires same
  schema/task; UI should guard and explain (W&B diff-only handles heterogeneity,
  we mirror that).
- **Report.html iframe sandboxing:** serving `report.html` from the same server
  in an iframe is fine; define CSP so generated HTML cannot script the app.
- **Artifact format stability:** 17-file layout is current source of truth;
  the runs reader must tolerate missing files (graceful degradation, matching
  backend philosophy).
- **Does "ambiguous" target ever require user override inside a purely-staged
  run?** Confirm wizard interruption semantics with the workflow interrupt
  mechanism before building fork/resume.

---

## 18. Reference links

### AutoML & leaders / leaderboards
- DataRobot Model Leaderboard — https://docs.datarobot.com/11.1/en/docs/workbench/wb-experiment/manage-experiments/leaderboard.html
- H2O AutoML (leaderboard, stopping criteria, ensembles) — https://s3.amazonaws.com/h2o-release/h2o/master/4765/docs-website/h2o-docs/automl.html
- AutoGluon `TabularPredictor.leaderboard` — https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.leaderboard.html
- Azure ML AutoML job → models + child jobs (no-code tutorial) — https://docs.azure.cn/en-us/machine-learning/tutorial-automated-ml-forecast?view=azureml-api-2
- Oracle OML AutoML UI experiments/leaderboard — https://docs.oracle.com/en/database/oracle/machine-learning/oml-automl-ui/amlui/view-experiment.html

### Experiment tracking
- MLflow Tracking UI — https://mlflow.org/docs/latest/tracking/index.html
- Databricks MLflow Experiments UI (chart view) — https://www.databricks.com/blog/accelerate-your-model-development-new-mlflow-experiments-ui
- W&B Experiments — https://docs.wandb.ai/models/track
- W&B Run Comparer (diff-only) — https://docs.wandb.ai/models/app/features/panels/run-comparer
- SageMaker Studio UI — https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-ui.html
- SageMaker Experiments — https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-mlops.html / https://github.com/aws/sagemaker-experiments
- SageMaker Model Dashboard — https://docs.aws.amazon.com/sagemaker/latest/dg/model-dashboard.html
- Vertex AI Experiments — https://docs.cloud.google.com/vertex-ai/docs/experiments/intro-vertex-ai-experiments

### Pipeline / DAG UIs
- Airflow 3 UI overview (Grid/Graph/Runs, themes) — https://airflow.apache.org/docs/apache-airflow/stable/ui.html
- Dagster UI / webserver — https://docs.dagster.io/guides/operate/webserver
- Azure ML Designer — https://learn.microsoft.com/en-us/azure/machine-learning/concept-designer?view=azureml-api-1
- React Flow — https://reactflow.dev/ ; ELK layout example — https://reactflow.dev/examples/layout/elkjs

### Agentic / LangGraph visualization
- LangSmith Studio (LangGraph) — https://docs.langchain.com/langsmith/studio
- LangGraph frontend SDK patterns (nodes→cards, state→regions, interrupts) — https://docs.langchain.com/oss/python/langgraph/frontend/overview.md
- Langfuse Agent Graphs (aggregated vs expanded) — https://langfuse.com/docs/observability/features/agent-graphs

### Explainability & data profiling
- SHAP beeswarm — https://shap.readthedocs.io/en/latest/example_notebooks/api_examples/plots/beeswarm.html
- SHAP force plot — https://shap.readthedocs.io/en/latest/generated/shap.plots.force.html
- Azure Responsible AI insights UI — https://docs.azure.cn/en-us/machine-learning/how-to-responsible-ai-insights-ui
- ydata-profiling — https://docs.profiling.ydata.ai/latest/getting-started/quickstart

### Developer-tool aesthetics & design systems
- Linear design refresh (principles) — https://linear.app/now/behind-the-latest-design-refresh
- Linear UI redesign notes — https://linear.app/now/how-we-redesigned-the-linear-ui
- Vercel dashboard redesign (status-in-tab, SWR) — https://vercel.com/blog/dashboard-redesign
- Supabase Design System (components, charts/empty-state/table patterns) — https://supabase-design-system.vercel.app/

### Design inspiration (caution use)
- Dribbble: ML Dashboard UI (Fuselab Creative) — https://dribbble.com/shots/17361656-Machine-Learning-Dashboard-UI-Design
- Dribbble: AI Command Center Dashboard — https://dribbble.com/shots/27355196-AI-Command-Center-Dashboard-Design
- Dribbble: AI Dataset Dashboard (Exalt Studio) — https://dribbble.com/search/dashboard-machine
- Dribbble: Nixtio Dashboard UI — https://dribbble.com/shots/25683483-Dashboard-UI

---

## Appendix A — One-line recaps per section

- **Repo:** stage slices + `WorkflowState` + 17-file artifact layout fully power a read-only inspector today; only the live *streaming* layer is missing.
- **Research:** three dominant paradigms — workflow spine (Airflow/Dagster/LangGraph), ranked leaderboard (DataRobot/H2O/AutoGluon/MLflow/W&B/Azure), and diff-based compare (W&B) — plus honest explainability (SHAP/Azure RAI) and data-friendly developer aesthetics (Linear/Vercel/Supabase).
- **Design:** developer-platform look, token-based light/dark themes, metric provenance everywhere, failure-friendly, progressive disclosure toward raw JSON/logs.
- **Contract:** everything `Proposed`; each endpoint maps to an existing `sdk.py` capability so v1 cost is thin-wrapping + one SSE emitter.
- **Priorities:** Must = runs inspection + pipeline spine + leaderboard; Should = SSE, SHAP tab, compare, DAG view; Future = fork/resume, WHY rationale, model registry, PDF.