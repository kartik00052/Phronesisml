"""Evaluation metrics — problem-type-appropriate model scoring.

Computes metrics based on the task type recorded by Target Detection
— never infers problem type independently.  Surfaces ambiguity
caveats when Target Detection recorded low confidence.

Supported metric sets:
- **Classification**: accuracy, precision (macro), recall (macro),
  F1 (macro), confusion matrix.
- **Regression**: RMSE, MAE, R².
- **Ambiguous**: computes both classification and regression metrics
  where applicable, and includes the ambiguity caveat in the report.

MLflow integration:
- If MLflow is configured and reachable, logs experiment, params,
  metrics, and the model artifact.
- If MLflow is not reachable or not configured, logs a warning and
  continues without tracking (graceful degradation).

Scalability:
- All metrics are O(n) or O(n·classes) — no scalability concern.
- MLflow logging is synchronous but fast (local file or REST).
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def evaluate_model(
    model: Any,
    df: pd.DataFrame,
    target_column: str,
    feature_names: list[str],
    task_type: str | None,
    best_params: dict[str, Any] | None = None,
    target_detection_confidence: float | None = None,
    ambiguity_reason: str | None = None,
    mlflow_experiment: str | None = None,
) -> dict[str, Any]:
    """Evaluate a trained model and return a metrics report.

    Args:
        model: A trained sklearn-compatible estimator.
        df: The full engineered DataFrame (train + test will be
            extracted from the trainer's split, or this can be a
            held-out test set).
        target_column: Name of the target column.
        feature_names: Names of the feature columns.
        task_type: ``"classification"``, ``"regression"``, or
            ``"ambiguous"`` — from Target Detection.
        best_params: The hyperparameters that produced this model.
        target_detection_confidence: Confidence from Target Detection.
        ambiguity_reason: Reason if Target Detection was ambiguous.
        mlflow_experiment: Optional MLflow experiment name.

    Returns:
        A dict with keys: ``task_type``, ``metrics``, ``model_info``,
        ``ambiguity_caveat``, ``mlflow_logged``.

    """
    features = df[feature_names].values
    target = df[target_column].values

    y_pred = model.predict(features)

    # ── Compute metrics based on task type ──────────────────────────
    if task_type == "classification":
        metrics = _classification_metrics(target, y_pred)
    elif task_type == "regression":
        metrics = _regression_metrics(target, y_pred)
    elif task_type == "ambiguous":
        # Compute both sets where applicable — skip regression if
        # target is non-numeric (e.g. string labels).
        metrics = _classification_metrics(target, y_pred)
        with contextlib.suppress(ValueError, TypeError):
            metrics.update(_regression_metrics(target, y_pred))
    else:
        # Fallback: try classification if values are discrete
        unique_target = np.unique(target)
        if len(unique_target) <= 20 and np.all(unique_target == unique_target.astype(int)):
            metrics = _classification_metrics(target, y_pred)
        else:
            metrics = _regression_metrics(target, y_pred)

    # ── Build ambiguity caveat ───────────────────────────────────────
    ambiguity_caveat: str | None = None
    if ambiguity_reason is not None:
        ambiguity_caveat = (
            f"Target detection was ambiguous (confidence: "
            f"{target_detection_confidence:.2f}). "
            f"{ambiguity_reason} "
            f"Metrics below should be interpreted with caution."
        )
    elif target_detection_confidence is not None and target_detection_confidence < 0.6:
        ambiguity_caveat = (
            f"Target detection confidence is low "
            f"({target_detection_confidence:.2f}). "
            f"Metrics below should be interpreted with caution."
        )

    # ── Model info ───────────────────────────────────────────────────
    model_info: dict[str, Any] = {
        "model_type": type(model).__name__,
        "model_module": type(model).__module__,
        "best_params": best_params or {},
        "n_features": len(feature_names),
        "n_samples": len(df),
    }

    # ── MLflow logging (graceful degradation) ────────────────────────
    mlflow_logged = _log_to_mlflow(
        model=model,
        metrics=metrics,
        params=best_params or {},
        model_info=model_info,
        experiment_name=mlflow_experiment,
    )

    report: dict[str, Any] = {
        "task_type": task_type,
        "metrics": metrics,
        "model_info": model_info,
        "ambiguity_caveat": ambiguity_caveat,
        "mlflow_logged": mlflow_logged,
    }

    logger.info(
        "Evaluation complete: task=%s, metrics=%s, ambiguity=%s, mlflow=%s",
        task_type,
        list(metrics.keys()),
        ambiguity_caveat is not None,
        mlflow_logged,
    )
    return report


def _classification_metrics(
    y_true: np.ndarray[Any, Any],
    y_pred: np.ndarray[Any, Any],
) -> dict[str, Any]:
    """Compute classification metrics: accuracy, precision, recall, F1, confusion matrix."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    accuracy = float(accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    recall = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred)

    return {
        "accuracy": accuracy,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "confusion_matrix": cm.tolist(),
    }


def _regression_metrics(
    y_true: np.ndarray[Any, Any],
    y_pred: np.ndarray[Any, Any],
) -> dict[str, Any]:
    """Compute regression metrics: RMSE, MAE, R²."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
    }


def _log_to_mlflow(
    model: Any,
    metrics: dict[str, Any],
    params: dict[str, Any],
    model_info: dict[str, Any],
    experiment_name: str | None,
) -> bool:
    """Log to MLflow with graceful degradation.

    Returns ``True`` if logging succeeded, ``False`` if MLflow was
    unavailable or not configured.
    """
    try:
        import mlflow

        mlflow.set_experiment(experiment_name or "aetherml_default")

        with mlflow.start_run(log_output=False) as run:
            # Log params
            for key, value in params.items():
                mlflow.log_param(key, value)

            # Log metrics (only numeric values)
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)

            # Log model info as params
            for key, value in model_info.items():
                if isinstance(value, (str, int, float, bool)):
                    mlflow.log_param(f"info_{key}", value)

            # Log model artifact
            mlflow.sklearn.log_model(model, "model")

            logger.info("MLflow run logged: %s", run.info.run_id)
        return True
    except ImportError:
        logger.warning("MLflow not installed — skipping experiment tracking.")
        return False
    except Exception as exc:
        logger.warning("MLflow logging failed (continuing without tracking): %s", exc)
        return False
