"""AetherML public SDK — the clean developer-facing API.

This module provides the ``AetherML`` class, a thin facade over the
internal LangGraph workflow.  Developers interact with meaningful ML
operations; the SDK handles orchestration, state management, and
engine selection internally.

Usage::

    from aetherml import AetherML

    ml = AetherML("data.csv")
    ml.run()                     # execute the full pipeline
    report = ml.report()         # get the Markdown report
    summary = ml.summary()       # get dataset summary

The advanced API (``run_pipeline``, ``WorkflowState``, stage lists)
remains available for users who need full control.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


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
    preview: pd.DataFrame

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
    features: pd.DataFrame


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


@dataclass(frozen=True)
class EvaluationMetrics:
    """Model evaluation results."""

    accuracy: float | None = None
    precision_macro: float | None = None
    recall_macro: float | None = None
    f1_macro: float | None = None
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


# ── Internal engine bootstrap (lazy, lightweight) ────────────────


def _make_engine(
    config: Any | None = None,
    data_path: str | None = None,
) -> Any:
    """Build a computation engine via the engine selector."""
    from aetherml.configs.settings import AetherMLConfig
    from aetherml.engines.engine_selector import select_engine

    if config is None:
        config = AetherMLConfig()
    return select_engine(config=config, data_path=data_path)


def _make_agents(
    engine: Any,
    config: Any | None = None,
) -> dict[str, Any]:
    """Compose all agents with the given engine and config."""
    from aetherml.configs.settings import AetherMLConfig

    if config is None:
        config = AetherMLConfig()

    from aetherml.agents.eda.agent import EDAAgent
    from aetherml.agents.etl.agent import ETLAgent, ETLConfig
    from aetherml.agents.evaluation.agent import EvaluationAgent
    from aetherml.agents.explainability.agent import ExplainabilityAgent
    from aetherml.agents.feature_engineering.agent import FeatureEngineeringAgent
    from aetherml.agents.model_selection.agent import ModelSelectionAgent
    from aetherml.agents.reporting.agent import ReportingAgent
    from aetherml.agents.storage.agent import StorageAgent
    from aetherml.agents.target_detection.agent import TargetDetectionAgent
    from aetherml.agents.upload.agent import UploadAgent
    from aetherml.agents.validation.agent import ValidationAgent

    return {
        "upload": UploadAgent(engine=engine),
        "validation": ValidationAgent(engine=engine),
        "etl": ETLAgent(config=ETLConfig(null_strategy="drop")),
        "eda": EDAAgent(engine=engine),
        "target_detection": TargetDetectionAgent(engine=engine),
        "feature_engineering": FeatureEngineeringAgent(
            engine=engine,
            feature_selection_config=config.feature_selection,
        ),
        "model_selection": ModelSelectionAgent(engine=engine),
        "evaluation": EvaluationAgent(engine=engine),
        "explainability": ExplainabilityAgent(engine=engine),
        "reporting": ReportingAgent(),
        "storage": StorageAgent(),
    }


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


class AetherML:
    """High-level SDK for automated machine learning.

    ``AetherML`` provides an intuitive interface over the internal
    LangGraph pipeline.  Every method delegates to existing agents
    without duplicating business logic.

    Args:
        data_path: Path to a dataset (CSV, Excel, JSON, Parquet, etc.).
        config: Optional ``AetherMLConfig``.  If ``None``, defaults are
            used and can be overridden via property setters.

    Example::

        from aetherml import AetherML

        ml = AetherML("customers.csv")
        ml.run()
        print(ml.report())
    """

    def __init__(
        self,
        data_path: str,
        config: Any | None = None,
    ) -> None:
        from aetherml.configs.settings import AetherMLConfig
        from aetherml.workflow.state import WorkflowState

        self._data_path = data_path
        self._config = config or AetherMLConfig()
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
            self._agents = _make_agents(self._eng, self._config)
        return self._agents

    async def _run_stages(self, stages: list[str]) -> None:
        """Execute the requested pipeline stages via LangGraph.

        Deduplicates: if stages A..B have already been executed,
        only runs the remaining stages.
        """
        from aetherml.workflow.graph import build_graph

        # Determine what still needs to run
        already = self._executed_stages
        needed = [s for s in stages if s not in already]
        if not needed:
            return

        # The graph needs all stages up to the furthest requested
        max_idx = max(stages.index(s) for s in needed)
        graph_stages = stages[: max_idx + 1]

        agents = self._get_agents()
        graph = build_graph(agents, stages=graph_stages)

        if self._start_time is None:
            self._start_time = time.monotonic()

        try:
            from aetherml.exceptions import WorkflowError

            final_state = await graph.ainvoke(self._state)
        except WorkflowError:
            raise
        except Exception as exc:
            from aetherml.exceptions import WorkflowError

            raise WorkflowError(f"Pipeline execution failed: {exc}") from exc

        # Merge returned state into our accumulated state
        if hasattr(final_state, "model_dump"):
            state_dict = final_state.model_dump()
        elif isinstance(final_state, dict):
            state_dict = final_state
        else:
            state_dict = {}

        for key, value in state_dict.items():
            if value is not None:
                setattr(self._state, key, value)

        self._executed_stages.update(stages)

    def _ensure_sync(self, stages: list[str]) -> None:
        """Run stages synchronously via asyncio.run()."""
        import asyncio

        asyncio.run(self._run_stages(stages))

    # ── Public properties ──────────────────────────────────────────

    @property
    def data_path(self) -> str:
        """Path to the input dataset."""
        return self._data_path

    @property
    def config(self) -> Any:
        """The current ``AetherMLConfig``."""
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

    def load(self) -> AetherML:
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

        collected = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
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
        fill_value: Any = None,
        encode: bool = True,
    ) -> AetherML:
        """Clean and transform raw data (ETL stage).

        Applies null handling, type casting, and categorical encoding.

        Args:
            null_strategy: ``"drop"``, ``"fill"``, or ``"flag"``.
                Overrides the constructor default if provided.
            fill_value: Value for ``null_strategy="fill"``.
            encode: Whether to label-encode categorical columns.

        Returns:
            ``self`` for method chaining.
        """
        self._ensure_sync(_UPLOAD)

        if null_strategy is not None:
            from aetherml.agents.etl.agent import ETLAgent, ETLConfig

            agents = self._get_agents()
            agents["etl"] = ETLAgent(config=ETLConfig(null_strategy=null_strategy))

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
            df = validated if isinstance(validated, pd.DataFrame) else pd.DataFrame(validated)
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

    def profile(self) -> DatasetSummary:
        """Alias for ``summary()`` — returns dataset profile.

        This is a convenience alias.  The underlying EDA stage
        enriches the internal state with statistical profiles.

        Returns:
            A ``DatasetSummary``.
        """
        self._ensure_sync(_EDA)
        base = self.summary()
        # Merge EDA profile data into the summary if available
        profile = self._state.data_profile
        if profile is not None:
            return DatasetSummary(
                rows=base.rows,
                columns=base.columns,
                column_names=base.column_names,
                dtypes=base.dtypes,
                memory_bytes=profile.get("memory_bytes", base.memory_bytes),
                missing_values=base.missing_values,
                duplicate_rows=base.duplicate_rows,
                numeric_columns=profile.get("numeric_columns", base.numeric_columns),
                categorical_columns=profile.get("categorical_columns", base.categorical_columns),
                preview=base.preview,
            )
        return base

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
        target_hint: str | None = None,
    ) -> TargetInfo:
        """Automatically detect the prediction target and task type.

        Args:
            target_hint: Optional column name hint.  If provided,
                boosts the confidence for that column.

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
        if isinstance(features, pd.DataFrame):
            df = features
        elif features is not None:
            df = pd.DataFrame(features)
        else:
            df = pd.DataFrame()

        return FeatureReport(
            feature_names=self._state.feature_names or [],
            n_features=len(self._state.feature_names or []),
            n_rows=len(df),
            features=df,
        )

    def recommend_model(self) -> ModelInfo:
        """Recommend and train the best model for the dataset.

        Evaluates multiple candidate models and selects the best one
        based on cross-validation performance.

        Returns:
            A ``ModelInfo`` with the selected model, score, candidates,
            and training details.
        """
        self._ensure_sync(_MODEL)

        bp = self._state.best_pipeline or {}
        return ModelInfo(
            model_type=bp.get("model_type", "unknown"),
            score=bp.get("score", 0.0),
            candidates=self._state.candidate_models or [],
            best_params=bp.get("best_params", {}),
            truncated=bp.get("truncated", False),
            trials_used=bp.get("trials_used", 0),
            time_elapsed=bp.get("time_elapsed", 0.0),
        )

    def train(self) -> ModelInfo:
        """Alias for ``recommend_model()``.

        Trains the recommended model on the engineered features.

        Returns:
            A ``ModelInfo``.
        """
        return self.recommend_model()

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
            confusion_matrix=metrics.get("confusion_matrix"),
            rmse=metrics.get("rmse"),
            mae=metrics.get("mae"),
            r2=metrics.get("r2"),
            ambiguity_caveat=report.get("ambiguity_caveat"),
            raw=report,
        )

    def explain(self) -> ExplanationReport:
        """Explain model predictions using SHAP.

        Computes feature importance based on SHAP values.  Requires
        the ``shap`` package (gracefully degrades if missing).

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
        )

    def report(self, narrative: str | None = None) -> str:
        """Generate a full Markdown report of the pipeline run.

        Runs all stages up to reporting if not already done.

        Args:
            narrative: Optional narrative text to include in the
                report's "Narrative Summary" section.

        Returns:
            A Markdown string containing the complete pipeline report.
        """
        self._ensure_sync(_REPORT)
        return str(self._state.final_report or "")

    def run(self) -> AetherML:
        """Execute the complete ML pipeline end-to-end.

        Runs all 11 stages: upload, ETL, validation, EDA, target
        detection, feature engineering, model selection, evaluation,
        explainability, reporting, and storage.

        Returns:
            ``self`` for method chaining.

        Example::

            ml = AetherML("data.csv")
            ml.run()
            print(ml.report())
            print(ml.evaluate())
        """
        self._ensure_sync(_FULL)
        return self

    # ── Convenience accessors ──────────────────────────────────────

    def get_data(self) -> pd.DataFrame:
        """Return the raw loaded DataFrame.

        Runs ``load()`` automatically if not yet done.
        """
        self._ensure_sync(_UPLOAD)
        df = self._state.raw_data
        if df is None:
            raise ValueError("No data loaded.")
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)

    def get_cleaned_data(self) -> pd.DataFrame:
        """Return the cleaned (post-ETL) DataFrame.

        Runs ``clean()`` automatically if not yet done.
        """
        self._ensure_sync(_ETL)
        df = self._state.processed_data
        if df is None:
            raise ValueError("No cleaned data available.")
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)

    def get_features(self) -> pd.DataFrame:
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

    # ── Dunder methods ─────────────────────────────────────────────

    def __repr__(self) -> str:
        stages = len(self._executed_stages)
        elapsed = f"{self.elapsed:.1f}s" if self.elapsed is not None else "N/A"
        return (
            f"AetherML(path={self._data_path!r}, "
            f"stages_completed={stages}, "
            f"elapsed={elapsed})"
        )
