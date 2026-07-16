"""Evaluation metrics — problem-type-appropriate model scoring.

Computes metrics based on the task type recorded by Task Detection
— never infers problem type independently.  Surfaces ambiguity
caveats when Task Detection recorded low confidence.

Supported metric sets:
- **Classification**: accuracy, precision (macro), recall (macro),
  F1 (macro), confusion matrix.
- **Regression**: RMSE, MAE, R².
- **Clustering**: silhouette, davies-bouldin, calinski-harabasz.
- **Anomaly Detection**: contamination ratio, anomaly count.
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
    target_column: str | None = None,
    feature_names: list[str] | None = None,
    task_type: str | None = None,
    best_params: dict[str, Any] | None = None,
    target_detection_confidence: float | None = None,
    ambiguity_reason: str | None = None,
    mlflow_experiment: str | None = None,
    cluster_labels: list[int] | None = None,
    anomaly_labels: list[int] | None = None,
    anomaly_contamination: float | None = None,
) -> dict[str, Any]:
    """Evaluate a trained model and return a metrics report.

    Args:
        model: A trained sklearn-compatible estimator.
        df: The full engineered DataFrame.
        target_column: Name of the target column (None for unsupervised).
        feature_names: Names of the feature columns.
        task_type: ``"classification"``, ``"regression"``,
            ``"clustering"``, ``"anomaly_detection"``, or
            ``"ambiguous"`` — from Task Detection.
        best_params: The hyperparameters that produced this model.
        target_detection_confidence: Confidence from Task Detection.
        ambiguity_reason: Reason if Task Detection was ambiguous.
        mlflow_experiment: Optional MLflow experiment name.
        cluster_labels: Pre-computed cluster labels (for clustering).
        anomaly_labels: Pre-computed anomaly labels (for anomaly).
        anomaly_contamination: Expected contamination ratio.

    Returns:
        A dict with keys: ``task_type``, ``metrics``, ``model_info``,
        ``ambiguity_caveat``, ``mlflow_logged``.

    """
    if feature_names is None:
        if target_column:
            feature_names = [c for c in df.columns if c != target_column]
        else:
            feature_names = list(df.columns)

    features_df = df[feature_names].copy()

    # Encode any remaining categorical (object) columns as integers
    for col in features_df.columns:
        if features_df[col].dtype == "object":
            features_df[col] = pd.factorize(features_df[col])[0]

    features = features_df.values

    # ── Compute metrics based on task type ──────────────────────────
    if task_type == "clustering":
        if cluster_labels is not None:
            metrics = _clustering_metrics(features, cluster_labels)
        elif model is not None and hasattr(model, "labels_"):
            metrics = _clustering_metrics(features, model.labels_.tolist())
        else:
            metrics = {}
    elif task_type == "anomaly_detection":
        if anomaly_labels is not None:
            metrics = _anomaly_metrics(anomaly_labels, anomaly_contamination or 0.1)
        elif model is not None and hasattr(model, "predict"):
            try:
                pred = model.predict(features)
                labels = (pred == -1).astype(int).tolist()
                metrics = _anomaly_metrics(labels, anomaly_contamination or 0.1)
            except Exception:
                metrics = {}
        else:
            metrics = {}
    elif target_column is not None and target_column in df.columns:
        target = df[target_column].values
        y_pred = model.predict(features)

        if task_type == "classification":
            metrics = _classification_metrics(target, y_pred)
        elif task_type == "regression":
            metrics = _regression_metrics(target, y_pred)
        elif task_type == "ambiguous":
            unique_target = np.unique(target)
            is_classification_like = len(unique_target) <= 20 and np.all(
                unique_target == unique_target.astype(int)
            )
            if is_classification_like:
                metrics = _classification_metrics(target, y_pred)
                with contextlib.suppress(ValueError, TypeError):
                    metrics.update(_regression_metrics(target, y_pred))
            else:
                metrics = _regression_metrics(target, y_pred)
        else:
            unique_target = np.unique(target)
            if len(unique_target) <= 20 and np.all(unique_target == unique_target.astype(int)):
                metrics = _classification_metrics(target, y_pred)
            else:
                metrics = _regression_metrics(target, y_pred)
    else:
        metrics = {}

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
    model_name = type(model).__name__ if model is not None else "unsupervised"
    model_module = type(model).__module__ if model is not None else "unknown"
    model_info: dict[str, Any] = {
        "model_type": model_name,
        "model_module": model_module,
        "best_params": best_params or {},
        "n_features": len(feature_names),
        "n_samples": len(df),
    }

    # ── MLflow logging (graceful degradation) ────────────────────────
    mlflow_logged = False
    if model is not None:
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
    """Compute classification metrics: accuracy, precision, recall, F1, ROC-AUC, CM."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    accuracy = float(accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    recall = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred)

    # ROC-AUC: requires probability estimates or binary labels
    with contextlib.suppress(ValueError, TypeError):
        roc_auc = float(roc_auc_score(y_true, y_pred))
        return {
            "accuracy": accuracy,
            "precision_macro": precision,
            "recall_macro": recall,
            "f1_macro": f1,
            "roc_auc": roc_auc,
            "confusion_matrix": cm.tolist(),
        }

    return {
        "accuracy": accuracy,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "roc_auc": None,
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


def _clustering_metrics(
    X: np.ndarray[Any, Any],
    labels: list[int],
) -> dict[str, Any]:
    """Compute clustering metrics: silhouette, davies-bouldin, calinski-harabasz."""
    from sklearn.metrics import (
        calinski_harabasz_score,
        davies_bouldin_score,
        silhouette_score,
    )

    labels_arr = np.array(labels)
    n_clusters = len(set(labels_arr) - {-1})

    if n_clusters < 2:
        return {
            "n_clusters": n_clusters,
            "silhouette_score": None,
            "davies_bouldin_score": None,
            "calinski_harabasz_score": None,
        }

    # Filter noise points (label == -1 from DBSCAN)
    mask = labels_arr != -1
    if mask.sum() < 2:
        return {
            "n_clusters": n_clusters,
            "silhouette_score": None,
            "davies_bouldin_score": None,
            "calinski_harabasz_score": None,
        }

    X_valid = X[mask]
    labels_valid = labels_arr[mask]

    sil = None
    db = None
    ch = None

    with contextlib.suppress(ValueError, TypeError):
        sil = float(silhouette_score(X_valid, labels_valid))
    with contextlib.suppress(ValueError, TypeError):
        db = float(davies_bouldin_score(X_valid, labels_valid))
    with contextlib.suppress(ValueError, TypeError):
        ch = float(calinski_harabasz_score(X_valid, labels_valid))

    return {
        "n_clusters": n_clusters,
        "silhouette_score": sil,
        "davies_bouldin_score": db,
        "calinski_harabasz_score": ch,
    }


def _anomaly_metrics(
    labels: list[int],
    contamination: float = 0.1,
) -> dict[str, Any]:
    """Compute anomaly detection metrics."""
    labels_arr = np.array(labels)
    n_anomalies = int(labels_arr.sum())
    n_total = len(labels_arr)
    detected_contamination = n_anomalies / n_total if n_total > 0 else 0.0

    return {
        "n_anomalies": n_anomalies,
        "n_total": n_total,
        "detected_contamination": detected_contamination,
        "expected_contamination": contamination,
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

        mlflow.set_experiment(experiment_name or "Phronesis_default")

        with mlflow.start_run() as run:
            # Log params
            for key, value in params.items():
                mlflow.log_param(key, value)

            # Log metrics (only numeric values)
            for key, value in metrics.items():
                if isinstance(value, int | float):
                    mlflow.log_metric(key, value)

            # Log model info as params
            for key, value in model_info.items():
                if isinstance(value, str | int | float | bool):
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
