"""Phronesis public SDK — the clean developer-facing API.

This module provides the ``Phronesis`` class, a thin facade over the
internal LangGraph workflow.  Developers interact with meaningful ML
operations; the SDK handles orchestration, state management, and
engine selection internally.

Usage::

    from phronesisml import Phronesis

    ml = Phronesis("data.csv")
    ml.run()                     # execute the full pipeline
    report = ml.report()         # get the Markdown report
    summary = ml.summary()       # get dataset summary

The advanced API (``run_pipeline``, ``WorkflowState``, stage lists)
remains available for users who need full control.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401 — used only in type annotations

logger = logging.getLogger(__name__)


def _to_df(data: Any) -> Any:
    """Ensure data is a pandas DataFrame (lazy import)."""
    import pandas as pd

    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame(data)


# ── Typed result objects ─────────────────────────────────────────


@dataclass(frozen=True)
class DatasetSummary:
    """Structured summary of a loaded dataset."""

    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    memory_bytes: int
    missing_values: dict[str, int]
    duplicate_rows: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    preview: Any  # pd.DataFrame — deferred to avoid eager pandas import

    @property
    def memory_mb(self) -> float:
        """Memory usage in megabytes."""
        return self.memory_bytes / (1024 * 1024)


@dataclass(frozen=True)
class ValidationReport:
    """Result of data validation checks."""

    passed: bool
    rows: int
    columns: int
    null_counts: dict[str, int]
    null_columns: list[str]
    empty_columns: list[str]
    duplicate_rows: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class EDAReport:
    """Exploratory data analysis results."""

    shape: tuple[int, int]
    numeric_columns: list[str]
    categorical_columns: list[str]
    numeric_summary: dict[str, Any]
    categorical_summary: dict[str, Any]
    memory_bytes: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class TargetInfo:
    """Result of automatic target detection."""

    column: str
    task_type: str
    confidence: float
    ambiguity_reason: str | None
    candidates: list[dict[str, Any]]


@dataclass(frozen=True)
class FeatureReport:
    """Result of feature engineering."""

    feature_names: list[str]
    n_features: int
    n_rows: int
    features: Any  # pd.DataFrame — deferred to avoid eager pandas import


@dataclass(frozen=True)
class ModelInfo:
    """Recommended model details."""

    model_type: str
    score: float
    candidates: list[dict[str, Any]]
    best_params: dict[str, Any]
    truncated: bool
    trials_used: int
    time_elapsed: float
    estimated_training_cost: str = "unknown"


@dataclass(frozen=True)
class EvaluationMetrics:
    """Model evaluation results."""

    accuracy: float | None = None
    precision_macro: float | None = None
    recall_macro: float | None = None
    f1_macro: float | None = None
    roc_auc: float | None = None
    confusion_matrix: list[list[int]] | None = None
    rmse: float | None = None
    mae: float | None = None
    r2: float | None = None
    ambiguity_caveat: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExplanationReport:
    """SHAP-based model explanation results."""

    feature_importance: dict[str, float]
    explainer_type: str
    sampled: bool
    n_samples_used: int
    n_features_used: int = 0
    max_samples: int = 0


@dataclass(frozen=True)
class ClusteringReport:
    """Clustering analysis results."""

    algorithm: str
    n_clusters: int
    silhouette_score: float | None
    davies_bouldin_score: float | None
    calinski_harabasz_score: float | None
    cluster_labels: list[int]
    params: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnomalyReport:
    """Anomaly detection results."""

    algorithm: str
    n_anomalies: int
    contamination: float
    anomaly_labels: list[int]
    anomaly_scores: list[float]
    params: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskInfo:
    """Result of unified task detection."""

    task_type: str
    target_column: str | None
    confidence: float
    ambiguity_reason: str | None
    candidates: list[dict[str, Any]]


@dataclass(frozen=True)
class ModelComparison:
    """Ranked comparison of multiple trained models.

    Produced by :meth:`Phronesis.compare` and the ``simple.compare``
    function.  ``ranking`` is best-first, sorted by the task's primary
    metric.
    """

    task_type: str
    primary_metric: str
    higher_is_better: bool
    ranking: list[dict[str, Any]]
    models: list[dict[str, Any]]

    @property
    def best_model(self) -> str | None:
        """Name of the top-ranked model, or ``None`` if no models were compared."""
        return self.ranking[0]["model"] if self.ranking else None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the comparison."""
        return {
            "task_type": self.task_type,
            "primary_metric": self.primary_metric,
            "higher_is_better": self.higher_is_better,
            "ranking": self.ranking,
            "models": self.models,
        }


@dataclass(frozen=True)
class SavedRun:
    """A restored artifact run, loadable with ``Phronesis.restore()``.

    Holds the persisted trained model, its transform recipe, and run
    metadata so predictions can be reproduced offline without re-running
    the pipeline.
    """

    run_id: str
    model: Any
    task_type: str
    target_column: str | None
    feature_names: list[str]
    feature_transform: dict[str, Any] | None
    config: dict[str, Any]
    metadata: dict[str, Any]
    model_info: dict[str, Any]

    @classmethod
    def from_directory(cls, directory: str | Path) -> SavedRun:
        """Restore a saved run from an artifact directory.

        Reads ``run_metadata.json``, ``model.json``,
        ``feature_metadata.json``, ``config.json``, and ``model.joblib``
        from *directory*.

        Args:
            directory: The artifact directory produced by
                :meth:`Phronesis.save`.

        Returns:
            A ``SavedRun`` ready for offline prediction.

        Raises:
            FileNotFoundError: If any required artifact file is missing.
        """
        base = Path(directory)

        def _read_json(name: str) -> dict[str, Any]:
            path = base / name
            if not path.is_file():
                msg = f"Saved run artifact missing: {path}"
                raise FileNotFoundError(msg)
            data = json.loads(path.read_text(encoding="utf-8"))
            return dict(data)

        run_metadata = _read_json("run_metadata.json")
        model_info = _read_json("model.json")
        feature_metadata = _read_json("feature_metadata.json")
        config = _read_json("config.json")

        model_path = base / "model.joblib"
        if not model_path.is_file():
            msg = f"Saved model missing: {model_path}"
            raise FileNotFoundError(msg)

        import joblib

        return cls(
            run_id=run_metadata.get("run_id", base.name),
            model=joblib.load(model_path),
            task_type=run_metadata.get("task_type") or "unknown",
            target_column=run_metadata.get("target_column"),
            feature_names=list(feature_metadata.get("feature_names", [])),
            feature_transform=feature_metadata.get("feature_transform"),
            config=config,
            metadata=run_metadata,
            model_info=model_info,
        )

    def predict(self, data: Any, already_engineered: bool = False) -> list[Any]:
        """Predict on new rows using the restored model.

        Args:
            data: Raw rows shaped like the training data (the target
                column, if present, is ignored) — or, when
                *already_engineered* is ``True``, a DataFrame in the
                trained feature space.
            already_engineered: ``True`` to skip recipe transformation.

        Returns:
            A list of model predictions (one per input row).

        Raises:
            ValueError: If the recipe is missing but required.
            DataTransformError: If the input cannot be transformed.
        """
        import pandas as pd

        if self.model is None:
            msg = "Saved run contains no trained model."
            raise ValueError(msg)

        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)

        if already_engineered:
            missing = [c for c in self.feature_names if c not in df.columns]
            if missing:
                msg = f"Prediction data is missing engineered feature columns: {missing}"
                raise ValueError(msg)
            features = df[list(self.feature_names)]
        else:
            if not self.feature_transform:
                msg = (
                    "Saved run has no transform recipe. Pass "
                    "'already_engineered=True' with engineered features."
                )
                raise ValueError(msg)
            from phronesisml.ml.feature_engineering.transform import apply_transform_recipe

            features = apply_transform_recipe(df, self.feature_transform)

        return list(self.model.predict(features))


# ── Internal engine bootstrap (lazy, lightweight) ────────────────


def _make_engine(
    config: Any | None = None,
    data_path: str | None = None,
) -> Any:
    """Build a computation engine via the engine selector."""
    from phronesisml.configs.settings import PhronesisConfig
    from phronesisml.engines.engine_selector import select_engine

    if config is None:
        config = PhronesisConfig()
    return select_engine(config=config, data_path=data_path)


def _make_agents(
    engine: Any,
    config: Any | None = None,
    agent_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compose all agents with the given engine and config.

    Delegates to the canonical ``compose_agents()`` function.
    *agent_overrides* are forwarded as constructor-kwarg overrides
    (e.g. ``{"model_selection": {"cv": 5}}``).
    """
    from phronesisml.agents.compose import compose_agents
    from phronesisml.configs.settings import PhronesisConfig

    if config is None:
        config = PhronesisConfig()

    return compose_agents(
        engine=engine,
        config=config,
        agent_overrides=agent_overrides,
    )


# ── Pipeline stage definitions ───────────────────────────────────

_UPLOAD = ["upload"]
_ETL = ["upload", "etl"]
_VALIDATION = _ETL + ["validation"]
_EDA = _VALIDATION + ["eda"]
_TARGET = _EDA + ["target_detection"]
_FEATURES = _TARGET + ["feature_engineering"]
_MODEL = _FEATURES + ["model_selection"]
_EVALUATION = _MODEL + ["evaluation"]
_EXPLAIN = _EVALUATION + ["explainability"]
_REPORT = _EXPLAIN + ["reporting"]
_FULL = _REPORT + ["storage"]

# ── Execution modes ──────────────────────────────────────────────
# Fast: skip explainability and storage (most expensive stages)
_FAST = _EVALUATION + ["reporting"]
# Balanced: default (full pipeline)
_BALANCED = _FULL
# Full: complete execution (same as balanced, explicit for clarity)
_FULL_MODE = _FULL

_UNSUPERVISED_STAGES = [
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "reporting",
]
_CLUSTERING = _EDA + _UNSUPERVISED_STAGES
_ANOMALY = _EDA + _UNSUPERVISED_STAGES

_STAGE_MAP: dict[str, list[str]] = {
    "load": _UPLOAD,
    "clean": _ETL,
    "validate": _VALIDATION,
    "eda": _EDA,
    "detect_target": _TARGET,
    "engineer_features": _FEATURES,
    "recommend_model": _MODEL,
    "train": _MODEL,
    "evaluate": _EVALUATION,
    "explain": _EXPLAIN,
    "report": _REPORT,
    "run": _FULL,
}


# ── Public SDK class ─────────────────────────────────────────────


class Phronesis:
    """High-level SDK for automated machine learning.

    ``Phronesis`` provides an intuitive interface over the internal
    LangGraph pipeline.  Every method delegates to existing agents
    without duplicating business logic.

    Args:
        data_path: Path to a dataset (CSV, Excel, JSON, Parquet, etc.).
        config: Optional ``PhronesisConfig``.  If ``None``, defaults are
            used and can be overridden via property setters.

    Example::

        from phronesisml import Phronesis

        ml = Phronesis("customers.csv")
        ml.run()
        print(ml.report())
    """

    def __init__(
        self,
        data_path: str,
        config: Any | None = None,
        agent_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        from phronesisml.configs.settings import PhronesisConfig
        from phronesisml.workflow.state import WorkflowState

        self._data_path = data_path
        self._config = config or PhronesisConfig()
        self._agent_overrides = agent_overrides
        self._state = WorkflowState(data_path=data_path)
        self._engine: Any = None
        self._agents: dict[str, Any] = {}
        self._executed_stages: set[str] = set()
        self._start_time: float | None = None

    # ── Lazy internal helpers ──────────────────────────────────────

    @property
    def _eng(self) -> Any:
        """Lazy-initialise the computation engine."""
        if self._engine is None:
            self._engine = _make_engine(self._config, self._data_path)
        return self._engine

    def _get_agents(self) -> dict[str, Any]:
        """Lazy-initialise agents (only once)."""
        if not self._agents:
            self._agents = _make_agents(
                self._eng,
                self._config,
                agent_overrides=self._agent_overrides,
            )
        return self._agents

    async def _run_stages(self, stages: list[str]) -> None:
        """Execute the requested pipeline stages via LangGraph.

        Deduplicates: if stages A..B have already been executed,
        only runs the remaining stages.
        """
        from phronesisml.workflow.graph import build_graph

        # Determine what still needs to run
        already = self._executed_stages
        needed = [s for s in stages if s not in already]
        if not needed:
            logger.debug("All requested stages already executed — skipping.")
            return

        # Build graph with only the needed stages — previously executed
        # stages are skipped; their outputs already live in self._state.
        agents = self._get_agents()
        graph = build_graph(
            agents,
            stages=needed,
            sampling_config=self._config.sampling,
            engine=self._eng,
        )

        if self._start_time is None:
            self._start_time = time.monotonic()

        # ── Populate run metadata (BUG-05 fix) ────────────────────────
        # run_id/status are owned by no agent; the SDK stamps them here so
        # reports and storage always carry a real identifier/status.
        if self._state.run_id is None:
            self._state.run_id = f"run_{uuid4().hex}"
        self._state.status = "running"

        # ── SDK metadata stamps ────────────────────────────────────────
        # Config and engine snapshots feed reporting/storage artifacts and
        # are owned by the SDK (no agent writes them).
        if self._state.config_snapshot is None:
            self._state.config_snapshot = self._config.model_dump(mode="json")
        if self._state.engine_name is None:
            engine_cls = type(self._eng).__name__
            self._state.engine_name = engine_cls.removesuffix("Engine").lower()

        logger.info(
            "Phronesis: running %d stages: %s",
            len(needed),
            " → ".join(needed),
        )

        t0 = time.perf_counter()
        try:
            from phronesisml.exceptions import WorkflowError

            final_state = await graph.ainvoke(self._state)
        except WorkflowError:
            self._state.status = "failed"
            raise
        except Exception as exc:
            self._state.status = "failed"
            from phronesisml.exceptions import WorkflowError

            raise WorkflowError(f"Pipeline execution failed: {exc}") from exc

        elapsed = time.perf_counter() - t0
        logger.info(
            "Phronesis: stages complete in %.2fs (%d stages executed).",
            elapsed,
            len(needed),
        )

        # Merge returned state into our accumulated state — avoid
        # model_dump() which serialises DataFrames and models to dicts.
        if hasattr(final_state, "model_fields_set"):
            for key in final_state.model_fields_set:
                setattr(self._state, key, getattr(final_state, key))
        elif isinstance(final_state, dict):
            for key, value in final_state.items():
                if value is not None:
                    setattr(self._state, key, value)

        # Mark the run complete AFTER merging, so the initial state's
        # "running" stamp isn't copied back over it (BUG-05 fix).
        self._state.status = "completed"

        # Re-render the final report so its header reflects the terminal
        # status — the reporting node rendered it while status was still
        # "running" (BUG-05 fix).
        if "reporting" in needed and self._state.final_report is not None:
            from phronesisml.ml.reports.builder import build_report

            self._state.final_report = build_report(self._state)

        self._executed_stages.update(stages)

    def _ensure_sync(self, stages: list[str]) -> None:
        """Run stages synchronously via asyncio.run()."""
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "Cannot call synchronous Phronesis methods from inside a running "
                "event loop (e.g. inside FastAPI or Jupyter async mode). "
                "Use the _async variants or await _run_stages() directly."
            )
        asyncio.run(self._run_stages(stages))

    # ── Public properties ──────────────────────────────────────────

    @property
    def data_path(self) -> str:
        """Path to the input dataset."""
        return self._data_path

    @property
    def config(self) -> Any:
        """The current ``PhronesisConfig``."""
        return self._config

    @property
    def state(self) -> Any:
        """The internal ``WorkflowState`` (advanced usage)."""
        return self._state

    @property
    def elapsed(self) -> float | None:
        """Seconds elapsed since the first stage was executed, or ``None``."""
        if self._start_time is None:
            return None
        return time.monotonic() - self._start_time

    # ── Stage methods ──────────────────────────────────────────────

    def load(self) -> Phronesis:
        """Load the dataset from disk.

        Detects file format automatically.  For Excel files with
        multiple sheets, selects the sheet with the most data.

        Returns:
            ``self`` for method chaining.
        """
        self._ensure_sync(_UPLOAD)
        return self

    def summary(self) -> DatasetSummary:
        """Return a structured summary of the loaded dataset.

        Runs ``load()`` automatically if not already done.

        Returns:
            A ``DatasetSummary`` with rows, columns, dtypes, memory,
            missing values, duplicates, and a preview DataFrame.
        """
        self._ensure_sync(_UPLOAD)

        df = self._state.raw_data
        if df is None:
            raise ValueError("No data loaded.")

        collected = _to_df(df)
        missing = collected.isnull().sum().to_dict()
        numeric_cols = collected.select_dtypes(include="number").columns.tolist()
        cat_cols = collected.select_dtypes(exclude="number").columns.tolist()

        return DatasetSummary(
            rows=len(collected),
            columns=len(collected.columns),
            column_names=list(collected.columns),
            dtypes={c: str(d) for c, d in collected.dtypes.items()},
            memory_bytes=int(collected.memory_usage(deep=True).sum()),
            missing_values={k: int(v) for k, v in missing.items() if v > 0},
            duplicate_rows=int(collected.duplicated().sum()),
            numeric_columns=numeric_cols,
            categorical_columns=cat_cols,
            preview=collected.head(5),
        )

    def clean(
        self,
        null_strategy: str | None = None,
    ) -> Phronesis:
        """Clean and transform raw data (ETL stage).

        Applies null handling, type casting, and categorical encoding.

        Args:
            null_strategy: ``"drop"``, ``"fill"``, or ``"flag"``.
                Overrides the constructor default if provided.

        Returns:
            ``self`` for method chaining.
        """
        self._ensure_sync(_UPLOAD)

        if null_strategy is not None:
            from phronesisml.agents.etl.agent import ETLAgent, ETLConfig

            agents = self._get_agents()
            agents["etl"] = ETLAgent(config=ETLConfig(null_strategy=null_strategy))
            from phronesisml.workflow.graph import clear_graph_cache

            clear_graph_cache()

        self._ensure_sync(_ETL)
        return self

    def validate(self) -> ValidationReport:
        """Run data validation checks.

        Checks: empty data, zero columns, null analysis, duplicates.

        Returns:
            A ``ValidationReport`` with pass/fail status and details.
        """
        self._ensure_sync(_VALIDATION)

        report = self._state.validation_report or {}
        validated = self._state.validated_data
        n_rows, n_cols = (0, 0)
        if validated is not None:
            df = _to_df(validated)
            n_rows, n_cols = df.shape

        return ValidationReport(
            passed=report.get("passed", False),
            rows=n_rows,
            columns=n_cols,
            null_counts=report.get("null_counts", {}),
            null_columns=report.get("null_columns", []),
            empty_columns=report.get("empty_columns", []),
            duplicate_rows=report.get("duplicate_rows", 0),
            raw=report,
        )

    def eda(self) -> EDAReport:
        """Run exploratory data analysis.

        Computes statistical summaries, distributions, correlations,
        and column-level insights.

        Returns:
            An ``EDAReport`` with numeric/categorical summaries.
        """
        self._ensure_sync(_EDA)

        profile = self._state.data_profile or {}
        return EDAReport(
            shape=tuple(profile.get("shape", {"rows": 0, "columns": 0}).values())
            if isinstance(profile.get("shape"), dict)
            else (0, 0),
            numeric_columns=profile.get("numeric_columns", []),
            categorical_columns=profile.get("categorical_columns", []),
            numeric_summary=profile.get("numeric_summary", {}),
            categorical_summary=profile.get("categorical_summary", {}),
            memory_bytes=profile.get("memory_bytes", 0),
            raw=profile,
        )

    def detect_target(
        self,
    ) -> TargetInfo:
        """Automatically detect the prediction target and task type.

        Returns:
            A ``TargetInfo`` with the detected column, task type,
            confidence, and reasoning.
        """
        self._ensure_sync(_TARGET)

        return TargetInfo(
            column=self._state.target_column or "",
            task_type=self._state.task_type or "unknown",
            confidence=self._state.target_detection_confidence or 0.0,
            ambiguity_reason=self._state.ambiguity_reason,
            candidates=[],
        )

    def engineer_features(self) -> FeatureReport:
        """Engineer features: encode, scale, handle outliers, select.

        Returns:
            A ``FeatureReport`` with the engineered feature names
            and the resulting DataFrame.
        """
        self._ensure_sync(_FEATURES)

        features = self._state.features
        if features is not None:
            df = _to_df(features)
        else:
            import pandas as pd

            df = pd.DataFrame()

        return FeatureReport(
            feature_names=self._state.feature_names or [],
            n_features=len(self._state.feature_names or []),
            n_rows=len(df),
            features=df,
        )

    def recommend_model(self, cv: int | None = None, model_type: str | None = None) -> ModelInfo:
        """Recommend and train the best model for the dataset.

        Evaluates multiple candidate models and selects the best one
        based on cross-validation performance.

        Args:
            cv: Number of cross-validation folds.  If ``None``
                (default), uses a single train/test split.  Pass an
                integer ≥ 2 to enable k-fold cross-validation.
            model_type: Optional name of a specific model to train
                (e.g. ``"random_forest"``).  If provided, trains only
                that model instead of selecting the best from all
                candidates.

        Returns:
            A ``ModelInfo`` with the selected model, score, candidates,
            training details, and estimated cost.
        """
        if cv is not None or model_type is not None:
            from phronesisml.agents.model_selection.agent import ModelSelectionAgent

            agents = self._get_agents()
            agents["model_selection"] = ModelSelectionAgent(
                engine=self._eng,
                cv=cv,
                model_type=model_type,
            )
            from phronesisml.workflow.graph import clear_graph_cache

            clear_graph_cache()
        self._ensure_sync(_MODEL)

        bp = self._state.best_pipeline or {}
        return ModelInfo(
            model_type=bp.get("model_type", "unknown"),
            score=bp.get("score", 0.0),
            candidates=self._state.candidate_models or [],
            # Prefer "best_params"; fall back to legacy "params" (BUG-04 fix).
            best_params=bp.get("best_params") or bp.get("params", {}),
            truncated=bp.get("truncated", False),
            trials_used=bp.get("trials_used", 0),
            time_elapsed=bp.get("time_elapsed", 0.0),
            estimated_training_cost=bp.get("estimated_training_cost", "unknown"),
        )

    def train(self, cv: int | None = None, model_type: str | None = None) -> ModelInfo:
        """Alias for ``recommend_model()``.

        Trains the recommended model on the engineered features.

        Args:
            cv: Number of cross-validation folds.  If ``None``
                (default), uses a single train/test split.
            model_type: Optional name of a specific model to train.

        Returns:
            A ``ModelInfo``.
        """
        return self.recommend_model(cv=cv, model_type=model_type)

    def evaluate(self) -> EvaluationMetrics:
        """Evaluate the trained model.

        Computes task-appropriate metrics (accuracy, precision, recall,
        F1 for classification; RMSE, MAE, R2 for regression).

        Returns:
            An ``EvaluationMetrics`` with all computed metrics.
        """
        self._ensure_sync(_EVALUATION)

        report = self._state.evaluation_report or {}
        metrics = report.get("metrics", {})

        return EvaluationMetrics(
            accuracy=metrics.get("accuracy"),
            precision_macro=metrics.get("precision_macro"),
            recall_macro=metrics.get("recall_macro"),
            f1_macro=metrics.get("f1_macro"),
            roc_auc=metrics.get("roc_auc"),
            confusion_matrix=metrics.get("confusion_matrix"),
            rmse=metrics.get("rmse"),
            mae=metrics.get("mae"),
            r2=metrics.get("r2"),
            ambiguity_caveat=report.get("ambiguity_caveat"),
            raw=report,
        )

    def explain(self) -> ExplanationReport:
        """Explain model predictions using SHAP.

        Computes feature importance based on SHAP values.  SHAP is a
        core dependency and is always available.

        Returns:
            An ``ExplanationReport`` with feature importance scores.
        """
        self._ensure_sync(_EXPLAIN)

        report = self._state.explanation_report or {}
        return ExplanationReport(
            feature_importance=report.get("feature_importance", {}),
            explainer_type=report.get("explainer_type", "none"),
            sampled=report.get("sampled", False),
            n_samples_used=report.get("n_samples_used", 0),
            n_features_used=report.get("n_features_used", 0),
            max_samples=report.get("max_samples", 0),
        )

    def detect_task(
        self,
    ) -> TaskInfo:
        """Detect the ML task type (supervised or unsupervised).

        Runs upload through target detection. Returns the detected
        task type which may be classification, regression, clustering,
        anomaly_detection, or analytics.

        Args:
            force_task: Optional override to force a specific task type.

        Returns:
            A ``TaskInfo`` with task_type, target_column, confidence,
            and ambiguity reasoning.
        """
        self._ensure_sync(_TARGET)

        return TaskInfo(
            task_type=self._state.task_type or "unknown",
            target_column=self._state.target_column,
            confidence=self._state.target_detection_confidence or 0.0,
            ambiguity_reason=self._state.ambiguity_reason,
            candidates=[],
        )

    def cluster(
        self,
        n_clusters: int | None = None,
        algorithms: list[str] | None = None,
    ) -> ClusteringReport:
        """Run clustering analysis on the dataset.

        Executes upload through clustering evaluation. Automatically
        selects the best clustering algorithm (KMeans, DBSCAN,
        Agglomerative) based on silhouette score.

        Args:
            n_clusters: Optional hint for number of clusters.
            algorithms: Optional list of algorithms to try.

        Returns:
            A ``ClusteringReport`` with algorithm, scores, labels.
        """
        if n_clusters is not None or algorithms is not None:
            self._state.clustering_n_clusters = n_clusters
            self._state.clustering_algorithms = algorithms
            from phronesisml.workflow.graph import clear_graph_cache

            clear_graph_cache()

        # Force the unsupervised task so target detection and model
        # selection take the clustering branch (BUG fix: without this,
        # target detection stamps "ambiguous" on numeric data and the
        # pipeline trains a supervised model instead).
        self._state.task_type = "clustering"
        self._state.target_column = None
        self._ensure_sync(_CLUSTERING)
        state = self._state

        labels = state.cluster_labels or []
        metrics = state.cluster_metrics or {}

        return ClusteringReport(
            algorithm=metrics.get("algorithm", "unknown"),
            n_clusters=metrics.get("n_clusters", 0),
            silhouette_score=metrics.get("silhouette_score"),
            davies_bouldin_score=metrics.get("davies_bouldin_score"),
            calinski_harabasz_score=metrics.get("calinski_harabasz_score"),
            cluster_labels=labels,
            params=metrics.get("params", {}),
            raw=metrics,
        )

    def detect_anomalies(
        self,
        contamination: float = 0.1,
        algorithms: list[str] | None = None,
    ) -> AnomalyReport:
        """Run anomaly detection on the dataset.

        Executes upload through anomaly evaluation. Automatically
        selects the best algorithm (Isolation Forest, LOF).

        Args:
            contamination: Expected fraction of anomalies.
            algorithms: Optional list of algorithms to try.

        Returns:
            An ``AnomalyReport`` with algorithm, labels, scores.
        """
        self._state.anomaly_contamination = contamination
        if algorithms is not None:
            self._state.anomaly_algorithms = algorithms
            from phronesisml.workflow.graph import clear_graph_cache

            clear_graph_cache()

        # Force the unsupervised task (see ``cluster()`` for rationale).
        self._state.task_type = "anomaly_detection"
        self._state.target_column = None
        self._ensure_sync(_ANOMALY)
        state = self._state

        labels = state.anomaly_labels or []
        scores = state.anomaly_scores or []
        metrics = state.anomaly_metrics or {}

        return AnomalyReport(
            algorithm=metrics.get("algorithm", "unknown"),
            n_anomalies=metrics.get("n_anomalies", 0),
            contamination=contamination,
            anomaly_labels=labels,
            anomaly_scores=scores,
            params=metrics.get("params", {}),
            raw=metrics,
        )

    def report(self) -> str:
        """Generate a full Markdown report of the pipeline run.

        Runs all stages up to reporting if not already done.

        Returns:
            A Markdown string containing the complete pipeline report.
        """
        self._ensure_sync(_REPORT)
        return str(self._state.final_report or "")

    def generate_report(self, format: str = "markdown") -> str:
        """Generate a pipeline report in the specified format.

        Args:
            format: Output format.  ``"markdown"`` (default) returns
                a Markdown string.  ``"html"`` returns a self-contained
                HTML document.  ``"pdf"`` raises ``NotImplementedError``.

        Returns:
            A string containing the report in the requested format.

        Raises:
            NotImplementedError: If *format* is ``"pdf"``.
        """
        if format == "pdf":
            msg = "PDF report format is not yet supported."
            raise NotImplementedError(msg)
        if format == "html":
            from phronesisml.ml.reports.builder import build_html_report

            self._ensure_sync(_REPORT)
            return build_html_report(self._state)
        if format == "markdown":
            return self.report()
        msg = f"Report format {format!r} is not supported. Supported formats: 'markdown', 'html'."
        raise NotImplementedError(msg)

    def run(self, mode: str = "balanced") -> Phronesis:
        """Execute the complete ML pipeline end-to-end.

        Runs all 11 stages: upload, ETL, validation, EDA, target
        detection, feature engineering, model selection, evaluation,
        explainability, reporting, and storage.

        Args:
            mode: Execution mode controlling which stages run.
                - ``"fast"``: Skips explainability and storage.
                  Recommended for quick prototyping.
                - ``"balanced"``: Full pipeline (default).
                - ``"full"``: Same as balanced, explicit for clarity.

        Returns:
            ``self`` for method chaining.

        Example::

            ml = Phronesis("data.csv")
            ml.run(mode="fast")  # Quick results
            ml.run()             # Full pipeline
        """
        if mode == "fast":
            stages = _FAST
            logger.info("Running in FAST mode — skipping explainability and storage.")
        elif mode == "balanced":
            stages = _BALANCED
        elif mode == "full":
            stages = _FULL_MODE
        else:
            msg = f"Unknown mode '{mode}'. Use 'fast', 'balanced', or 'full'."
            raise ValueError(msg)

        self._ensure_sync(stages)
        return self

    # ── Convenience accessors ──────────────────────────────────────

    def get_data(self) -> Any:
        """Return the raw loaded DataFrame.

        Runs ``load()`` automatically if not yet done.
        """
        self._ensure_sync(_UPLOAD)
        df = self._state.raw_data
        if df is None:
            raise ValueError("No data loaded.")
        return _to_df(df)

    def get_cleaned_data(self) -> Any:
        """Return the cleaned (post-ETL) DataFrame.

        Runs ``clean()`` automatically if not yet done.
        """
        self._ensure_sync(_ETL)
        df = self._state.processed_data
        if df is None:
            raise ValueError("No cleaned data available.")
        return _to_df(df)

    def get_features(self) -> Any:
        """Return the engineered feature DataFrame.

        Runs ``engineer_features()`` automatically if not yet done.
        """
        return self.engineer_features().features

    def get_model(self) -> Any:
        """Return the trained sklearn model object.

        Runs ``train()`` automatically if not yet done.
        """
        self._ensure_sync(_MODEL)
        return self._state.trained_model

    # ── Convenience aliases ─────────────────────────────────────────

    def target(self) -> TargetInfo:
        return self.detect_target()

    def engineer(self) -> FeatureReport:
        return self.engineer_features()

    def select_model(self, cv: int | None = None, model_type: str | None = None) -> ModelInfo:
        return self.recommend_model(cv=cv, model_type=model_type)

    def recommend(self, cv: int | None = None, model_type: str | None = None) -> ModelInfo:
        return self.recommend_model(cv=cv, model_type=model_type)

    # ── Extended SDK surface ─────────────────────────────────────────

    def analyze(self) -> EDAReport:
        """Analyze the dataset: load, clean, validate, and profile.

        Equivalent to :meth:`eda`; runs every stage through EDA and
        returns the statistical report.

        Returns:
            An ``EDAReport`` with numeric/categorical summaries.
        """
        return self.eda()

    def profile(self) -> DatasetSummary:
        """Return a structured profile of the loaded dataset.

        Equivalent to :meth:`summary`; includes shape, dtypes, memory,
        missing values, duplicates, and a preview.

        Returns:
            A ``DatasetSummary``.
        """
        return self.summary()

    def predict(
        self,
        data: Any,
        already_engineered: bool = False,
    ) -> list[Any]:
        """Predict on new rows with the trained model.

        The saved transform recipe (null fill, label encoding, min-max
        scaling, feature selection) is applied to *data* before
        prediction, reproducing the exact feature space the model saw
        during training — no retraining required.  Deterministic and
        offline.

        Args:
            data: A pandas DataFrame (or array-like) shaped like the
                original training data; the target column, if present,
                is ignored.
            already_engineered: ``True`` if *data* already contains the
                engineered feature columns (skips recipe transformation).

        Returns:
            A list of model predictions, one per input row.

        Raises:
            ValueError: If no trained model is available or the recipe
                is missing while required.
            DataTransformError: If *data* cannot be transformed by the
                saved recipe (e.g. missing columns).
        """
        self._ensure_sync(_MODEL)
        return self._predict_ready(data, already_engineered=already_engineered)

    def _predict_ready(
        self,
        data: Any,
        already_engineered: bool = False,
    ) -> list[Any]:
        """Predict using the model already trained on this instance.

        Internal: assumes the model stages have run (e.g. via
        ``await _run_stages(_MODEL)``).  Public callers should use
        :meth:`predict`, which runs the stages as needed.
        """
        if self._state.trained_model is None:
            msg = (
                "No trained model available. Run train() / recommend_model() "
                "before calling predict()."
            )
            raise ValueError(msg)

        import pandas as pd

        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)

        if already_engineered:
            feature_names = self._state.feature_names or list(df.columns)
            missing = [c for c in feature_names if c not in df.columns]
            if missing:
                msg = f"Prediction data is missing engineered feature columns: {missing}"
                raise ValueError(msg)
            features = df[list(feature_names)]
        else:
            if not self._state.feature_transform:
                msg = (
                    "No feature transform recipe is available for this run. "
                    "Pass 'already_engineered=True' with engineered features, "
                    "or retrain through the pipeline so a recipe is recorded."
                )
                raise ValueError(msg)
            from phronesisml.ml.feature_engineering.transform import apply_transform_recipe

            features = apply_transform_recipe(df, self._state.feature_transform)

        predictions = self._state.trained_model.predict(features)
        return list(predictions)

    def compare(self, model_types: list[str] | None = None) -> ModelComparison:
        """Train several models on the same data and rank them.

        The recommended baseline model (already trained on this
        instance) is included automatically.  Each additional requested
        model is trained through the full pipeline with its own
        resource-bounded HPO, so comparisons are apples-to-apples.

        Args:
            model_types: Names of models to compare (e.g.
                ``["random_forest", "logistic_regression"]``).  If
                ``None``, every model in the recommended candidate pool
                is compared.

        Returns:
            A ``ModelComparison`` with a best-first ``ranking`` sorted by
            the task's primary metric.

        Example::

            ml = Phronesis("data.csv")
            ml.train()
            comparison = ml.compare(["random_forest", "gradient_boosting"])
            print(comparison.best_model)
        """
        self._ensure_sync(_EVALUATION)

        import asyncio

        return asyncio.run(self._compare_core(model_types))

    async def _compare_core(self, model_types: list[str] | None = None) -> ModelComparison:
        """Compute the model comparison for this instance.

        Internal: assumes the evaluation stages have run.  Public
        callers should use :meth:`compare` (sync) or await this method
        from an async context after ``await _run_stages(_EVALUATION)``.
        """
        task_type = self._state.task_type or "classification"
        baseline_name = (self._state.best_pipeline or {}).get("model_type")
        baseline_report = self._state.evaluation_report or {}
        baseline_metrics = baseline_report.get("metrics", {})

        if model_types is None:
            model_types = [
                str(name)
                for c in (self._state.candidate_models or [])
                if (name := c.get("name")) is not None
            ]

        models: list[dict[str, Any]] = [{"model": baseline_name, "metrics": baseline_metrics}]
        for model_type in model_types:
            if not model_type or model_type == baseline_name:
                continue
            models.append(await self._compare_one_core(model_type))

        from phronesisml.ml.evaluation.report import compare_models

        evaluations = [
            {"model_info": {"name": m.get("model")}, "metrics": m.get("metrics", {})}
            for m in models
            if m.get("metrics")
        ]
        ranking = compare_models(evaluations, task_type)

        return ModelComparison(
            task_type=task_type,
            primary_metric=ranking["primary_metric"],
            higher_is_better=ranking["higher_is_better"],
            ranking=ranking["ranking"],
            models=models,
        )

    async def _compare_one_core(self, model_type: str) -> dict[str, Any]:
        """Train a single named model on the same data and return its metrics."""
        from phronesisml.exceptions import WorkflowError

        other = Phronesis(
            data_path=self._data_path,
            config=self._config,
            agent_overrides={"model_selection": {"model_type": model_type}},
        )
        try:
            await other._run_stages(_EVALUATION)
        except WorkflowError as exc:
            return {"model": model_type, "metrics": {}, "error": str(exc)}
        report = other.state.evaluation_report or {}
        return {"model": model_type, "metrics": report.get("metrics", {})}

    def save(self, directory: str | Path | None = None) -> dict[str, Any]:
        """Persist the full artifact suite (including the trained model).

        Runs every stage through storage if needed, then writes the
        standard artifact set to ``<directory>/<run_id>/`` (default
        ``./Phronesis_artifacts/<run_id>/``).

        Args:
            directory: Base directory for artifacts.  ``None`` re-uses
                the pipeline default or the last artifact URI.

        Returns:
            A dict with ``artifact_uri``, ``saved_files``, and
            ``warnings``.

        Example::

            ml = Phronesis("data.csv")
            ml.train()
            info = ml.save("saved_runs")
            restored = Phronesis.restore(info["artifact_uri"])
            restored.predict(new_rows)
        """
        self._ensure_sync(_FULL)
        return self._save_ready(directory)

    def _save_ready(self, directory: str | Path | None = None) -> dict[str, Any]:
        """Persist the artifact suite assuming all stages have already run.

        Internal: public callers should use :meth:`save`, which runs the
        pipeline through storage as needed.
        """
        from phronesisml.services.storage import save_artifacts

        if directory is None:
            if self._state.artifact_uri:
                base = Path(self._state.artifact_uri)
            else:
                base = Path("./Phronesis_artifacts")
        else:
            base = Path(directory)

        result = save_artifacts(self._state, base_dir=base)
        self._state.artifact_uri = result["artifact_uri"]
        return result

    @classmethod
    def restore(cls, directory: str | Path) -> SavedRun:
        """Restore a saved run for offline prediction.

        Args:
            directory: The artifact directory produced by :meth:`save`.

        Returns:
            A ``SavedRun`` with a ``predict()`` method and run metadata.
        """
        return SavedRun.from_directory(directory)

    def version(self) -> str:
        """Return the installed ``phronesisml`` version."""
        from phronesisml import __version__

        return __version__

    def capabilities(self) -> dict[str, Any]:
        """Report the SDK's capabilities: engines, tasks, stages, APIs.

        Deterministic, offline, and inspectable — the same information
        surfaced by ``phronesisml capabilities``.

        Returns:
            A dict describing supported task types, engines, explainers,
            pipeline stages, SDK methods, CLI commands, and extras.
        """
        from phronesisml import __version__
        from phronesisml._stages import _FULL_PIPELINE_STAGES
        from phronesisml.engines.recommend import engine_capabilities

        methods = [
            "run",
            "train",
            "analyze",
            "predict",
            "evaluate",
            "profile",
            "clean",
            "validate",
            "recommend",
            "compare",
            "report",
            "explain",
            "save",
            "restore",
            "version",
            "capabilities",
            "health",
            "load",
            "summary",
            "eda",
            "detect_target",
            "engineer_features",
            "cluster",
            "detect_anomalies",
            "detect_task",
            "generate_report",
        ]
        return {
            "name": "phronesisml",
            "version": __version__,
            "offline": True,
            "deterministic": True,
            "task_types": [
                "classification",
                "regression",
                "clustering",
                "anomaly_detection",
                "ambiguous",
                "analytics",
            ],
            "engines": engine_capabilities(),
            "explainers": ["tree", "linear", "permutation", "kernel"],
            "pipeline_stages": list(_FULL_PIPELINE_STAGES),
            "sdk_methods": methods,
            "cli_commands": [
                "run",
                "info",
                "train",
                "evaluate",
                "analyze",
                "validate",
                "profile",
                "explain",
                "report",
                "compare",
                "version",
                "capabilities",
                "doctor",
            ],
            "extras": ["cli", "spark", "mlflow", "excel", "dev", "all"],
        }

    def health(self) -> dict[str, Any]:
        """Run offline dependency and self checks.

        Verifies that every core and optional dependency imports, and
        reports a stable ``status``.

        Returns:
            A dict with ``status`` (``"ok"`` / ``"degraded"``),
            ``version``, ``python``, and per-dependency availability.
        """
        from phronesisml import __version__

        checks: dict[str, Any] = {}
        for module, label in (
            ("pandas", "pandas"),
            ("numpy", "numpy"),
            ("polars", "polars"),
            ("sklearn", "scikit-learn"),
            ("shap", "shap"),
            ("langgraph", "langgraph"),
            ("pydantic", "pydantic"),
            ("joblib", "joblib"),
            ("pyarrow", "pyarrow"),
            ("openpyxl", "openpyxl (excel extra)"),
            ("pyspark", "pyspark (spark extra)"),
            ("mlflow", "mlflow (mlflow extra)"),
            ("typer", "typer (cli extra)"),
            ("rich", "rich (cli extra)"),
        ):
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "installed")
                checks[label] = {"installed": True, "version": str(version)}
            except Exception:
                checks[label] = {"installed": False, "version": None}

        missing_core = sorted(
            label for label, info in checks.items() if not info["installed"] and "(" not in label
        )
        status = "ok" if not missing_core else "degraded"

        return {
            "status": status,
            "version": __version__,
            "python": sys.version.split()[0],
            "dependencies": checks,
            "missing_core": missing_core,
        }

    # ── Dunder methods ─────────────────────────────────────────────

    def __repr__(self) -> str:
        stages = len(self._executed_stages)
        elapsed = f"{self.elapsed:.1f}s" if self.elapsed is not None else "N/A"
        return f"Phronesis(path={self._data_path!r}, stages_completed={stages}, elapsed={elapsed})"

    def _repr_html_(self) -> str:
        stages = len(self._executed_stages)
        elapsed = f"{self.elapsed:.1f}s" if self.elapsed is not None else "N/A"
        target = self._state.target_column or "N/A"
        model = (self._state.best_pipeline or {}).get("model_type", "N/A")
        return (
            "<div style='font-family:monospace;padding:8px;"
            "border:1px solid #ccc;border-radius:4px'>"
            f"<b>Phronesis</b><br>"
            f"Path: <code>{self._data_path}</code><br>"
            f"Stages completed: {stages}/11<br>"
            f"Elapsed: {elapsed}<br>"
            f"Target: <code>{target}</code><br>"
            f"Model: <code>{model}</code>"
            "</div>"
        )
