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

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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
) -> dict[str, Any]:
    """Compose all agents with the given engine and config."""
    from phronesisml.configs.settings import PhronesisConfig

    if config is None:
        config = PhronesisConfig()

    from phronesisml.agents.eda.agent import EDAAgent
    from phronesisml.agents.etl.agent import ETLAgent, ETLConfig
    from phronesisml.agents.evaluation.agent import EvaluationAgent
    from phronesisml.agents.explainability.agent import ExplainabilityAgent
    from phronesisml.agents.feature_engineering.agent import FeatureEngineeringAgent
    from phronesisml.agents.model_selection.agent import ModelSelectionAgent
    from phronesisml.agents.reporting.agent import ReportingAgent
    from phronesisml.agents.storage.agent import StorageAgent
    from phronesisml.agents.target_detection.agent import TargetDetectionAgent
    from phronesisml.agents.upload.agent import UploadAgent
    from phronesisml.agents.validation.agent import ValidationAgent

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
    ) -> None:
        from phronesisml.configs.settings import PhronesisConfig
        from phronesisml.workflow.state import WorkflowState

        self._data_path = data_path
        self._config = config or PhronesisConfig()
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
        from phronesisml.workflow.graph import build_graph

        # Determine what still needs to run
        already = self._executed_stages
        needed = [s for s in stages if s not in already]
        if not needed:
            return

        # Build graph with only the needed stages — previously executed
        # stages are skipped; their outputs already live in self._state.
        agents = self._get_agents()
        graph = build_graph(agents, stages=needed)

        if self._start_time is None:
            self._start_time = time.monotonic()

        try:
            from phronesisml.exceptions import WorkflowError

            final_state = await graph.ainvoke(self._state)
        except WorkflowError:
            raise
        except Exception as exc:
            from phronesisml.exceptions import WorkflowError

            raise WorkflowError(f"Pipeline execution failed: {exc}") from exc

        # Merge returned state into our accumulated state — avoid
        # model_dump() which serialises DataFrames and models to dicts.
        if hasattr(final_state, "model_fields_set"):
            for key in final_state.model_fields_set:
                setattr(self._state, key, getattr(final_state, key))
        elif isinstance(final_state, dict):
            for key, value in final_state.items():
                if value is not None:
                    setattr(self._state, key, value)

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
        fill_value: Any = None,
        encode: bool = True,
    ) -> Phronesis:
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
            from phronesisml.agents.etl.agent import ETLAgent, ETLConfig

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

    def run(self) -> Phronesis:
        """Execute the complete ML pipeline end-to-end.

        Runs all 11 stages: upload, ETL, validation, EDA, target
        detection, feature engineering, model selection, evaluation,
        explainability, reporting, and storage.

        Returns:
            ``self`` for method chaining.

        Example::

            ml = Phronesis("data.csv")
            ml.run()
            print(ml.report())
            print(ml.evaluate())
        """
        self._ensure_sync(_FULL)
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
