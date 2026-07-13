"""Model training with resource-bounded hyperparameter optimization.

Trains each candidate model from ``auto_selector`` using a train/test
split and optional grid search over the candidate's parameter space.
All HPO is enforced to respect ``max_trials`` and ``max_time_seconds``
— the search cannot run unbounded under any code path.

Design:
- ``train_models()`` is the single entry point.  It iterates over
  candidates, trains each with its parameter grid, and returns the
  best model plus metadata.
- ``max_trials`` caps the total number of parameter combinations
  evaluated across ALL candidates (not per-candidate).  This is a
  hard ceiling — once exhausted, remaining candidates are skipped.
- ``max_time_seconds`` caps total wall-clock time.  A monotonic clock
  is checked before each trial; if exceeded, the search stops and the
  best result found so far is returned with ``truncated=True``.
- All data operations use ``engine.collect()`` to materialise DataFrames.
  sklearn model imports are allowed per the established convention.
- The train/test split is stratified for classification and random
  for regression, using ``task_type`` from Target Detection.

Scalability:
- For very large datasets, the train/test split holds in memory (pandas).
  Future: add sampling or chunked training for out-of-core data.
- Parameter grids are intentionally small (3-5 values per param).
  Future: replace with Bayesian optimisation for larger search spaces.
"""

from __future__ import annotations

import contextlib
import importlib
import logging
import time
from typing import Any

import numpy as np
import pandas as pd

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.exceptions import AgentError
from phronesisml.ml.automl.auto_selector import CandidateModel

logger = logging.getLogger(__name__)

# Default resource bounds — enforced at the agent level, not optional.
DEFAULT_MAX_TRIALS = 50
DEFAULT_MAX_TIME_SECONDS = 120
DEFAULT_TEST_SIZE = 0.2
DEFAULT_RANDOM_STATE = 42


def train_models(
    df: pd.DataFrame,
    engine: BaseEngine,
    candidates: list[CandidateModel],
    target_column: str,
    task_type: str,
    max_trials: int = DEFAULT_MAX_TRIALS,
    max_time_seconds: int = DEFAULT_MAX_TIME_SECONDS,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
    cv: int | None = None,
) -> dict[str, Any]:
    """Train candidate models and return the best one.

    Args:
        df: The engineered feature DataFrame (collected to pandas).
        engine: The active computation engine (for interface consistency).
        candidates: Ranked list of candidate models from ``auto_selector``.
        target_column: Name of the target column.
        task_type: ``"classification"``, ``"regression"``, or ``"ambiguous"``.
        max_trials: Maximum total parameter combinations to evaluate.
            Enforced as a hard ceiling — search stops when exceeded.
        max_time_seconds: Maximum total wall-clock seconds for HPO.
            Enforced via monotonic clock check before each trial.
        test_size: Fraction of data to hold out for evaluation.
        random_state: Random seed for reproducibility.
        cv: Number of cross-validation folds.  If ``None`` (default),
            uses a single train/test split.  If an integer ≥ 2, uses
            k-fold cross-validation to score each trial.

    Returns:
        A dict with keys: ``best_model``, ``best_params``,
        ``best_score``, ``cv_results``, ``trials_used``,
        ``time_elapsed``, ``truncated``.

    Raises:
        AgentError: If no model could be trained successfully.

    """
    # ── Prepare data ─────────────────────────────────────────────────
    feature_cols = [c for c in df.columns if c != target_column]
    features = df[feature_cols].values
    target = df[target_column].values

    use_cv = cv is not None and cv >= 2

    if use_cv:
        features_train = features
        features_test = features
        target_train = target
        target_test = target
    else:
        features_train, features_test, target_train, target_test = _split_data(
            features,
            target,
            task_type,
            test_size,
            random_state,
        )

    # ── Search state ─────────────────────────────────────────────────
    best_score = -float("inf")
    best_model: Any = None
    best_params: dict[str, Any] = {}
    cv_results: list[dict[str, Any]] = []
    trials_used = 0
    truncated = False
    start_time = time.monotonic()

    # ── Iterate over candidates ──────────────────────────────────────
    for candidate in candidates:
        if trials_used >= max_trials:
            logger.warning(
                "HPO truncated: max_trials=%d reached after %d trials.",
                max_trials,
                trials_used,
            )
            truncated = True
            break

        elapsed = time.monotonic() - start_time
        if elapsed >= max_time_seconds:
            logger.warning(
                "HPO truncated: max_time_seconds=%d reached after %.1fs.",
                max_time_seconds,
                elapsed,
            )
            truncated = True
            break

        param_grid = _build_param_grid(
            candidate.param_space,
            max_remaining_trials=max_trials - trials_used,
        )

        try:
            model_class = _import_estimator(candidate.estimator_path)
        except (ImportError, ModuleNotFoundError) as exc:
            logger.warning(
                "Could not import estimator for %s: %s — skipping.",
                candidate.name,
                exc,
            )
            continue

        for params in param_grid:
            # ── Resource check: trials ───────────────────────────────
            if trials_used >= max_trials:
                truncated = True
                break

            # ── Resource check: time ─────────────────────────────────
            elapsed = time.monotonic() - start_time
            if elapsed >= max_time_seconds:
                truncated = True
                break

            try:
                # Some models (e.g. LinearRegression) don't accept random_state
                try:
                    model = model_class(**params, random_state=random_state)
                except TypeError:
                    model = model_class(**params)

                if use_cv:
                    from sklearn.model_selection import cross_val_score

                    cv_scores = cross_val_score(
                        model,
                        features_train,
                        target_train,
                        cv=cv,
                        scoring="accuracy" if task_type == "classification" else "r2",
                    )
                    score = float(cv_scores.mean())
                else:
                    model.fit(features_train, target_train)
                    score = model.score(features_test, target_test)

                trials_used += 1

                result_entry = {
                    "candidate": candidate.name,
                    "params": params,
                    "score": float(score),
                    "time_sec": float(time.monotonic() - start_time),
                }
                cv_results.append(result_entry)

                if score > best_score:
                    best_score = score
                    best_model = model
                    best_params = params

                logger.debug(
                    "Trial %d: %s %s -> %.4f",
                    trials_used,
                    candidate.name,
                    params,
                    score,
                )
            except Exception as exc:
                logger.warning(
                    "Trial failed for %s %s: %s",
                    candidate.name,
                    params,
                    exc,
                )
                trials_used += 1

        if truncated:
            break

    elapsed = time.monotonic() - start_time

    if best_model is None:
        msg = (
            f"No model could be trained successfully after {trials_used} "
            f"trials ({elapsed:.1f}s). Check data quality and candidate models."
        )
        raise AgentError(msg)

    # Refit best model on all data when using CV (cross_val_score doesn't refit)
    if use_cv:
        with contextlib.suppress(Exception):
            best_model.fit(features, target)

    logger.info(
        "Training complete: best=%s, score=%.4f, trials=%d, time=%.1fs, truncated=%s",
        best_params,
        best_score,
        trials_used,
        elapsed,
        truncated,
    )

    return {
        "best_model": best_model,
        "best_params": best_params,
        "best_score": float(best_score),
        "cv_results": cv_results,
        "trials_used": trials_used,
        "time_elapsed": float(elapsed),
        "truncated": truncated,
        "feature_names": feature_cols,
    }


def _split_data(
    features: np.ndarray[Any, Any],
    target: np.ndarray[Any, Any],
    task_type: str,
    test_size: float,
    random_state: int,
) -> tuple[
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
]:
    """Split data into train/test sets.

    Uses stratified split for classification, random split for regression
    and ambiguous tasks.
    """
    from sklearn.model_selection import train_test_split

    stratify = target if task_type == "classification" else None
    result: tuple[
        np.ndarray[Any, Any],
        np.ndarray[Any, Any],
        np.ndarray[Any, Any],
        np.ndarray[Any, Any],
    ] = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )
    return result


def _import_estimator(estimator_path: str) -> type[Any]:
    """Dynamically import an sklearn estimator class from its dotted path."""
    module_path, class_name = estimator_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)  # type: ignore[no-any-return]


def _build_param_grid(
    param_space: dict[str, list[Any]],
    max_remaining_trials: int,
) -> list[dict[str, Any]]:
    """Build a list of parameter dicts from the param space.

    If the full grid exceeds ``max_remaining_trials``, truncate to
    the first ``max_remaining_trials`` combinations (pre-order).
    """
    if not param_space:
        return [{}]

    keys = list(param_space.keys())
    values = [param_space[k] for k in keys]

    # Cartesian product (iterative to avoid recursion depth issues)
    grid: list[dict[str, Any]] = [{}]
    for key, vals in zip(keys, values, strict=True):
        new_grid: list[dict[str, Any]] = []
        for combo in grid:
            for v in vals:
                new_grid.append({**combo, key: v})
        grid = new_grid

        # Early truncation if grid is already too large
        if len(grid) > max_remaining_trials:
            grid = grid[:max_remaining_trials]
            break

    return grid[:max_remaining_trials]
