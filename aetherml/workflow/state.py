"""Shared workflow state for the LangGraph orchestration layer.

``WorkflowState`` is a Pydantic model that serves as the single source
of truth for all data flowing through the pipeline.  Every agent reads
from and writes to this state — there is no direct agent-to-agent
communication.

Design rationale:
- Pydantic BaseModel over TypedDict: gives us runtime validation,
  serialisation, and clear field-level documentation.
- Explicit field ownership: each field's ``description`` documents
  which agent owns (writes to) it.  Agents must only write to fields
  they own.
- All fields are optional with defaults: allows partial pipelines where
  not every agent runs.

Field ownership map:
    run_id                          → [metadata] pipeline identifier
    status                          → [metadata] pipeline status
    raw_data                        → upload agent
    data_path                       → upload agent (input)
    file_format                     → upload agent
    row_count                       → upload agent
    validated_data                  → validation agent
    validation_report               → validation agent
    active_engine                   → engine_selection agent
    processed_data                  → etl agent
    transform_log                   → etl agent
    data_profile                    → eda agent (merged profiling)
    eda_report                      → eda agent
    target_column                   → target_detection agent
    task_type                       → target_detection agent
    target_detection_confidence     → target_detection agent
    ambiguity_reason                → target_detection agent
    features                        → feature_engineering agent
    feature_names                   → feature_engineering agent
    candidate_models                → model_selection agent (merged automl)
    best_pipeline                   → model_selection agent
    trained_model                   → model_selection agent
    evaluation_report               → evaluation agent
    explanation_report              → explainability agent
    rag_context                     → rag agent
    final_report                    → reporting agent
    artifact_uri                    → storage agent
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    """Mutable shared state passed through the LangGraph workflow.

    Every field defaults to ``None`` so that partial pipelines work
    correctly — only the fields populated by the agents that actually
    run will have values.
    """

    # ── Pipeline metadata ────────────────────────────────────────────
    run_id: str | None = Field(
        default=None,
        description="[metadata] Unique identifier for this pipeline run.",
    )
    status: str | None = Field(
        default=None,
        description="[metadata] Current pipeline status (running, completed, failed).",
    )

    # ── Upload agent ────────────────────────────────────────────────
    data_path: str | None = Field(
        default=None,
        description="[input] Path or URI to the source dataset.",
    )
    raw_data: Any = Field(
        default=None,
        description="[upload] Raw DataFrame loaded from data_path.",
    )
    file_format: str | None = Field(
        default=None,
        description="[upload] Detected file format (csv, parquet, json, …).",
    )
    row_count: int | None = Field(
        default=None,
        description="[upload] Number of rows in the raw dataset.",
    )

    # ── Validation agent ────────────────────────────────────────────
    validated_data: Any = Field(
        default=None,
        description="[validation] DataFrame after schema/type validation.",
    )
    validation_report: dict[str, Any] | None = Field(
        default=None,
        description="[validation] Summary of validation checks and results.",
    )

    # ── Engine selection agent ──────────────────────────────────────
    active_engine: str | None = Field(
        default=None,
        description="[engine_selection] Name of the selected engine (pandas/polars/spark).",
    )

    # ── ETL agent ───────────────────────────────────────────────────
    processed_data: Any = Field(
        default=None,
        description="[etl] DataFrame after cleaning and transformation.",
    )
    transform_log: list[dict[str, Any]] | None = Field(
        default=None,
        description="[etl] Ordered list of transformations applied.",
    )

    # ── EDA agent (merged profiling) ────────────────────────────────
    data_profile: dict[str, Any] | None = Field(
        default=None,
        description="[eda] Statistical profile of the dataset.",
    )
    eda_report: dict[str, Any] | None = Field(
        default=None,
        description="[eda] Exploratory data analysis summary and visuals.",
    )

    # ── Feature engineering agent ───────────────────────────────────
    features: Any = Field(
        default=None,
        description="[feature_engineering] DataFrame of engineered features.",
    )
    feature_names: list[str] | None = Field(
        default=None,
        description="[feature_engineering] Names of the generated feature columns.",
    )

    # ── Target detection agent ──────────────────────────────────────
    target_column: str | None = Field(
        default=None,
        description="[target_detection] Name of the target column.",
    )
    task_type: str | None = Field(
        default=None,
        description=(
            "[target_detection] Detected task type "
            "(classification, regression, ambiguous)."
        ),
    )
    target_detection_confidence: float | None = Field(
        default=None,
        description="[target_detection] Confidence score (0.0–1.0) for the detected target.",
    )
    ambiguity_reason: str | None = Field(
        default=None,
        description="[target_detection] Human-readable explanation when confidence < threshold.",
    )

    # ── Model selection agent (merged automl) ───────────────────────
    candidate_models: list[dict[str, Any]] | None = Field(
        default=None,
        description="[model_selection] List of candidate model descriptors.",
    )
    best_pipeline: dict[str, Any] | None = Field(
        default=None,
        description="[model_selection] Best pipeline found by AutoML search.",
    )
    trained_model: Any = Field(
        default=None,
        description="[model_selection] Trained model object.",
    )

    # ── Evaluation agent ────────────────────────────────────────────
    evaluation_report: dict[str, Any] | None = Field(
        default=None,
        description="[evaluation] Model evaluation metrics and diagnostics.",
    )

    # ── Explainability agent ────────────────────────────────────────
    explanation_report: dict[str, Any] | None = Field(
        default=None,
        description="[explainability] SHAP / LIME / feature-importance report.",
    )

    # ── RAG agent ───────────────────────────────────────────────────
    rag_context: dict[str, Any] | None = Field(
        default=None,
        description="[rag] Knowledge retrieved for the current pipeline step.",
    )

    # ── Reporting agent ─────────────────────────────────────────────
    final_report: Any = Field(
        default=None,
        description="[reporting] Final pipeline report (HTML / PDF / Markdown).",
    )

    # ── Storage agent ───────────────────────────────────────────────
    artifact_uri: str | None = Field(
        default=None,
        description="[storage] URI where the model / artifacts were persisted.",
    )

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
