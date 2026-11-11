"""Prediction service — real inference with a run's stored fitted model.

Model + feature metadata are loaded through the SDK's ``SavedRun`` single
source of truth (``run_metadata.json`` / ``model.json`` /
``feature_metadata.json`` / ``config.json`` / ``model.joblib``), then
predicted over the provided sample rows restricted to the run's recorded
feature set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.db import repositories


class PredictionError(Exception):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def predict(run_id: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
    run = repositories.get_run(run_id)
    if run is None:
        raise PredictionError("RunNotFound", "No such run.", status=404)
    run_dir = _run_dir(run_id)
    if run_dir is None:
        raise PredictionError(
            "ModelUnavailable",
            "No stored artifacts are available for this run.",
        )
    if not samples:
        raise PredictionError("EmptySamples", "At least one sample row is required.")

    try:
        from phronesisml.sdk import SavedRun

        saved = SavedRun.from_directory(run_dir)
    except FileNotFoundError as exc:  # noqa: BLE001 - saved-run loader raises this per file
        raise PredictionError(
            "ModelUnavailable",
            "Trained model artifacts (model.joblib + metadata) are incomplete for this run.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise PredictionError("ModelLoadFailed", f"Could not load the saved run: {exc}") from exc

    model = saved.model
    try:
        predictions = _predict_rows(saved, samples)
    except Exception as exc:  # noqa: BLE001
        raise PredictionError("PredictionFailed", f"Inference failed: {exc}") from exc

    return {
        "runId": run_id,
        "modelType": getattr(model, "name", None) or run.best_model_type or "unknown",
        "predictions": predictions,
    }


def _run_dir(run_id: str) -> Path | None:
    """Resolved run artifact directory, or ``None`` when it escapes storage."""
    from backend.app.config import get_settings

    storage_root = get_settings().run_storage_dir.resolve()
    resolved = (storage_root / run_id).resolve()
    if not resolved.is_relative_to(storage_root):
        return None
    return resolved if resolved.is_dir() else None


def _predict_rows(saved: Any, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import pandas as pd

    frame = pd.DataFrame(samples)
    transform = saved.feature_transform
    if transform:
        from phronesisml.ml.feature_engineering.transform import apply_transform_recipe

        features = apply_transform_recipe(frame, transform)
    else:
        features = frame[list(saved.feature_names or frame.columns)]

    raw_predictions = list(saved.model.predict(features))
    module = getattr(saved.model, "predict_proba", None)
    predictions: list[dict[str, Any]] = []
    for idx, pred in enumerate(raw_predictions):
        entry: dict[str, Any] = {"prediction": _json_scalar(pred)}
        if module is not None:
            try:
                proba = module(features.iloc[[idx]]).tolist()[0]
                entry["probability"] = [round(float(p), 6) for p in proba]
            except Exception:  # noqa: BLE001
                pass
        entry["features"] = {str(k): _json_scalar(v) for k, v in samples[idx].items()}
        predictions.append(entry)
    return predictions


def _json_scalar(value: Any) -> Any:
    import math

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    return str(value)
